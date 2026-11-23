"""Participante regional de 2PC. Cada continente tem duas réplicas de aplicação, UMA BD própria."""
from __future__ import annotations
import os,uuid,ssl,logging,json
from contextlib import contextmanager
from typing import Literal
from fastapi import FastAPI,Depends,HTTPException
from pydantic import BaseModel,Field
from psycopg import sql
from psycopg.errors import UniqueViolation
from .db import connect
from .security import bearer

logging.basicConfig(level=logging.INFO)
REGION=os.environ['REGION']
INSTANCE=os.getenv('INSTANCE','primary')
DB_HOST=os.environ['DB_HOST']
app=FastAPI(title=f'GlobalScale Participante {REGION}',docs_url=None,redoc_url=None)

def system(c=Depends(bearer)):
    if c['role']!='system':raise HTTPException(403,'Serviço interno apenas')
    return c

def db():return connect(DB_HOST)

def gid(tx_id,side):
    try:uuid.UUID(tx_id)
    except (ValueError,TypeError):raise HTTPException(400,'ID de transacção inválido')
    if side not in ('source','dest'):raise HTTPException(400,'Lado inválido')
    return 'gs_'+tx_id.replace('-','')+'_'+side

def gstate(conn,tx_id,side):
    name=gid(tx_id,side)
    if conn.execute('SELECT 1 FROM pg_prepared_xacts WHERE gid=%s',(name,)).fetchone():return 'PREPARED'
    if conn.execute('SELECT 1 FROM ledger WHERE operation_id=%s AND kind=%s',(tx_id, 'TRANSFER_'+side.upper())).fetchone():return 'COMMITTED'
    return 'ABSENT'

class NewAccount(BaseModel):
    id:str; owner_id:str; branch:str;currency:str

class LocalOperation(BaseModel):
    operation_id:str;account_id:str;kind:Literal['DEPOSIT','WITHDRAW'];amount_minor:int=Field(gt=0)
    detail:dict={}

class LocalTransfer(BaseModel):
    tx_id:str;source_id:str;dest_id:str;debit_minor:int=Field(gt=0);credit_minor:int=Field(gt=0)
    fee_minor:int=Field(ge=0);detail:dict={}

class Prepare(BaseModel):
    tx_id:str;side:Literal['source','dest'];account_id:str;amount_minor:int=Field(gt=0);currency:str
    details:dict={}

class Resolve(BaseModel):
    tx_id:str;side:Literal['source','dest'];decision:Literal['commit','abort']

class NormalizeCurrency(BaseModel):
    account_id:str
    currency:str
    balance_minor:int=Field(ge=0)
    operation_id:str
    details:dict={}

@app.get('/health')
def health():
    try:
        with db() as c:c.execute('SELECT 1')
        return {'ok':True,'region':REGION,'instance':INSTANCE,'database':DB_HOST}
    except Exception:raise HTTPException(503,'Base de dados indisponível')

@app.post('/internal/accounts')
def create_account(a:NewAccount,_=Depends(system)):
    with db() as c:
        c.execute('INSERT INTO accounts(id,owner_id,branch,currency) VALUES (%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING',(a.id,a.owner_id,a.branch,a.currency))
    return {'ok':True,'id':a.id,'region':REGION}

@app.get('/internal/accounts/{account_id}')
def account(account_id:str,_=Depends(system)):
    with db() as c:
        row=c.execute('SELECT id,owner_id,branch,currency,balance_minor FROM accounts WHERE id=%s',(account_id,)).fetchone()
    if not row:raise HTTPException(404,'Conta regional inexistente')
    return row

@app.post('/internal/normalize-currency')
def normalize_currency(v:NormalizeCurrency,_=Depends(system)):
    with db() as c:
        c.execute('BEGIN')
        try:
            account=c.execute('SELECT currency,balance_minor FROM accounts WHERE id=%s FOR UPDATE',(v.account_id,)).fetchone()
            if not account:raise HTTPException(404,'Conta inexistente')
            existing=c.execute('SELECT 1 FROM ledger WHERE operation_id=%s AND account_id=%s',(v.operation_id,v.account_id)).fetchone()
            if existing:
                c.execute('COMMIT')
                current=c.execute('SELECT currency,balance_minor FROM accounts WHERE id=%s',(v.account_id,)).fetchone()
                return {'ok':True,'idempotent':True,'currency':current['currency'],'balance_minor':current['balance_minor']}
            if account['currency']==v.currency:
                c.execute('COMMIT')
                return {'ok':True,'idempotent':True,'currency':account['currency'],'balance_minor':account['balance_minor']}
            details={**v.details,'previous_currency':account['currency'],
                     'previous_balance_minor':account['balance_minor'],
                     'new_currency':v.currency,'new_balance_minor':v.balance_minor}
            c.execute('UPDATE accounts SET currency=%s,balance_minor=%s WHERE id=%s',
                      (v.currency,v.balance_minor,v.account_id))
            c.execute('INSERT INTO ledger(operation_id,account_id,kind,delta_minor,currency,details) VALUES (%s,%s,%s,%s,%s,%s)',
                      (v.operation_id,v.account_id,'CURRENCY_CONVERSION',v.balance_minor,v.currency,json.dumps(details)))
            c.execute('COMMIT')
            return {'ok':True,'idempotent':False,'currency':v.currency,'balance_minor':v.balance_minor}
        except Exception:
            c.execute('ROLLBACK')
            raise

@app.get('/internal/ledger/{account_id}')
def ledger(account_id:str,_=Depends(system)):
    with db() as c:
        return c.execute('SELECT operation_id,kind,delta_minor,currency,created_at FROM ledger WHERE account_id=%s ORDER BY id DESC LIMIT 80',(account_id,)).fetchall()

@app.get('/internal/stats')
def stats(_=Depends(system)):
    with db() as c:
        return {
            'region':REGION,'instance':INSTANCE,
            'accounts':c.execute('SELECT count(*) AS n FROM accounts').fetchone()['n'],
            'operations':c.execute('SELECT count(*) AS n FROM ledger').fetchone()['n'],
            'prepared':c.execute("SELECT count(*) AS n FROM pg_prepared_xacts WHERE gid LIKE 'gs_%'").fetchone()['n']}

@app.post('/internal/local-operation')
def local_op(v:LocalOperation,_=Depends(system)):
    with db() as c:
        c.execute('BEGIN')
        try:
            acc=c.execute('SELECT balance_minor,currency FROM accounts WHERE id=%s FOR UPDATE',(v.account_id,)).fetchone()
            if not acc:raise HTTPException(404,'Conta inexistente')
            existing=c.execute('SELECT delta_minor FROM ledger WHERE operation_id=%s AND account_id=%s',(v.operation_id,v.account_id)).fetchone()
            if existing:
                c.execute('COMMIT')
                return {'ok':True,'idempotent':True,'balance_minor':acc['balance_minor']}
            delta=v.amount_minor if v.kind=='DEPOSIT' else -v.amount_minor
            if acc['balance_minor']+delta<0:raise HTTPException(409,'SALDO_INSUFICIENTE')
            c.execute('UPDATE accounts SET balance_minor=balance_minor+%s WHERE id=%s',(delta,v.account_id))
            c.execute('INSERT INTO ledger(operation_id,account_id,kind,delta_minor,currency,details) VALUES (%s,%s,%s,%s,%s,%s)',(v.operation_id,v.account_id,v.kind,delta,acc['currency'],__import__('json').dumps(v.detail)))
            c.execute('COMMIT')
            return {'ok':True,'idempotent':False,'balance_minor':acc['balance_minor']+delta}
        except Exception:
            c.execute('ROLLBACK')
            raise

@app.post('/internal/local-transfer')
def local_transfer(v:LocalTransfer,_=Depends(system)):
    if v.source_id==v.dest_id:raise HTTPException(400,'Contas idênticas')
    with db() as c:
        c.execute('BEGIN')
        try:
            accounts=c.execute('SELECT id,balance_minor,currency FROM accounts WHERE id IN (%s,%s) ORDER BY id FOR UPDATE',(v.source_id,v.dest_id)).fetchall()
            by_id={r['id']:r for r in accounts}
            if len(by_id)!=2:raise HTTPException(404,'Conta inexistente')
            existing=c.execute('SELECT 1 FROM ledger WHERE operation_id=%s',(v.tx_id,)).fetchone()
            if existing:
                c.execute('COMMIT')
                return {'ok':True,'idempotent':True}
            debit=v.debit_minor+v.fee_minor
            if by_id[v.source_id]['balance_minor']<debit:raise HTTPException(409,'SALDO_INSUFICIENTE')
            c.execute('UPDATE accounts SET balance_minor=balance_minor-%s WHERE id=%s',(debit,v.source_id))
            c.execute('UPDATE accounts SET balance_minor=balance_minor+%s WHERE id=%s',(v.credit_minor,v.dest_id))
            for id_,delta,kind in ((v.source_id,-debit,'TRANSFER_SOURCE'),(v.dest_id,v.credit_minor,'TRANSFER_DEST')):
                c.execute('INSERT INTO ledger(operation_id,account_id,kind,delta_minor,currency,details) VALUES (%s,%s,%s,%s,%s,%s)',(v.tx_id,id_,kind,delta,by_id[id_]['currency'],__import__('json').dumps(v.detail)))
            c.execute('COMMIT')
            return {'ok':True,'idempotent':False}
        except Exception:
            c.execute('ROLLBACK')
            raise

@app.post('/internal/prepare')
def prepare(v:Prepare,_=Depends(system)):
    name=gid(v.tx_id,v.side)
    with db() as c:
        state=gstate(c,v.tx_id,v.side)
        if state!='ABSENT':return {'ok':True,'state':state,'region':REGION,'instance':INSTANCE}
        c.execute('BEGIN')
        try:
            a=c.execute('SELECT balance_minor,currency FROM accounts WHERE id=%s FOR UPDATE',(v.account_id,)).fetchone()
            if not a:raise HTTPException(404,'Conta inexistente')
            if a['currency']!=v.currency:raise HTTPException(409,'MOEDA_DIFERENTE')
            delta=-v.amount_minor if v.side=='source' else v.amount_minor
            if a['balance_minor']+delta<0:raise HTTPException(409,'SALDO_INSUFICIENTE')
            c.execute('UPDATE accounts SET balance_minor=balance_minor+%s WHERE id=%s',(delta,v.account_id))
            c.execute('INSERT INTO ledger(operation_id,account_id,kind,delta_minor,currency,details) VALUES (%s,%s,%s,%s,%s,%s)',(v.tx_id,v.account_id,'TRANSFER_'+v.side.upper(),delta,v.currency,__import__('json').dumps(v.details)))
            c.execute(sql.SQL('PREPARE TRANSACTION {}').format(sql.Literal(name)))
            return {'ok':True,'state':'PREPARED','region':REGION,'instance':INSTANCE}
        except Exception:
            c.execute('ROLLBACK')
            raise

@app.post('/internal/resolve')
def resolve(v:Resolve,_=Depends(system)):
    name=gid(v.tx_id,v.side)
    with db() as c:
        state=gstate(c,v.tx_id,v.side)
        if state=='PREPARED':
            command='COMMIT PREPARED' if v.decision=='commit' else 'ROLLBACK PREPARED'
            c.execute(sql.SQL('{} {}').format(sql.SQL(command),sql.Literal(name)))
            return {'ok':True,'status':'COMMITTED' if v.decision=='commit' else 'ABORTED','instance':INSTANCE}
        if v.decision=='commit' and state=='ABSENT':
            # Unknown transaction is NOT success: coordinator must retain pending state.
            raise HTTPException(409,'Transacção preparada não encontrada')
        if v.decision=='abort' and state=='COMMITTED':
            raise HTTPException(409,'Transacção já confirmada; não pode abortar')
        return {'ok':True,'status':'COMMITTED' if state=='COMMITTED' else 'ABORTED','idempotent':True}

@app.get('/internal/prepared/{tx_id}/{side}')
def tx_state(tx_id:str,side:str,_=Depends(system)):
    with db() as c:return {'state':gstate(c,tx_id,side)}

def run():
    import uvicorn
    uvicorn.run(app,host='0.0.0.0',port=9443,ssl_certfile=f'/certs/region-{REGION}.crt',ssl_keyfile=f'/certs/region-{REGION}.key',ssl_ca_certs='/certs/ca.crt',ssl_cert_reqs=ssl.CERT_REQUIRED,workers=1)

if __name__=='__main__':run()
