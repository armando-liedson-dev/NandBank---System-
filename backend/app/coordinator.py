"""Coordenador 2PC durável: decisão persistida ANTES do commit em participantes."""
from __future__ import annotations
import json,logging,time,os,threading,ssl
import httpx
from fastapi import HTTPException
from .config import region_url
from .db import connect
from .security import service_token,hmac_signature

LOG=logging.getLogger('globalscale.2pc')
def _contexto_mtls():
    # httpx 0.28.x: verify como caminho para CA retorna antes de processar cert=.
    # Usar SSLContext com cadeia do cliente carregada, tanto para HAProxy como para Java.
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='/certs/ca.crt')
    ctx.load_cert_chain(certfile='/certs/client.crt', keyfile='/certs/client.key')
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx

CLIENT_ARGS={'verify':_contexto_mtls(), 'timeout':6.0, 'trust_env':False}


def probe_instance(region, instance, timeout=1.8):
    """Verifica directamente uma instância, sem o fallback do HAProxy."""
    if instance not in ('primary', 'standby'):
        raise ValueError('Instância inválida')
    url=f'https://{region}-{instance}:9443/health'
    with httpx.Client(**{**CLIENT_ARGS, 'timeout': timeout}) as client:
        response=client.get(url)
        response.raise_for_status()
        data=response.json()
        if data.get('region') != region or data.get('instance') != instance:
            raise RuntimeError('Resposta de saúde não corresponde à instância consultada')
        return data

def call(region,path,payload=None,method='POST'):
    """mTLS verificado com três caminhos redundantes: HAProxy, principal, standby.

    O encaminhamento directo e usado apenas se o router nao responder; cada
    operacao que pode ser repetida possui idempotencia no backend regional.
    Nunca ignorar TLS, e nunca tratar resposta de negocio 4xx como sucesso.
    """
    endpoints=[('router',region_url(region)),
               ('principal',f'https://{region}-primary:9443'),
               ('reserva',f'https://{region}-standby:9443')]
    headers={'Authorization':'Bearer '+service_token()}
    last=''
    for round_ in range(2):
        for label,base in endpoints:
            try:
                with httpx.Client(**CLIENT_ARGS) as client:
                    response=(client.post(base+path,json=payload,headers=headers)
                              if method=='POST' else client.get(base+path,headers=headers))
                if response.status_code>=400:
                    try:
                        detail=response.json().get('detail','Erro regional')
                    except Exception:
                        detail=response.text[:200]
                    if response.status_code in (502,503,504):
                        last=f'{label}: HTTP {response.status_code}: {detail}'
                        LOG.warning('Falha transitória %s %s: %s',region,label,last)
                        continue
                    raise HTTPException(response.status_code,f'{region.upper()}: {detail}')
                return response.json()
            except (httpx.TransportError,httpx.TimeoutException) as e:
                last=f'{label}: {type(e).__name__}: {str(e)[:150]}'
                LOG.warning('Falha de transporte %s %s %s: %s',region,label,path,last)
        if round_==0:
            time.sleep(1.5)
    raise HTTPException(503,f'{region.upper()}: router, principal e standby indisponíveis ({last[:150]})')

def legacy_check(row):
    payload={'transaction_id':row['id'],'source_region':row['source_region'],'dest_region':row['dest_region'],
             'amount_minor':row['amount_minor'],'currency':row['source_currency']}
    raw=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
    with httpx.Client(**CLIENT_ARGS) as c:
        r=c.post('https://legacy:8090/legacy/validate',content=raw,headers={'Content-Type':'application/json','X-Integrity-HMAC':hmac_signature(raw)})
        r.raise_for_status()
        if not r.json().get('approved'):
            raise HTTPException(409,'Integração legado rejeitou a transacção')

def set_status(c,tx_id,status,error=''):
    c.execute('UPDATE transfers SET status=%s,last_error=%s,updated_at=now() WHERE id=%s',(status,error[:600],tx_id))

def _resolve(c,t,decision):
    failures=[]
    for region,side in ((t['source_region'],'source'),(t['dest_region'],'dest')):
        try:call(region,'/internal/resolve',{'tx_id':t['id'],'side':side,'decision':decision})
        except Exception as e:failures.append(f'{region}-{side}: {str(e)[:160]}')
    if failures:
        set_status(c,t['id'],'DECISION_COMMIT' if decision=='commit' else 'DECISION_ABORT','; '.join(failures))
        return False
    set_status(c,t['id'],'COMMITTED' if decision=='commit' else 'ABORTED')
    return True

def process(tx_id):
    """Idempotente. Advisory lock impede dois coordenadores simultâneos na mesma transferência."""
    with connect() as c:
        lock=c.execute('SELECT pg_try_advisory_lock(hashtext(%s)) AS locked',(tx_id,)).fetchone()['locked']
        if not lock:return {'id':tx_id,'status':'PENDING','note':'Outra instância está a processar'}
        try:
            t=c.execute('SELECT * FROM transfers WHERE id=%s',(tx_id,)).fetchone()
            if not t:raise HTTPException(404,'Transferência não encontrada')
            if t['status'] in ('COMMITTED','ABORTED'):
                return {'id':tx_id,'status':t['status'],'error':t['last_error']}
            if t['status']=='DECISION_COMMIT':
                done=_resolve(c,t,'commit')
                return {'id':tx_id,'status':'COMMITTED' if done else 'PENDING','error':'' if done else 'A concluir compromisso 2PC'}
            if t['status']=='DECISION_ABORT':
                done=_resolve(c,t,'abort')
                return {'id':tx_id,'status':'ABORTED' if done else 'PENDING','error':t['last_error']}
            if t['status']=='PREPARING':
                # Recuperação após interrupção do coordenador: antes de decisão durável, a única opção segura é abortar.
                set_status(c,tx_id,'DECISION_ABORT','Coordenador interrompido durante PREPARE')
                _resolve(c,t,'abort')
                return {'id':tx_id,'status':'ABORTED','error':'Operação interrompida antes da decisão'}
            # Recebido e ainda não preparado: auditoria e validação legado prévias.
            try:
                legacy_check(t)
                set_status(c,tx_id,'PREPARING')
                call(t['source_region'],'/internal/prepare',{
                    'tx_id':tx_id,'side':'source','account_id':t['source_id'],
                    'amount_minor':t['amount_minor']+t['fee_minor'],'currency':t['source_currency'],
                    'details':{'rate':t['rate_text'],'fee_minor':t['fee_minor']}})
                call(t['dest_region'],'/internal/prepare',{
                    'tx_id':tx_id,'side':'dest','account_id':t['destination_id'],
                    'amount_minor':t['credit_minor'],'currency':t['dest_currency'],
                    'details':{'rate':t['rate_text'],'source_region':t['source_region']}})
            except Exception as e:
                LOG.warning('2PC ABORT %s: %s',tx_id,e)
                set_status(c,tx_id,'DECISION_ABORT',str(e))
                resolved=_resolve(c,t,'abort')
                return {'id':tx_id,'status':'ABORTED' if resolved else 'PENDING',
                        'error':str(e) if resolved else 'Cancelamento pendente; o coordenador continuará a recuperar a operação.'}
            # Fronteira crítica: COMMIT durável no diário antes de qualquer commit de participante.
            set_status(c,tx_id,'DECISION_COMMIT')
            done=_resolve(c,t,'commit')
            return {'id':tx_id,'status':'COMMITTED' if done else 'PENDING','error':'' if done else 'Compromisso durável; conclusão em recuperação'}
        finally:
            c.execute('SELECT pg_advisory_unlock(hashtext(%s))',(tx_id,))

def process_local(tx_id):
    with connect() as c:
        lock=c.execute('SELECT pg_try_advisory_lock(hashtext(%s)) AS locked',(tx_id,)).fetchone()['locked']
        if not lock:return {'id':tx_id,'status':'PENDING'}
        try:
            t=c.execute('SELECT * FROM transfers WHERE id=%s',(tx_id,)).fetchone()
            if t['status'] in ('COMMITTED','ABORTED'):return {'id':tx_id,'status':t['status'],'error':t['last_error']}
            try:
                legacy_check(t)
                call(t['source_region'],'/internal/local-transfer',{
                    'tx_id':tx_id,'source_id':t['source_id'],'dest_id':t['destination_id'],
                    'debit_minor':t['amount_minor'],'credit_minor':t['credit_minor'],
                    'fee_minor':t['fee_minor'],'detail':{'rate':t['rate_text']}})
                set_status(c,tx_id,'COMMITTED')
                return {'id':tx_id,'status':'COMMITTED'}
            except HTTPException as e:
                if e.status_code in (400,404,409):
                    set_status(c,tx_id,'ABORTED',str(e.detail))
                    return {'id':tx_id,'status':'ABORTED','error':str(e.detail)}
                set_status(c,tx_id,'PENDING',str(e))
                return {'id':tx_id,'status':'PENDING','error':str(e)}
            except Exception as e:
                set_status(c,tx_id,'PENDING',str(e))
                return {'id':tx_id,'status':'PENDING','error':str(e)}
        finally:c.execute('SELECT pg_advisory_unlock(hashtext(%s))',(tx_id,))

def reconcile_loop(stop:threading.Event):
    """Retoma commits após falhas; PREPARING antigo só aborta após janela de segurança."""
    while not stop.wait(6):
        try:
            with connect() as c:
                rows=c.execute("""SELECT id,source_region,dest_region,status FROM transfers
                    WHERE status IN ('DECISION_COMMIT','DECISION_ABORT')
                    OR (status='PREPARING' AND updated_at < now()- interval '45 seconds')
                    OR (status IN ('PENDING','NEW') AND updated_at < now()- interval '8 seconds')
                    LIMIT 60""").fetchall()
            for t in rows:
                try:
                    if t['source_region']==t['dest_region']:process_local(t['id'])
                    else:process(t['id'])
                except Exception as e:LOG.error('Recuperação %s: %s',t['id'],e)
        except Exception as e:LOG.error('Worker recuperação: %s',e)
