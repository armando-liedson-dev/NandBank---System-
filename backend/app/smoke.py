"""Teste integrado da banca real do protótipo. Apenas dados fictícios. Idempotência e 2PC."""
import os,sys,uuid,time,json,ssl
import httpx
BASE='https://gateway:8443'
CONTEXT={'verify':'/certs/ca.crt','timeout':35.0}
P='DemoPassword1234!'

def api(method,path,token=None,body=None,expect_ok=True):
    headers={'Authorization':'Bearer '+token} if token else {}
    with httpx.Client(**CONTEXT) as c:
        r=c.request(method,BASE+path,headers=headers,json=body)
    try:data=r.json()
    except Exception:data={'body':r.text[:300]}
    if expect_ok and r.status_code>=400:raise AssertionError(f'{method} {path}: {r.status_code}: {data}')
    return data

def login(email,password):return api('POST','/api/auth/login',body={'email':email,'password':password})['access_token']

def register(branch,region,currency):
    email=f'smoke.{region}.{uuid.uuid4().hex[:11]}@example.invalid'
    account=api('POST','/api/auth/register',body={'name':'Cliente Teste '+region.upper(),'email':email,'password':P,'branch':branch,'currency':currency})
    return account['account_id'],login(email,P)

def balance(token,id):return api('GET','/api/accounts/'+id,token)['balance_minor']

def run():
    print('=== GLOBALSCALE / TESTE INTEGRADO ===',flush=True)
    api('GET','/api/health')
    config=api('GET','/api/config');assert len(config['regions'])==6
    src,stoken=register('ES-MAD','eu','EUR')
    dst,dtoken=register('CN-SHA','as','CNY')
    teller=login('regional.eu@globalscale.local',os.environ['REGIONAL_PASSWORD'])
    deposit_id=str(uuid.uuid4())
    dep=api('POST','/api/teller/deposit',teller,{'account_id':src,'amount':'700.00','currency':'EUR','idempotency_key':deposit_id})
    assert dep['ok']
    # repetir com a mesma chave não duplica o depósito
    api('POST','/api/teller/deposit',teller,{'account_id':src,'amount':'700.00','currency':'EUR','idempotency_key':deposit_id})
    assert balance(stoken,src)==70000
    assert balance(dtoken,dst)==0
    quote=api('GET','/api/fx/quote?source=EUR&destination=CNY&amount=120.00')
    key=str(uuid.uuid4())
    req={'source_id':src,'destination_id':dst,'amount':'120.00','note':'Teste internacional 2PC','idempotency_key':key}
    tx=api('POST','/api/transfers',stoken,req)
    if tx['status']!='COMMITTED':raise AssertionError(f'2PC não confirmou: {tx}')
    s=balance(stoken,src);d=balance(dtoken,dst)
    assert s==70000-quote['total_debit_minor'],(s,quote)
    assert d==quote['credit_minor'],(d,quote)
    # idempotência após commit (não duplica débito)
    tx2=api('POST','/api/transfers',stoken,req)
    assert tx2['id']==tx['id'] and balance(stoken,src)==s and balance(dtoken,dst)==d
    assert tx2['status']=='COMMITTED'
    # saldo insuficiente: 2PC ABORT sem débito
    refused=api('POST','/api/transfers',stoken,{**req,'idempotency_key':str(uuid.uuid4()),'amount':'900000.00'})
    assert refused['status']=='ABORTED',refused
    assert balance(stoken,src)==s and balance(dtoken,dst)==d
    # transferências locais ACID - criar segunda conta no continente da origem
    dst_local,local_token=register('PT-LIS','eu','EUR')
    local=api('POST','/api/transfers',stoken,{'source_id':src,'destination_id':dst_local,'amount':'10.00','idempotency_key':str(uuid.uuid4()),'note':'Teste local'})
    assert local['status']=='COMMITTED',local
    assert balance(local_token,dst_local)==1000
    # PDF deve estar disponível após commit
    with httpx.Client(**CONTEXT) as c:
        pdf=c.get(BASE+'/api/transactions/'+tx['id']+'/receipt.pdf',headers={'Authorization':'Bearer '+stoken})
    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF'),(pdf.status_code,pdf.text[:50] if pdf.status_code!=200 else '')
    nodes=api('GET','/api/admin/nodes',teller)
    assert nodes and nodes[0]['region']=='eu'
    print(json.dumps({'result':'PASSOU','nodes':6,'transfer_2pc':tx['id'],'credited_CNY_minor':d,'debit_EUR_minor':70000-s,'idempotence':True,'insufficient_balance':True,'local_ACID':True,'pdf':True,'regional_scope':True},indent=2,ensure_ascii=False),flush=True)
    return 0

if __name__=='__main__':
    try:sys.exit(run())
    except Exception as e:print('TESTE FALHOU:',repr(e),flush=True);sys.exit(1)
