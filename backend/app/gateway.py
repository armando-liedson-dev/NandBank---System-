"""API pública NandBank: identidade, FX, contas, balcão, 2PC, gestão e PWA."""
from __future__ import annotations
import os,io,json,uuid,logging,threading,ssl,time,decimal,hashlib,math
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
from fastapi import FastAPI,Depends,HTTPException,Request,Query
from fastapi.responses import FileResponse,StreamingResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from .db import connect
from .security import password_hash,password_verify,issue_token,bearer,permitted
from .config import REGIONS,CURRENCIES,region_config,branch_details
from .coordinator import call,process,process_local,reconcile_loop,probe_instance

logger=logging.getLogger('nandbank.gateway')
logging.basicConfig(level=logging.INFO)
_stop=threading.Event()
_worker=None
_failover_stop=threading.Event()
_failover_worker=None
_FAILOVER_LOCK=threading.RLock()
_FAILOVER_COOLDOWN_SECONDS=int(os.getenv('FAILOVER_PAUSE_SECONDS','8'))
_FAILOVER_INTERVAL_SECONDS=2.0
_FAILOVER_STARTUP_GRACE_SECONDS=20
_FAILOVER_BOOT_TIME=time.time()
_FAILOVER={
    code:{
        'primary_up':None,'standby_up':None,'primary_failures':0,
        'failover_until':0.0,'last_event':None,'event_at':None,'last_error':''
    } for code in REGIONS
}

def _record_region_probe(code,primary_ok,standby_ok,error=''):
    now=time.time()
    with _FAILOVER_LOCK:
        item=_FAILOVER[code]
        previous=item['primary_up']
        if primary_ok:
            if previous is False:
                item['last_event']='PRIMARY_RECOVERED'
                item['event_at']=datetime.now(timezone.utc).isoformat()
            item['primary_up']=True
            item['primary_failures']=0
        else:
            item['primary_failures']+=1
            if item['primary_failures']>=2:
                if previous is None and now-_FAILOVER_BOOT_TIME<_FAILOVER_STARTUP_GRACE_SECONDS:
                    # Não confundir o arranque dos contentores com uma falha durante o serviço.
                    item['primary_up']=None
                else:
                    if previous is not False:
                        item['failover_until']=max(item['failover_until'],now+_FAILOVER_COOLDOWN_SECONDS)
                        item['last_event']='PRIMARY_DOWN'
                        item['event_at']=datetime.now(timezone.utc).isoformat()
                    item['primary_up']=False
        item['standby_up']=bool(standby_ok)
        item['last_error']=error[:240]

def _probe_region_now(code):
    results={}
    for instance in ('primary','standby'):
        try:
            probe_instance(code,instance)
            results[instance]=True
        except Exception as exc:
            results[instance]=False
            results[instance+'_error']=f'{type(exc).__name__}: {str(exc)[:120]}'
    _record_region_probe(code,results['primary'],results['standby'],
                         results.get('primary_error') or results.get('standby_error') or '')
    return results

def _failover_monitor(stop):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(2,len(REGIONS)*2)) as pool:
        while not stop.wait(_FAILOVER_INTERVAL_SECONDS):
            futures={}
            for code in REGIONS:
                for instance in ('primary','standby'):
                    futures[(code,instance)]=pool.submit(probe_instance,code,instance,1.8)
            results={code:{'primary':False,'standby':False,'errors':[]} for code in REGIONS}
            for (code,instance),future in futures.items():
                try:
                    future.result(timeout=2.2)
                    results[code][instance]=True
                except Exception as exc:
                    results[code]['errors'].append(f'{instance}: {type(exc).__name__}')
            for code,result in results.items():
                _record_region_probe(code,result['primary'],result['standby'],'; '.join(result['errors']))

def _failover_snapshot(code):
    now=time.time()
    with _FAILOVER_LOCK:
        item=dict(_FAILOVER[code])
    primary='UP' if item['primary_up'] is True else 'DOWN' if item['primary_up'] is False else 'CHECKING'
    standby='UP' if item['standby_up'] is True else 'DOWN' if item['standby_up'] is False else 'CHECKING'
    active='primary' if primary=='UP' else 'standby' if standby=='UP' else None
    remaining=max(0,math.ceil(item['failover_until']-now))
    available=active is not None
    if primary=='CHECKING' and standby=='CHECKING':
        status='CHECKING'
        message=f'A verificar a disponibilidade dos servidores de {REGIONS[code]["name"]}.'
    elif not available:
        status='DOWN'
        message=f'Os dois servidores de {REGIONS[code]["name"]} estão indisponíveis. Não é possível efectuar operações.'
    elif primary=='DOWN' and standby=='UP':
        status='FAILOVER'
        message=(f'O servidor principal de {REGIONS[code]["name"]} está em baixo. '
                 f'O servidor secundário assumiu automaticamente.')
        if remaining:
            message+=f' Novas transferências estão temporariamente bloqueadas. Aguarde {remaining} segundos.'
        else:
            message+=' O servidor secundário está a aceitar operações.'
    elif primary=='CHECKING':
        status='CHECKING'
        message=f'A verificar o servidor principal de {REGIONS[code]["name"]}; a instância secundária está disponível.'
    elif remaining:
        status='RECOVERING'
        message=(f'O servidor principal de {REGIONS[code]["name"]} já recuperou. '
                 f'O período de segurança termina dentro de {remaining} segundos.')
    else:
        status='UP'
        message=f'Servidor principal de {REGIONS[code]["name"]} operacional.'
    return {
        'region':code,'name':REGIONS[code]['name'],'status':status,
        'primary_status':primary,'standby_status':standby,
        'active_instance':active,'instance':active,
        'service_available':available,'failover_active':primary=='DOWN',
        'write_blocked':bool(remaining or not available or primary=='CHECKING'),
        'cooldown_remaining':remaining,
        'cooldown_until':datetime.fromtimestamp(item['failover_until'],timezone.utc).isoformat() if item['failover_until'] else None,
        'message':message,'last_event':item['last_event'],'event_at':item['event_at'],
        'diagnostic':item['last_error']
    }

def assert_region_writable(code):
    pending=_node_pending(code)
    if pending and pending['action']=='STOP_PRIMARY':
        raise HTTPException(503,detail=f'{REGIONS[code]["name"]}: manutenção em preparação. Operações temporariamente indisponíveis; aguarde o nó secundário.',headers={'Retry-After':'5'})
    snapshot=_failover_snapshot(code)
    if snapshot['primary_status']=='CHECKING' or snapshot['standby_status']=='CHECKING':
        _probe_region_now(code)
        snapshot=_failover_snapshot(code)
    if snapshot['primary_status']=='CHECKING':
        raise HTTPException(503,
            detail=f'{snapshot["name"]}: a verificar a disponibilidade do servidor principal. Aguarde alguns segundos e tente novamente.',
            headers={'Retry-After':'5'})
    if not snapshot['service_available']:
        raise HTTPException(503,
            detail=f'{snapshot["name"]}: os servidores principal e secundário estão indisponíveis. Aguarde a recuperação.',
            headers={'Retry-After':'60'})
    if snapshot['cooldown_remaining']>0:
        remaining=snapshot['cooldown_remaining']
        raise HTTPException(503,
            detail=(f'{snapshot["name"]}: transacção não concluída. O servidor está em recuperação; '
                    f'aguarde {remaining} segundos e tente novamente. Nenhum valor foi debitado.'),
            headers={'Retry-After':str(remaining)})

def _ensure_nandbank_schema():
    # Migração idempotente: não elimina nem modifica dados bancários preexistentes.
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS virtual_cards (
          id text PRIMARY KEY, account_id text NOT NULL REFERENCES account_registry(id),
          user_id text NOT NULL REFERENCES users(id), region text NOT NULL,
          last4 text NOT NULL, status text NOT NULL DEFAULT 'REQUESTED'
          CHECK(status IN ('REQUESTED','ACTIVE','FROZEN','REJECTED','CANCELLED')),
          created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now(),
          reviewed_by text, reviewed_at timestamptz)""")
        # A suspensão é lógica: nunca apagar contas nem o diário de movimentos.
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'ACTIVE'")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS status_reason text NOT NULL DEFAULT ''")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS status_changed_at timestamptz")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS status_changed_by text")
        c.execute("CREATE INDEX IF NOT EXISTS ix_users_role_region ON users(role,region,branch)")
        c.execute("CREATE INDEX IF NOT EXISTS ix_cards_user ON virtual_cards(user_id)")
        c.execute("""CREATE TABLE IF NOT EXISTS node_control_jobs (
          id text PRIMARY KEY, region text NOT NULL, action text NOT NULL
          CHECK(action IN ('STOP_PRIMARY','START_PRIMARY')),
          reason text NOT NULL, note text NOT NULL DEFAULT '',
          actor_id text NOT NULL REFERENCES users(id),
          status text NOT NULL DEFAULT 'PENDING'
          CHECK(status IN ('PENDING','RUNNING','COMPLETED','FAILED')),
          result text NOT NULL DEFAULT '', created_at timestamptz DEFAULT now(),
          updated_at timestamptz DEFAULT now())""")
        c.execute("CREATE INDEX IF NOT EXISTS ix_node_jobs_status ON node_control_jobs(status,created_at)")


def _node_pending(code):
    with connect() as c:
        return c.execute("""SELECT id,action FROM node_control_jobs
          WHERE region=%s AND status IN ('PENDING','RUNNING')
          ORDER BY created_at DESC LIMIT 1""",(code,)).fetchone()


def _apply_demo_fx_default():
    # Actualiza apenas a taxa de demonstração original; preserva cotações editadas pelo gerente.
    try:
        with connect() as c:
            manual=c.execute("SELECT 1 FROM audit_events WHERE type='FX_MANUAL' AND details->>'currency'='MZN' LIMIT 1").fetchone()
            if not manual:
                c.execute("UPDATE fx_rates SET units_per_eur=70.11,updated_at=now() "
                          "WHERE currency='MZN' AND source='DEMO' AND units_per_eur=70.00")
    except Exception as exc:
        logger.warning('Não foi possível verificar a taxa inicial MZN: %s',exc)

D=lambda x:Decimal(str(x))
def cents(value):
    n=D(value)
    if not n.is_finite() or n<=0:raise HTTPException(400,'O montante deve ser positivo')
    if n>Decimal('10000000000'):raise HTTPException(400,'Montante acima do limite de demonstração')
    minor=n*100
    if minor!=minor.to_integral_value():raise HTTPException(400,'Use no máximo duas casas decimais')
    return int(minor)
def pretty(amount):return f'{Decimal(amount)/100:.2f}'
def audit(actor,kind,details):
    try:
        with connect() as c:c.execute('INSERT INTO audit_events(actor_id,type,details) VALUES (%s,%s,%s)',(actor,kind,json.dumps(details)))
    except Exception as e:logger.error('Falha auditoria: %s',e)

def lookup_account(account_id):
    with connect() as c:
        a=c.execute('SELECT a.id,a.user_id,a.region,a.branch,a.currency,u.status AS owner_status FROM account_registry a JOIN users u ON u.id=a.user_id WHERE a.id=%s',(account_id,)).fetchone()
    if not a:raise HTTPException(404,'Conta não encontrada')
    return a

def guard_account(claims,a,write=False):
    if claims['role']=='client' and a['user_id']!=claims['sub']:raise HTTPException(403,'Conta de outro cliente')
    if claims['role']=='regional_manager' and claims.get('region')!=a['region']:raise HTTPException(403,'Fora da sua região')
    if claims['role'] in ('branch_manager','teller') and claims.get('branch')!=a['branch']:raise HTTPException(403,'Fora da sua filial')

def rate_quote(source,dest,amount_minor,fee_enabled=True):
    if source not in CURRENCIES or dest not in CURRENCIES:raise HTTPException(400,'Moeda não suportada')
    with connect() as c:
        rows=c.execute('SELECT currency,units_per_eur,source,updated_at FROM fx_rates WHERE currency IN (%s,%s)',(source,dest)).fetchall()
    r={a['currency']:a for a in rows}
    if len(r)!=(1 if source==dest else 2):raise HTTPException(503,'Taxa de câmbio indisponível')
    rate=D(r[dest]['units_per_eur'])/D(r[source]['units_per_eur'])
    fee=(D(amount_minor)*D('0.01')).quantize(Decimal('1'),ROUND_HALF_UP) if fee_enabled else D(0)
    converted=(D(amount_minor)*rate).quantize(Decimal('1'),ROUND_HALF_UP)
    if converted<=0:raise HTTPException(400,'Montante inferior à unidade monetária mínima')
    return {
        'source_currency':source,'destination_currency':dest,'amount_minor':amount_minor,
        'fee_minor':int(fee),'total_debit_minor':int(D(amount_minor)+fee),
        'credit_minor':int(converted),'rate':str(rate.quantize(D('0.00000001'),ROUND_HALF_UP)),
        'source_amount':pretty(amount_minor),'fee':pretty(fee),
        'total_debit':pretty(D(amount_minor)+fee),'recipient_amount':pretty(converted),
        'fx_source':'DEMO' if r[source]['source']=='DEMO' or r[dest]['source']=='DEMO' else 'EXTERNAL',
        'updated_at':max(r[source]['updated_at'],r[dest]['updated_at']).isoformat(),
        'notice':'Moedas e cotações de simulação: não utilizar para transacções reais.'}

def seed_user(email,name,role,password,region=None,branch=None):
    if not password:return
    with connect() as c:
        existing=c.execute('SELECT 1 FROM users WHERE email=%s',(email.lower(),)).fetchone()
        if not existing:
            c.execute('INSERT INTO users(id,email,name,password_hash,role,region,branch) VALUES (%s,%s,%s,%s,%s,%s,%s)',(str(uuid.uuid4()),email.lower(),name,password_hash(password),role,region,branch))
            logger.warning('Criado perfil demonstrativo: %s',email)

@asynccontextmanager
async def lifespan(app:FastAPI):
    _ensure_nandbank_schema()
    _apply_demo_fx_default()
    seed_user('admin@globalscale.local','Gerente Global','global_manager',os.getenv('ADMIN_PASSWORD'))
    seed_user('regional.eu@globalscale.local','Gerente Europa','regional_manager',os.getenv('REGIONAL_PASSWORD'),'eu')
    for code,name in [('af','África'),('as','Ásia'),('na','América do Norte'),('sa','América do Sul'),('oc','Oceânia')]:
        seed_user(f'regional.{code}@globalscale.local',f'Gerente {name}','regional_manager',os.getenv('MANAGER_'+code.upper()+'_PASSWORD'),code)
    seed_user('filial.maputo@globalscale.local','Gerente Filial Maputo','branch_manager',os.getenv('BRANCH_PASSWORD'),'af','MZ-MPM')
    seed_user('balcao.maputo@globalscale.local','Operador Maputo','teller',os.getenv('TELLER_PASSWORD'),'af','MZ-MPM')
    # Alias NandBank na instalação nova; antigas contas @globalscale.local continuam válidas.
    seed_user('admin@nandbank.local','Gerente Global NandBank','global_manager',os.getenv('ADMIN_PASSWORD'))
    seed_user('regional.eu@nandbank.local','Gerente Europa NandBank','regional_manager',os.getenv('REGIONAL_PASSWORD'),'eu')
    for code,name in [('af','África'),('as','Ásia'),('na','América do Norte'),('sa','América do Sul'),('oc','Oceânia')]:
        seed_user(f'regional.{code}@nandbank.local',f'Gerente {name} NandBank','regional_manager',os.getenv('MANAGER_'+code.upper()+'_PASSWORD'),code)
    seed_user('filial.maputo@nandbank.local','Gerente Filial Maputo','branch_manager',os.getenv('BRANCH_PASSWORD'),'af','MZ-MPM')
    seed_user('balcao.maputo@nandbank.local','Operador Maputo','teller',os.getenv('TELLER_PASSWORD'),'af','MZ-MPM')
    _stop.clear()
    _failover_stop.clear()
    global _worker,_failover_worker
    _worker=threading.Thread(target=reconcile_loop,args=(_stop,),daemon=True,name='2pc-recovery')
    _worker.start()
    _failover_worker=threading.Thread(target=_failover_monitor,args=(_failover_stop,),daemon=True,name='failover-monitor')
    _failover_worker.start()
    yield
    _stop.set()
    _failover_stop.set()

app=FastAPI(title='NandBank — API Bancária Distribuída',version='1.0.0',lifespan=lifespan)

@app.middleware('http')
async def security_headers(request,call_next):
    r=await call_next(request)
    r.headers['X-Content-Type-Options']='nosniff'
    r.headers['X-Frame-Options']='DENY'
    r.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    r.headers['Cache-Control']='no-store'
    return r

class Register(BaseModel):
    name:str=Field(min_length=3,max_length=120)
    email:str=Field(min_length=5,max_length=180)
    password:str=Field(min_length=12,max_length=200)
    branch:str
    currency:str|None=None

class AdditionalAccount(BaseModel):
    branch:str;currency:str|None=None

class Login(BaseModel):
    email:str;password:str

class CustomerStatusChange(BaseModel):
    status:str
    reason:str=Field(min_length=5,max_length=300)

class CustomerUpdate(BaseModel):
    name:str=Field(min_length=3,max_length=120)
    email:str=Field(min_length=5,max_length=180)


class Transfer(BaseModel):
    source_id:str;destination_id:str
    amount:str
    idempotency_key:str=Field(min_length=8,max_length=128)
    note:str=''

class TellerOperation(BaseModel):
    account_id:str;amount:str;currency:str
    idempotency_key:str=Field(min_length=8,max_length=128)

class FxRateUpdate(BaseModel):
    currency:str;units_per_eur:str


# ---- Cartões virtuais académicos; não são cartões Visa/Mastercard, PAN ou CVV reais. ----
class CardRequest(BaseModel):
    account_id:str
class CardDecision(BaseModel):
    approved:bool
class NodeAction(BaseModel):
    action:str
    reason:str
    note:str=''

def _card_row(card_id):
    with connect() as c:
        row=c.execute("""SELECT v.*,u.name AS holder_name,a.currency,a.branch
          FROM virtual_cards v JOIN users u ON u.id=v.user_id
          JOIN account_registry a ON a.id=v.account_id WHERE v.id=%s""",(card_id,)).fetchone()
    if not row:raise HTTPException(404,'Cartão não encontrado')
    return row

@app.get('/api/cards')
def client_cards(user=Depends(bearer)):
    if user['role']!='client':raise HTTPException(403,'Apenas clientes')
    with connect() as c:
        return c.execute("""SELECT v.*,a.currency,a.branch,u.name AS holder_name
         FROM virtual_cards v JOIN account_registry a ON a.id=v.account_id
         JOIN users u ON u.id=v.user_id WHERE v.user_id=%s
         ORDER BY v.created_at DESC""",(user['sub'],)).fetchall()

@app.post('/api/cards/request',status_code=201)
def request_card(v:CardRequest,user=Depends(bearer)):
    if user['role']!='client':raise HTTPException(403,'Apenas clientes podem solicitar cartões')
    account=lookup_account(v.account_id)
    guard_account(user,account)
    if account['user_id']!=user['sub']:raise HTTPException(403,'Conta de outro cliente')
    with connect() as c:
        active=c.execute("""SELECT id FROM virtual_cards WHERE account_id=%s
          AND status IN ('REQUESTED','ACTIVE','FROZEN') LIMIT 1""",(account['id'],)).fetchone()
        if active:raise HTTPException(409,'Já existe um cartão ou pedido activo para esta conta')
        card_id=str(uuid.uuid4())
        last4=str(int.from_bytes(os.urandom(2),'big')%10000).zfill(4)
        c.execute("""INSERT INTO virtual_cards (id,account_id,user_id,region,last4)
          VALUES (%s,%s,%s,%s,%s)""",(card_id,account['id'],user['sub'],account['region'],last4))
    audit(user['sub'],'CARD_REQUESTED',{'card_id':card_id,'region':account['region']})
    return {'id':card_id,'status':'REQUESTED','message':'Pedido enviado ao gerente regional'}

@app.get('/api/admin/cards')
def pending_cards(user=Depends(bearer)):
    permitted(user,'regional_manager')
    with connect() as c:
        if user['role']=='global_manager':
            return c.execute("""SELECT v.*,u.name AS holder_name,u.email,a.branch,a.currency
             FROM virtual_cards v JOIN users u ON u.id=v.user_id
             JOIN account_registry a ON a.id=v.account_id ORDER BY v.created_at DESC LIMIT 200""").fetchall()
        return c.execute("""SELECT v.*,u.name AS holder_name,u.email,a.branch,a.currency
             FROM virtual_cards v JOIN users u ON u.id=v.user_id
             JOIN account_registry a ON a.id=v.account_id WHERE v.region=%s
             ORDER BY v.created_at DESC LIMIT 200""",(user['region'],)).fetchall()

@app.post('/api/admin/cards/{card_id}/review')
def review_card(card_id:str,v:CardDecision,user=Depends(bearer)):
    permitted(user,'regional_manager')
    row=_card_row(card_id)
    if user['role']=='regional_manager' and row['region']!=user['region']:
        raise HTTPException(403,'Cartão fora da sua região')
    with connect() as c:
        changed=c.execute("""UPDATE virtual_cards SET status=%s,reviewed_by=%s,
          reviewed_at=now(),updated_at=now() WHERE id=%s AND status='REQUESTED' RETURNING id""",
          ('ACTIVE' if v.approved else 'REJECTED',user['sub'],card_id)).fetchone()
        if not changed:raise HTTPException(409,'Pedido já analisado')
    audit(user['sub'],'CARD_APPROVED' if v.approved else 'CARD_REJECTED',{'card_id':card_id})
    return {'ok':True,'status':'ACTIVE' if v.approved else 'REJECTED'}

@app.post('/api/cards/{card_id}/{action}')
def card_toggle(card_id:str,action:str,user=Depends(bearer)):
    if action not in ('freeze','unfreeze'):raise HTTPException(404,'Operação inválida')
    if user['role']!='client':raise HTTPException(403,'Apenas o titular')
    row=_card_row(card_id)
    if row['user_id']!=user['sub']:raise HTTPException(403,'Cartão de outro cliente')
    before,after=('ACTIVE','FROZEN') if action=='freeze' else ('FROZEN','ACTIVE')
    with connect() as c:
        changed=c.execute("""UPDATE virtual_cards SET status=%s,updated_at=now()
          WHERE id=%s AND status=%s RETURNING id""",(after,card_id,before)).fetchone()
        if not changed:raise HTTPException(409,'O cartão não está no estado necessário')
    audit(user['sub'],'CARD_'+action.upper(),{'card_id':card_id})
    return {'ok':True,'status':after}

# Gestão de nós: o backend NÃO acede ao socket Docker.
# O agente limitado no próprio Windows executa apenas stop/start dos seis serviços aprovados.
_NODE_REASONS={'MAINTENANCE','FAULT','SECURITY','UPGRADE','FAILOVER_TEST','OTHER'}
_AGENT_LAST_SEEN=0.0

def _agent_authorize(x_agent_key:str|None):
    import secrets
    expected=os.getenv('CONTROL_AGENT_KEY','')
    if not expected or not x_agent_key or not secrets.compare_digest(x_agent_key,expected):
        raise HTTPException(403,'Agente não autorizado')

@app.get('/api/admin/node-actions')
def admin_node_actions(user=Depends(bearer)):
    permitted(user,'regional_manager')
    with connect() as c:
        if user['role']=='global_manager':
            rows=c.execute('SELECT * FROM node_control_jobs ORDER BY created_at DESC LIMIT 60').fetchall()
        else:
            rows=c.execute('SELECT * FROM node_control_jobs WHERE region=%s ORDER BY created_at DESC LIMIT 60',(user['region'],)).fetchall()
    return {'agent_online':time.time()-_AGENT_LAST_SEEN<20,'jobs':rows}

@app.post('/api/admin/nodes/{code}/action',status_code=202)
def manage_node(code:str,v:NodeAction,user=Depends(bearer)):
    permitted(user,'regional_manager')
    if code not in REGIONS:raise HTTPException(404,'Região inexistente')
    if user['role']=='regional_manager' and user['region']!=code:
        raise HTTPException(403,'Fora da sua região')
    if v.action not in ('STOP_PRIMARY','START_PRIMARY') or v.reason not in _NODE_REASONS:
        raise HTTPException(400,'Acção ou motivo inválido')
    if time.time()-_AGENT_LAST_SEEN>=20:
        raise HTTPException(503,'Agente Windows não está ligado. Inicie o agente no PC servidor.')
    if v.action=='STOP_PRIMARY':
        snap=_failover_snapshot(code)
        if snap['standby_status']!='UP':raise HTTPException(409,'O nó secundário não está disponível para assumir')
    job_id=str(uuid.uuid4())
    with connect() as c:
        existing=c.execute("""SELECT id FROM node_control_jobs WHERE region=%s AND status IN ('PENDING','RUNNING')
          LIMIT 1""",(code,)).fetchone()
        if existing:raise HTTPException(409,'Já existe uma intervenção em curso')
        c.execute("""INSERT INTO node_control_jobs(id,region,action,reason,note,actor_id)
            VALUES (%s,%s,%s,%s,%s,%s)""",(job_id,code,v.action,v.reason,v.note[:300],user['sub']))
    audit(user['sub'],'NODE_ACTION_REQUESTED',{'id':job_id,'region':code,'action':v.action,'reason':v.reason})
    return {'id':job_id,'status':'PENDING','message':'Intervenção registada. Agente Windows irá executar a acção.'}

@app.get('/api/agent/jobs')
def agent_jobs(x_agent_key:str|None=__import__('fastapi').Header(default=None)):
    _agent_authorize(x_agent_key)
    global _AGENT_LAST_SEEN
    _AGENT_LAST_SEEN=time.time()
    with connect() as c:
        rows=c.execute("""SELECT id,region,action,reason FROM node_control_jobs
            WHERE status='PENDING' ORDER BY created_at LIMIT 3""").fetchall()
    return rows

class AgentResult(BaseModel):
    ok:bool
    result:str=''

@app.post('/api/agent/jobs/{job_id}/result')
def agent_result(job_id:str,v:AgentResult,x_agent_key:str|None=__import__('fastapi').Header(default=None)):
    _agent_authorize(x_agent_key)
    with connect() as c:
        changed=c.execute("""UPDATE node_control_jobs SET status=%s,result=%s,updated_at=now()
          WHERE id=%s AND status IN ('PENDING','RUNNING') RETURNING region,action""",
          ('COMPLETED' if v.ok else 'FAILED',v.result[:500],job_id)).fetchone()
    if not changed:raise HTTPException(404,'Intervenção não encontrada ou já concluída')
    audit(None,'NODE_ACTION_RESULT',{'id':job_id,'region':changed['region'],'ok':v.ok})
    return {'ok':True}

@app.get('/api/health')
def health():return {'status':'ok','app':'NandBank','timestamp':datetime.now(timezone.utc).isoformat()}

@app.get('/api/config')
def configuration():
    return {'name':'NandBank','regions':region_config(),'currencies':list(CURRENCIES),'notice':'Sistema financeiro académico com dinheiro fictício e câmbios de demonstração.'}

@app.get('/api/failover/status')
def failover_status(user=Depends(bearer)):
    if user['role'] in ('regional_manager','branch_manager','teller'):
        allowed=[user['region']]
    else:
        allowed=list(REGIONS)
    return [_failover_snapshot(code) for code in allowed]

@app.post('/api/auth/register')
def register(v:Register):
    b=branch_details(v.branch)
    if not b:raise HTTPException(400,'Filial inválida')
    currency=b['suggested_currency']
    if currency not in CURRENCIES:raise HTTPException(400,'Moeda regional não suportada nesta versão')
    assert_region_writable(b['region'])
    if not any(x.isupper() for x in v.password) or not any(x.islower() for x in v.password) or not any(x.isdigit() for x in v.password):
        raise HTTPException(400,'Palavra-passe: 12 caracteres com maiúscula, minúscula e número')
    email=v.email.strip().lower()
    if '@' not in email or '.' not in email.split('@')[-1]:raise HTTPException(400,'Email inválido')
    user_id=str(uuid.uuid4());acc_id=str(uuid.uuid4())
    with connect() as c:
        c.execute('BEGIN')
        try:
            c.execute('INSERT INTO users(id,email,name,password_hash,role,region,branch) VALUES (%s,%s,%s,%s,%s,%s,%s)',(user_id,email,v.name.strip(),password_hash(v.password),'client',b['region'],v.branch))
            c.execute('INSERT INTO account_registry(id,user_id,region,branch,currency) VALUES (%s,%s,%s,%s,%s)',(acc_id,user_id,b['region'],v.branch,currency))
            call(b['region'],'/internal/accounts',{'id':acc_id,'owner_id':user_id,'branch':v.branch,'currency':currency})
            c.execute('COMMIT')
        except Exception as exc:
            c.execute('ROLLBACK')
            from psycopg.errors import UniqueViolation
            if isinstance(exc,UniqueViolation):raise HTTPException(409,'Email já registado')
            raise
    audit(user_id,'USER_REGISTERED',{'region':b['region'],'branch':v.branch,'account_id':acc_id})
    return {'ok':True,'account_id':acc_id,'user_id':user_id,'message':'Conta criada com saldo inicial zero'}

@app.post('/api/accounts')
def additional_account(v:AdditionalAccount,user=Depends(bearer)):
    if user['role']!='client':raise HTTPException(403,'Apenas clientes criam contas pessoais')
    b=branch_details(v.branch)
    if not b:raise HTTPException(400,'Filial inválida')
    currency=b['suggested_currency']
    if currency not in CURRENCIES:raise HTTPException(400,'Moeda regional não suportada nesta versão')
    assert_region_writable(b['region'])
    account_id=str(uuid.uuid4())
    with connect() as c:
        c.execute('BEGIN')
        try:
            c.execute('INSERT INTO account_registry(id,user_id,region,branch,currency) VALUES (%s,%s,%s,%s,%s)',(account_id,user['sub'],b['region'],v.branch,currency))
            call(b['region'],'/internal/accounts',{'id':account_id,'owner_id':user['sub'],'branch':v.branch,'currency':currency})
            c.execute('COMMIT')
        except Exception:
            c.execute('ROLLBACK')
            raise
    audit(user['sub'],'ACCOUNT_CREATED',{'account_id':account_id,'branch':v.branch})
    return {'ok':True,'account_id':account_id,'balance_minor':0}

@app.post('/api/auth/login')
def login(v:Login):
    with connect() as c:u=c.execute('SELECT * FROM users WHERE email=%s',(v.email.strip().lower(),)).fetchone()
    if not u or not password_verify(v.password,u['password_hash']):raise HTTPException(401,'Email ou palavra-passe inválidos')
    if u.get('status','ACTIVE')!='ACTIVE':
        raise HTTPException(403,{'EXPIRED':'Conta expirada!','SUSPENDED':'Conta suspensa!','SUSPECT':'Conta suspeita!'}.get(u['status'],'Conta indisponível!'))
    return {'access_token':issue_token(u['id'],u['role'],u['region'],u['branch']),'token_type':'bearer','role':u['role'],'name':u['name']}

@app.get('/api/me')
def me(user=Depends(bearer)):
    with connect() as c:
        u=c.execute('SELECT id,email,name,role,region,branch FROM users WHERE id=%s',(user['sub'],)).fetchone()
        accounts=c.execute('SELECT id,region,branch,currency FROM account_registry WHERE user_id=%s ORDER BY created_at',(user['sub'],)).fetchall() if user['role']=='client' else []
    if not u:raise HTTPException(401,'Conta inválida')
    results=[]
    for a in accounts:
        try:
            live=call(a['region'],'/internal/accounts/'+a['id'],method='GET')
            results.append({**a,'balance_minor':live['balance_minor'],'balance':pretty(live['balance_minor'])})
        except Exception:
            results.append({**a,'balance_minor':None,'balance':None,'status':'INDETERMINADO'})
    return {'user':u,'accounts':results}

@app.get('/api/accounts/lookup/{account_id}')
def account_lookup(account_id:str,user=Depends(bearer)):
    a=lookup_account(account_id)
    with connect() as c:
        owner=c.execute('SELECT name FROM users WHERE id=%s',(a['user_id'],)).fetchone()
    name=owner['name'] if owner else 'Beneficiário'
    return {'account_id':a['id'],'beneficiary':name,'region':a['region'],'branch':a['branch'],'currency':a['currency']}

@app.get('/api/accounts/{account_id}')
def account_info(account_id:str,user=Depends(bearer)):
    a=lookup_account(account_id);guard_account(user,a)
    live=call(a['region'],'/internal/accounts/'+account_id,method='GET')
    return {**a,**live,'balance':pretty(live['balance_minor'])}

def _demo_digits(seed,length):
    raw=hashlib.sha256(seed.encode('utf-8')).hexdigest()
    digits=''.join(str(int(ch,16)%10) for ch in raw)
    while len(digits)<length:
        raw=hashlib.sha256(raw.encode()).hexdigest()
        digits+=''.join(str(int(ch,16)%10) for ch in raw)
    return digits[:length]

def _make_iban(country,bban):
    rearranged=bban+country+'00'
    numeric=''.join(str(ord(ch)-55) if ch.isalpha() else ch for ch in rearranged.upper())
    check=98-(int(numeric)%97)
    return f'{country}{check:02d}{bban}'

@app.get('/api/accounts/{account_id}/details')
def account_details(account_id:str,user=Depends(bearer)):
    a=lookup_account(account_id);guard_account(user,a)
    live=call(a['region'],'/internal/accounts/'+account_id,method='GET')
    with connect() as c:
        owner=c.execute('SELECT name FROM users WHERE id=%s',(a['user_id'],)).fetchone()
    branch=branch_details(a['branch'])
    country=branch['country'] if branch else '—'
    country_codes={'Moçambique':'MZ','Portugal':'PT','Alemanha':'DE','França':'FR',
                   'Espanha':'ES','Itália':'IT','Reino Unido':'GB'}
    country_code=country_codes.get(country,'MZ')
    digits=_demo_digits('GlobalScale:'+account_id,24)
    nib=('9'+_demo_digits('NIB:'+account_id,20)) if country in ('Moçambique','Portugal') else None
    iban=_make_iban('PT',nib) if country=='Portugal' and nib else None
    swift='GSCB'+country_code+'GSXXX'
    return {
        'account_id':a['id'],'account_number':'GS'+digits[:12],
        'owner_name':owner['name'] if owner else 'Titular',
        'bank_name':'GlobalScale Bank (simulação académica)',
        'country':country,'region':REGIONS[a['region']]['name'],
        'branch':a['branch'],'branch_name':branch['city'] if branch else a['branch'],
        'currency':live['currency'],'balance_minor':live['balance_minor'],
        'balance':pretty(live['balance_minor']),'account_type':'Conta à ordem',
        'status':'Activa','nib':nib,'iban':iban,'swift_bic':swift,
        'notice':'Todos os identificadores bancários apresentados são fictícios e não podem ser usados para pagamentos reais.'
    }

@app.get('/api/accounts/{account_id}/ledger')
def account_ledger(account_id:str,user=Depends(bearer)):
    a=lookup_account(account_id);guard_account(user,a)
    return call(a['region'],'/internal/ledger/'+account_id,method='GET')

@app.get('/api/fx/rates')
def fx_rates():
    with connect() as c:return c.execute('SELECT currency,units_per_eur::text,source,updated_at FROM fx_rates ORDER BY currency').fetchall()

@app.get('/api/fx/quote')
def fx_quote(source:str,destination:str,amount:str):
    return rate_quote(source,destination,cents(amount))

@app.post('/api/transfers')
def transfer(v:Transfer,user=Depends(bearer)):
    if user['role']!='client':raise HTTPException(403,'Transferências pessoais exigem titular autenticado')
    a=lookup_account(v.source_id);b=lookup_account(v.destination_id)
    guard_account(user,a,write=True)
    if a['id']==b['id']:raise HTTPException(400,'Escolhe contas diferentes')
    amount=cents(v.amount);quote=rate_quote(a['currency'],b['currency'],amount)
    with connect() as c:
        current=c.execute('SELECT * FROM transfers WHERE actor_id=%s AND request_key=%s',(user['sub'],v.idempotency_key)).fetchone()
        if current:
            if current['source_id']!=a['id'] or current['destination_id']!=b['id'] or current['amount_minor']!=amount:
                raise HTTPException(409,'Chave de idempotência já usada com outros dados')
            tx_id=current['id']
            if current['status'] not in ('COMMITTED','ABORTED','DECISION_COMMIT','DECISION_ABORT','PREPARING'):
                assert_region_writable(a['region'])
                assert_region_writable(b['region'])
        else:
            if a.get('owner_status','ACTIVE')!='ACTIVE' or b.get('owner_status','ACTIVE')!='ACTIVE':
                raise HTTPException(403,'Origem ou destino com conta suspensa, suspeita ou expirada')
            assert_region_writable(a['region'])
            assert_region_writable(b['region'])
            tx_id=str(uuid.uuid4())
            c.execute('''INSERT INTO transfers(id,actor_id,request_key,source_id,destination_id,source_region,dest_region,source_currency,dest_currency,amount_minor,fee_minor,credit_minor,rate_text,status,note)
              VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'NEW',%s)''',
              (tx_id,user['sub'],v.idempotency_key,a['id'],b['id'],a['region'],b['region'],a['currency'],b['currency'],amount,quote['fee_minor'],quote['credit_minor'],quote['rate'],v.note[:400]))
    result=process_local(tx_id) if a['region']==b['region'] else process(tx_id)
    audit(user['sub'],'TRANSFER_ATTEMPT',{'tx_id':tx_id,'result':result['status']})
    return {**result,'quote':quote}

@app.get('/api/transfers/{tx_id}')
def transfer_status(tx_id:str,user=Depends(bearer)):
    with connect() as c:t=c.execute('SELECT * FROM transfers WHERE id=%s',(tx_id,)).fetchone()
    if not t:raise HTTPException(404,'Transferência inexistente')
    if user['role']=='client' and t['actor_id']!=user['sub']:raise HTTPException(403,'Sem acesso')
    if user['role']=='regional_manager' and user.get('region') not in (t['source_region'],t['dest_region']):raise HTTPException(403,'Sem acesso')
    return {**t,'amount':pretty(t['amount_minor']),'fee':pretty(t['fee_minor']),'credited':pretty(t['credit_minor'])}

@app.get('/api/transfers')
def my_transfers(user=Depends(bearer)):
    with connect() as c:
        if user['role']=='client':return c.execute('SELECT * FROM transfers WHERE actor_id=%s ORDER BY created_at DESC LIMIT 100',(user['sub'],)).fetchall()
        if user['role']=='global_manager':return c.execute('SELECT * FROM transfers ORDER BY created_at DESC LIMIT 200').fetchall()
        if user['role']=='regional_manager':return c.execute('SELECT * FROM transfers WHERE source_region=%s OR dest_region=%s ORDER BY created_at DESC LIMIT 200',(user['region'],user['region'])).fetchall()
        return c.execute('''SELECT * FROM transfers WHERE source_id IN
            (SELECT id FROM account_registry WHERE branch=%s)
            OR destination_id IN (SELECT id FROM account_registry WHERE branch=%s)
            ORDER BY created_at DESC LIMIT 200''',(user['branch'],user['branch'])).fetchall()

@app.post('/api/teller/deposit')
def teller_deposit(v:TellerOperation,user=Depends(bearer)):
    return teller_execute(v,user,'DEPOSIT')

@app.post('/api/teller/withdraw')
def teller_withdraw(v:TellerOperation,user=Depends(bearer)):
    return teller_execute(v,user,'WITHDRAW')

def teller_execute(v,user,operation):
    permitted(user,'teller','branch_manager','regional_manager')
    a=lookup_account(v.account_id);guard_account(user,a,True)
    assert_region_writable(a['region'])
    if v.currency not in CURRENCIES:raise HTTPException(400,'Moeda inválida')
    if operation=='WITHDRAW' and v.currency!=a['currency']:
        raise HTTPException(400,'Levantamento apenas na moeda da conta nesta versão')
    amount=cents(v.amount);quote=rate_quote(v.currency,a['currency'],amount,False)
    # O ID fornecido pelo operador é determinístico para retries, em vez de criar novos depósitos.
    with connect() as c:
        old=c.execute('SELECT * FROM operation_registry WHERE id=%s',(v.idempotency_key,)).fetchone()
        if old and (old['account_id']!=v.account_id or old['amount_minor']!=amount or old['deposit_currency']!=v.currency or old['operation_type']!=operation):
            raise HTTPException(409,'Identificador de operação reutilizado com dados diferentes')
        if not old:
            if a.get('owner_status','ACTIVE')!='ACTIVE':
                raise HTTPException(403,'Conta suspensa, suspeita ou expirada: operações de balcão bloqueadas')
            c.execute('''INSERT INTO operation_registry(id,actor_id,account_id,operation_type,amount_minor,deposit_currency,credited_minor,account_currency,rate_text,status)
              VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING')''',
              (v.idempotency_key,user['sub'],a['id'],operation,amount,v.currency,quote['credit_minor'],a['currency'],quote['rate']))
    result=call(a['region'],'/internal/local-operation',{
        'operation_id':v.idempotency_key,'account_id':a['id'],'kind':operation,
        'amount_minor':quote['credit_minor'],'detail':{'paid_currency':v.currency,'paid_minor':amount,'fx_rate':quote['rate']}})
    with connect() as c:c.execute("UPDATE operation_registry SET status='COMMITTED' WHERE id=%s",(v.idempotency_key,))
    audit(user['sub'],operation,{'account_id':a['id'],'operation_id':v.idempotency_key})
    return {'ok':True,'operation_id':v.idempotency_key,'balance_minor':result['balance_minor'],'quote':quote}

@app.get('/api/admin/stats')
def admin_stats(user=Depends(bearer)):
    permitted(user,'regional_manager','branch_manager','teller')
    with connect() as c:
        if user['role']=='global_manager':
            users=c.execute("SELECT count(*) AS n FROM users WHERE role='client'").fetchone()['n']
            transfers=c.execute("SELECT status,count(*) AS n FROM transfers GROUP BY status").fetchall()
            deposits=c.execute("SELECT operation_type,count(*) AS n FROM operation_registry GROUP BY operation_type").fetchall()
        elif user['role']=='regional_manager':
            users=c.execute("SELECT count(*) AS n FROM users WHERE role='client' AND region=%s",(user['region'],)).fetchone()['n']
            transfers=c.execute('SELECT status,count(*) AS n FROM transfers WHERE source_region=%s OR dest_region=%s GROUP BY status',(user['region'],user['region'])).fetchall()
            deposits=c.execute('SELECT operation_type,count(*) AS n FROM operation_registry WHERE account_id IN (SELECT id FROM account_registry WHERE region=%s) GROUP BY operation_type',(user['region'],)).fetchall()
        else:
            users=c.execute("SELECT count(*) AS n FROM users WHERE role='client' AND branch=%s",(user['branch'],)).fetchone()['n']
            transfers=c.execute('SELECT status,count(*) AS n FROM transfers WHERE source_id IN (SELECT id FROM account_registry WHERE branch=%s) GROUP BY status',(user['branch'],)).fetchall()
            deposits=c.execute('SELECT operation_type,count(*) AS n FROM operation_registry WHERE account_id IN (SELECT id FROM account_registry WHERE branch=%s) GROUP BY operation_type',(user['branch'],)).fetchall()
    return {'clients':users,'transfers':{x['status']:x['n'] for x in transfers},
            'operations':{x['operation_type']:x['n'] for x in deposits},'regions':len(REGIONS)}

@app.get('/api/admin/nodes')
def node_status(user=Depends(bearer)):
    permitted(user,'regional_manager','branch_manager','teller')
    allowed=[user['region']] if user['role'] in ('regional_manager','branch_manager','teller') else list(REGIONS)
    result=[]
    for code in allowed:
        snapshot=_failover_snapshot(code)
        stats={}
        if snapshot['service_available']:
            try:stats=call(code,'/internal/stats',method='GET')
            except Exception:pass
        result.append({**snapshot,**stats})
    return result

@app.get('/api/admin/operations')
def admin_operations(user=Depends(bearer)):
    permitted(user,'regional_manager','branch_manager','teller')
    with connect() as c:
        if user['role']=='global_manager':
            return c.execute('''SELECT o.*,r.region,r.branch FROM operation_registry o JOIN account_registry r ON r.id=o.account_id ORDER BY o.created_at DESC LIMIT 200''').fetchall()
        if user['role']=='regional_manager':
            return c.execute('''SELECT o.*,r.region,r.branch FROM operation_registry o JOIN account_registry r ON r.id=o.account_id WHERE r.region=%s ORDER BY o.created_at DESC LIMIT 200''',(user['region'],)).fetchall()
        return c.execute('''SELECT o.*,r.region,r.branch FROM operation_registry o JOIN account_registry r ON r.id=o.account_id WHERE r.branch=%s ORDER BY o.created_at DESC LIMIT 200''',(user['branch'],)).fetchall()

@app.get('/api/admin/accounts')
def admin_accounts(user=Depends(bearer)):
    permitted(user,'regional_manager','branch_manager','teller')
    with connect() as c:
        if user['role']=='global_manager':
            return c.execute('''SELECT a.*,u.name,u.email FROM account_registry a JOIN users u ON u.id=a.user_id ORDER BY a.created_at DESC LIMIT 300''').fetchall()
        if user['role']=='regional_manager':
            return c.execute('''SELECT a.*,u.name,u.email FROM account_registry a JOIN users u ON u.id=a.user_id WHERE a.region=%s ORDER BY a.created_at DESC LIMIT 300''',(user['region'],)).fetchall()
        return c.execute('''SELECT a.*,u.name,u.email FROM account_registry a JOIN users u ON u.id=a.user_id WHERE a.branch=%s ORDER BY a.created_at DESC LIMIT 300''',(user['branch'],)).fetchall()

# Gestão responsável dos clientes. Nunca apagar clientes com histórico financeiro.
CUSTOMER_STATES={'ACTIVE','SUSPENDED','SUSPECT','EXPIRED'}

def _customer_scope(user, customer_id, require_exclusive=False):
    permitted(user,'regional_manager','branch_manager')
    with connect() as c:
        target=c.execute("SELECT id,name,email,role,region,branch,status,status_reason,status_changed_at,created_at FROM users WHERE id=%s AND role='client'",(customer_id,)).fetchone()
        if not target:raise HTTPException(404,'Cliente não encontrado')
        accounts=c.execute('SELECT id,region,branch,currency,created_at FROM account_registry WHERE user_id=%s ORDER BY created_at',(customer_id,)).fetchall()
    if user['role']=='global_manager':return target,accounts
    scoped=[a for a in accounts if (a['region']==user.get('region') if user['role']=='regional_manager' else a['branch']==user.get('branch'))]
    if not scoped:raise HTTPException(403,'Cliente fora do seu âmbito')
    if require_exclusive and len(scoped)!=len(accounts):
        raise HTTPException(403,'O cliente possui contas fora do seu âmbito; intervenção reservada ao gerente global')
    return target,scoped

@app.get('/api/admin/customers')
def list_customers(user=Depends(bearer)):
    permitted(user,'regional_manager','branch_manager')
    with connect() as c:
        if user['role']=='global_manager':
            rows=c.execute("SELECT u.id,u.name,u.email,COALESCE(MIN(a.region),u.region) AS region,COALESCE(MIN(a.branch),u.branch) AS branch,ARRAY_AGG(DISTINCT a.region) FILTER (WHERE a.region IS NOT NULL) AS regions,u.status,u.status_reason,u.status_changed_at,u.created_at,count(a.id) AS account_count FROM users u LEFT JOIN account_registry a ON a.user_id=u.id WHERE u.role='client' GROUP BY u.id ORDER BY MIN(a.region) NULLS LAST,u.created_at DESC LIMIT 500").fetchall()
        else:
            field='a.region' if user['role']=='regional_manager' else 'a.branch'
            scope=user['region'] if user['role']=='regional_manager' else user['branch']
            rows=c.execute(f"SELECT u.id,u.name,u.email,MIN(a.region) AS region,MIN(a.branch) AS branch,ARRAY_AGG(DISTINCT a.region) AS regions,u.status,u.status_reason,u.status_changed_at,u.created_at,count(DISTINCT a.id) AS account_count FROM users u JOIN account_registry a ON a.user_id=u.id WHERE u.role='client' AND {field}=%s GROUP BY u.id ORDER BY u.created_at DESC LIMIT 500",(scope,)).fetchall()
    return rows

@app.get('/api/admin/customers/{customer_id}/activity')
def customer_activity(customer_id:str,user=Depends(bearer)):
    target,accounts=_customer_scope(user,customer_id)
    ids=[a['id'] for a in accounts]
    if not ids:return {'customer':target,'accounts':[],'operations':[],'transfers':[],'cards':[]}
    with connect() as c:
        operations=c.execute('SELECT o.* FROM operation_registry o WHERE o.account_id = ANY(%s) ORDER BY o.created_at DESC LIMIT 100',(ids,)).fetchall()
        transfers=c.execute('SELECT t.* FROM transfers t WHERE t.source_id = ANY(%s) OR t.destination_id = ANY(%s) ORDER BY t.created_at DESC LIMIT 100',(ids,ids)).fetchall()
        cards=c.execute('SELECT id,account_id,region,last4,status,created_at,updated_at FROM virtual_cards WHERE account_id = ANY(%s) ORDER BY created_at DESC LIMIT 100',(ids,)).fetchall()
    return {'customer':target,'accounts':accounts,'operations':operations,'transfers':transfers,'cards':cards}

@app.patch('/api/admin/customers/{customer_id}')
def update_customer(customer_id:str,v:CustomerUpdate,user=Depends(bearer)):
    target,_=_customer_scope(user,customer_id,require_exclusive=True)
    name=v.name.strip();email=v.email.strip().lower()
    if len(name)<3 or '@' not in email or '.' not in email.split('@')[-1]:
        raise HTTPException(400,'Nome ou email inválido')
    from psycopg.errors import UniqueViolation
    try:
        with connect(autocommit=False) as c:
            c.execute("UPDATE users SET name=%s,email=%s WHERE id=%s AND role='client'",(name,email,customer_id))
    except UniqueViolation:
        raise HTTPException(409,'Este email já pertence a outra conta')
    audit(user['sub'],'CUSTOMER_UPDATED',{'customer_id':customer_id,'old_name':target['name'],'new_name':name,'old_email':target['email'],'new_email':email})
    return {'ok':True,'customer_id':customer_id,'name':name,'email':email}

@app.patch('/api/admin/customers/{customer_id}/status')
def change_customer_status(customer_id:str,v:CustomerStatusChange,user=Depends(bearer)):
    target,_=_customer_scope(user,customer_id,require_exclusive=True)
    status=v.status.strip().upper();reason=v.reason.strip()
    if status not in CUSTOMER_STATES:raise HTTPException(400,'Estado de cliente inválido')
    if len(reason)<5:raise HTTPException(400,'Justificação obrigatória com pelo menos 5 caracteres')
    with connect(autocommit=False) as c:
        c.execute("UPDATE users SET status=%s,status_reason=%s,status_changed_at=now(),status_changed_by=%s WHERE id=%s AND role='client'",(status,reason,user['sub'],customer_id))
    audit(user['sub'],'CUSTOMER_STATUS_CHANGED',{'customer_id':customer_id,'before':target['status'],'after':status,'reason':reason})
    return {'ok':True,'customer_id':customer_id,'status':status,'message':'Estado actualizado. O histórico financeiro foi preservado.'}

class CustomerPermanentDelete(BaseModel):
    confirmation_email:str=Field(min_length=5,max_length=180)

@app.post('/api/admin/customers/{customer_id}/permanent-delete')
def delete_empty_customer(customer_id:str,v:CustomerPermanentDelete,user=Depends(bearer)):
    # Remocao fisica restrita ao gerente global e a contas SEM historico.
    # Clientes com depositos, transferencias ou saldo so podem ser arquivados.
    if user['role'] not in ('global_manager','regional_manager'):
        raise HTTPException(403,'Eliminacao definitiva exige gerente regional ou global')
    target,accounts=_customer_scope(user,customer_id,require_exclusive=True)
    if v.confirmation_email.strip().casefold()!=target['email'].casefold():
        raise HTTPException(400,'Escreva o email exacto para confirmar a eliminacao')
    if len(accounts)!=1:
        raise HTTPException(409,'Eliminacao definitiva limitada a clientes com uma unica conta sem historico')
    a=accounts[0]
    with connect() as c:
        if c.execute('SELECT 1 FROM operation_registry WHERE account_id=%s LIMIT 1',(a['id'],)).fetchone():
            raise HTTPException(409,'Ha operacoes de balcao: utilize Conta expirada')
        if c.execute('SELECT 1 FROM transfers WHERE source_id=%s OR destination_id=%s OR actor_id=%s LIMIT 1',
                     (a['id'],a['id'],customer_id)).fetchone():
            raise HTTPException(409,'Ha transferencias: utilize Conta expirada')
        if c.execute('SELECT 1 FROM virtual_cards WHERE user_id=%s OR account_id=%s LIMIT 1',
                     (customer_id,a['id'])).fetchone():
            raise HTTPException(409,'Ha cartoes: utilize Conta expirada')
    assert_region_writable(a['region'])
    # O participante faz lock, verifica saldo=0 e ausencia de ledger antes de apagar.
    # A chamada e idempotente para permitir repeticao se a resposta se perder.
    call(a['region'],'/internal/accounts/'+a['id']+'/purge-empty-test',{})
    try:
        with connect(autocommit=False) as c:
            # Revalidar as ligacoes globais na transaccao.
            c.execute('SELECT id FROM account_registry WHERE id=%s AND user_id=%s FOR UPDATE',(a['id'],customer_id))
            if c.execute('SELECT 1 FROM operation_registry WHERE account_id=%s LIMIT 1',(a['id'],)).fetchone() or \
               c.execute('SELECT 1 FROM transfers WHERE source_id=%s OR destination_id=%s LIMIT 1',(a['id'],a['id'])).fetchone():
                raise HTTPException(409,'Foi detectada uma operacao concorrente. Recuperacao necessaria.')
            c.execute('DELETE FROM account_registry WHERE id=%s AND user_id=%s',(a['id'],customer_id))
            c.execute("DELETE FROM users WHERE id=%s AND role='client'",(customer_id,))
    except Exception:
        # Compensacao: se a transaccao global falhar, reconstituir a conta regional vazia.
        try:
            call(a['region'],'/internal/accounts',{
                'id':a['id'],'owner_id':customer_id,'branch':a['branch'],'currency':a['currency']})
        except Exception:
            logger.exception('ERRO COMPENSACAO cliente %s conta %s',customer_id,a['id'])
        raise
    audit(user['sub'],'EMPTY_CUSTOMER_PERMANENTLY_DELETED',{
        'customer_id':customer_id,'account_id':a['id'],'email':target['email']})
    return {'ok':True,'deleted':True,'customer_id':customer_id}

@app.post('/api/admin/accounts/normalize-currencies')
def normalize_account_currencies(user=Depends(bearer)):
    if user['role']!='global_manager':
        raise HTTPException(403,'A normalização de moedas exige o Gerente Global')
    with connect() as c:
        rows=c.execute('SELECT id,region,branch,currency FROM account_registry ORDER BY created_at').fetchall()
    converted=[];unchanged=[];failures=[]
    for account in rows:
        branch=branch_details(account['branch'])
        if not branch:
            failures.append({'account_id':account['id'],'reason':'Filial não reconhecida'})
            continue
        expected=branch['suggested_currency']
        try:
            with connect() as c:
                pending_transfer=c.execute("SELECT 1 FROM transfers WHERE (source_id=%s OR destination_id=%s) AND status NOT IN ('COMMITTED','ABORTED') LIMIT 1",(account['id'],account['id'])).fetchone()
                pending_operation=c.execute("SELECT 1 FROM operation_registry WHERE account_id=%s AND status<>'COMMITTED' LIMIT 1",(account['id'],)).fetchone()
            if pending_transfer or pending_operation:
                raise HTTPException(409,'A conta tem operações pendentes; tente normalizar depois da recuperação.')
            assert_region_writable(account['region'])
            live=call(account['region'],'/internal/accounts/'+account['id'],method='GET')
            old_currency=live['currency']
            old_balance=int(live['balance_minor'])
            if old_currency!=expected:
                rate=rate_quote(old_currency,expected,100,False)['rate']
                new_balance=0 if old_balance==0 else rate_quote(old_currency,expected,old_balance,False)['credit_minor']
                operation_id='currency-normalize-'+hashlib.sha256((account['id']+':'+expected).encode()).hexdigest()[:32]
                call(account['region'],'/internal/normalize-currency',{
                    'account_id':account['id'],'currency':expected,
                    'balance_minor':new_balance,'operation_id':operation_id,
                    'details':{'from_currency':old_currency,'from_balance_minor':old_balance,
                               'to_currency':expected,'to_balance_minor':new_balance,
                               'rate':rate,'reason':'Normalização para a moeda definida pela filial'}
                })
                converted.append({'account_id':account['id'],'from':old_currency,'to':expected,
                                  'old_balance_minor':old_balance,'new_balance_minor':new_balance})
            else:
                unchanged.append(account['id'])
            with connect() as c:
                c.execute('UPDATE account_registry SET currency=%s WHERE id=%s',(expected,account['id']))
        except Exception as exc:
            failures.append({'account_id':account['id'],'reason':str(exc)[:220]})
    audit(user['sub'],'CURRENCY_NORMALIZATION',{'converted':len(converted),'unchanged':len(unchanged),'failures':len(failures)})
    return {'converted':converted,'unchanged':len(unchanged),'failures':failures,
            'message':f'{len(converted)} conta(s) convertida(s); {len(unchanged)} já estavam correctas; {len(failures)} falha(s).'}

@app.get('/api/admin/audit')
def admin_audit(user=Depends(bearer)):
    # O diário de auditoria é global: nunca expor operações de outras regiões a um gerente regional.
    permitted(user,'global_manager')
    with connect() as c:return c.execute('SELECT * FROM audit_events ORDER BY id DESC LIMIT 120').fetchall()

@app.post('/api/admin/fx/rates')
def modify_fx(v:FxRateUpdate,user=Depends(bearer)):
    permitted(user,'global_manager')
    if v.currency not in CURRENCIES:raise HTTPException(400,'Moeda inválida')
    rate=D(v.units_per_eur)
    if not rate.is_finite() or rate<=0 or rate>100000:raise HTTPException(400,'Taxa inválida')
    with connect() as c:c.execute("UPDATE fx_rates SET units_per_eur=%s,source='DEMO',updated_at=now() WHERE currency=%s",(rate,v.currency))
    audit(user['sub'],'FX_MANUAL',{'currency':v.currency,'rate':str(rate)})
    return {'ok':True,'notice':'Cotação de demonstração alterada'}

@app.post('/api/admin/fx/sync')
def sync_fx(user=Depends(bearer)):
    permitted(user,'global_manager')
    # Endpoint público de câmbio; apenas actualiza os símbolos presentes na lista interna.
    # Ausência de MZN/GHS numa fonte não substitui as cotações demonstrativas por zero.
    try:
        with httpx.Client(timeout=8.0) as client:
            r=client.get(os.getenv('FX_API_URL','https://api.frankfurter.dev/v1/latest?base=EUR'))
            r.raise_for_status();data=r.json()
        available={key:D(value) for key,value in data.get('rates',{}).items() if key in CURRENCIES and D(value)>0}
        with connect() as c:
            for currency,rate in available.items():
                c.execute("UPDATE fx_rates SET units_per_eur=%s,source='EXTERNAL',updated_at=now() WHERE currency=%s",(rate,currency))
        audit(user['sub'],'FX_EXTERNAL',{'currencies':list(available)})
        return {'updated':list(available),'remaining_demo':[x for x in CURRENCIES if x not in available]}
    except Exception as e:raise HTTPException(503,'Fonte externa indisponível; as taxas de demonstração mantêm-se.')

@app.get('/api/transactions/{tx_id}/receipt.pdf')
def pdf_receipt(tx_id:str,user=Depends(bearer)):
    with connect() as c:t=c.execute('SELECT * FROM transfers WHERE id=%s',(tx_id,)).fetchone()
    if not t:raise HTTPException(404,'Transacção não encontrada')
    if t['status']!='COMMITTED':raise HTTPException(409,'Comprovativo apenas para transacção confirmada')
    if user['role']=='client' and t['actor_id']!=user['sub']:raise HTTPException(403,'Sem permissão')
    if user['role']=='regional_manager' and user.get('region') not in (t['source_region'],t['dest_region']):raise HTTPException(403,'Sem permissão')
    if user['role'] in ('teller','branch_manager'):
        a=lookup_account(t['source_id'])
        guard_account(user,a)
    b=io.BytesIO();c=Canvas(b,pagesize=A4)
    c.setFillColorRGB(.17,.11,.20);c.rect(0,770,595,72,fill=1,stroke=0)
    c.setFillColorRGB(1,1,1);c.setFont('Helvetica-Bold',22);c.drawString(42,798,'NandBank')
    c.setFillColorRGB(0,0,0);c.setFont('Helvetica-Bold',15);c.drawString(42,734,'COMPROVATIVO DE TRANSFERENCIA - SIMULACAO')
    c.setFont('Helvetica',11)
    entries=[('Referencia',t['id']),('Estado','CONFIRMADA'),('Conta origem',t['source_id']),
       ('Conta destino',t['destination_id']),('Regiao origem',t['source_region'].upper()),
       ('Regiao destino',t['dest_region'].upper()),('Enviado',pretty(t['amount_minor'])+' '+t['source_currency']),
       ('Comissao',pretty(t['fee_minor'])+' '+t['source_currency']),
       ('Total debitado',pretty(t['amount_minor']+t['fee_minor'])+' '+t['source_currency']),
       ('Recebido',pretty(t['credit_minor'])+' '+t['dest_currency']),('Cambio',t['rate_text']),('Data',str(t['created_at']))]
    for i,(k,v) in enumerate(entries):
        y=694-i*36;c.setFont('Helvetica-Bold',10);c.drawString(42,y,k);c.setFont('Helvetica',10);c.drawString(200,y,str(v)[:70])
    c.setFont('Helvetica',9);c.drawString(42,100,'Projecto academico. Dinheiro ficticio. Nao e um recibo fiscal nem comprovativo bancario real.')
    c.showPage();c.save();b.seek(0)
    return StreamingResponse(b,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="nandbank-{tx_id}.pdf"'})

# SPA compilada em Docker (Vue 3). Sem CDN nem dependências externas no navegador.
UI=Path('/app/ui')
if UI.exists():app.mount('/static',StaticFiles(directory=UI),name='static')

@app.get('/{path:path}',include_in_schema=False)
def frontend(path:str):
    if path.startswith('api/') or path in ('docs','openapi.json'):
        raise HTTPException(404,'Rota inexistente')
    if path in ('manifest.webmanifest','sw.js','favicon.svg','style.css','theme.css','app.js','lion-mark.png') and (UI/path).is_file():
        return FileResponse(UI/path)
    if (UI/'index.html').is_file():return FileResponse(UI/'index.html')
    return {'message':'Frontend ainda não compilado. Execute o Docker Compose.'}

def run():
    import uvicorn
    uvicorn.run(app,host='0.0.0.0',port=8443,ssl_certfile='/certs/gateway.crt',ssl_keyfile='/certs/gateway.key',workers=1)

if __name__=='__main__':run()
