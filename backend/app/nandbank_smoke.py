"""Testes adicionais de cartões e permissões. Exige serviços Docker activos."""
import os,uuid,sys,json
import httpx
from .smoke import api,login,register,BASE,CONTEXT,P

def run():
    print('=== NANDBANK / CARTÕES, PERFIS E ASSETS ===',flush=True)
    aid,token=register('MZ-MPM','af','MZN')
    request=api('POST','/api/cards/request',token,{'account_id':aid})
    cid=request['id']
    assert request['status']=='REQUESTED'
    client_list=api('GET','/api/cards',token)
    assert any(x['id']==cid and x['status']=='REQUESTED' for x in client_list)
    manager=login('regional.af@nandbank.local',os.environ['MANAGER_AF_PASSWORD'])
    europe=login('regional.eu@nandbank.local',os.environ['REGIONAL_PASSWORD'])
    cards=api('GET','/api/admin/cards',manager)
    assert any(x['id']==cid for x in cards)
    with httpx.Client(**CONTEXT) as h:
        wrong=h.post(BASE+'/api/admin/cards/'+cid+'/review',headers={'Authorization':'Bearer '+europe},json={'approved':True})
        assert wrong.status_code==403,('âmbito regional',wrong.status_code,wrong.text[:200])
        unauth=h.post(BASE+'/api/admin/cards/'+cid+'/review',headers={'Authorization':'Bearer '+token},json={'approved':True})
        assert unauth.status_code==403,('permissão cliente',unauth.status_code)
    approved=api('POST','/api/admin/cards/'+cid+'/review',manager,{'approved':True})
    assert approved['status']=='ACTIVE'
    after=api('GET','/api/cards',token)
    assert any(x['id']==cid and x['status']=='ACTIVE' for x in after)
    frozen=api('POST','/api/cards/'+cid+'/freeze',token,{})
    assert frozen['status']=='FROZEN'
    active=api('POST','/api/cards/'+cid+'/unfreeze',token,{})
    assert active['status']=='ACTIVE'
    # CRUD lógico: cliente recém-criado, intervenção regional autorizada e recuperação.
    person=api('GET','/api/me',token)['user']
    directory=api('GET','/api/admin/customers',manager)
    assert any(u['id']==person['id'] for u in directory), 'Cliente não consta da base regional'
    activity=api('GET','/api/admin/customers/'+person['id']+'/activity',manager)
    assert any(a['id']==aid for a in activity['accounts'])
    with httpx.Client(**CONTEXT) as h:
        denied=h.patch(BASE+'/api/admin/customers/'+person['id']+'/status',headers={'Authorization':'Bearer '+europe},json={'status':'EXPIRED','reason':'Teste restricao regional'})
        assert denied.status_code==403,('regional de fora',denied.status_code)
    state=api('PATCH','/api/admin/customers/'+person['id']+'/status',manager,{'status':'EXPIRED','reason':'Teste académico de expiração'})
    assert state['status']=='EXPIRED'
    with httpx.Client(**CONTEXT) as h:
        old=h.get(BASE+'/api/me',headers={'Authorization':'Bearer '+token})
        assert old.status_code==403,('JWT deve bloquear conta expirada',old.status_code)
        login_denied=h.post(BASE+'/api/auth/login',json={'email':person['email'],'password':P})
        assert login_denied.status_code==403 and 'expirada' in login_denied.text.lower()
    restored=api('PATCH','/api/admin/customers/'+person['id']+'/status',manager,{'status':'ACTIVE','reason':'Reposição após teste académico'})
    assert restored['status']=='ACTIVE'
    assert login(person['email'],P)
    node_actions=api('GET','/api/admin/node-actions',manager)
    assert isinstance(node_actions['agent_online'],bool)
    with httpx.Client(**CONTEXT) as h:
        no_control=h.post(BASE+'/api/admin/nodes/af/action',headers={'Authorization':'Bearer '+token},json={'action':'STOP_PRIMARY','reason':'MAINTENANCE'})
        assert no_control.status_code==403,('cliente não pode desligar nós',no_control.status_code)
        # Teste sem executar qualquer STOP real no servidor.
        # Interface premium React: não requer ficheiros legados /lion-mark.png ou /theme.css.
        favicon=h.get(BASE+'/static/images/nandbank-lion-logo.png')
        assert favicon.status_code==200 and favicon.headers['content-type'].startswith('image/'),('logo HTTP',favicon.status_code,favicon.headers.get('content-type'))
        homepage=h.get(BASE+'/')
        assert homepage.status_code==200 and 'NandBank' in homepage.text
        import re
        bundles=re.findall(r'/static/assets/[^\"\']+\.(?:css|js)',homepage.text)
        assert bundles,('bundles React não encontrados',homepage.text[:350])
        for bundle in bundles:
            asset=h.get(BASE+bundle)
            assert asset.status_code==200 and ('javascript' in asset.headers.get('content-type','') or 'css' in asset.headers.get('content-type','')),('asset React',bundle,asset.status_code,asset.headers.get('content-type'))
    result={'result':'PASSOU','card_request':True,'regional_authorization':True,'card_approval':True,'card_freeze_unfreeze':True,'client_cannot_operate_nodes':True,'frontend_assets':True,'customer_management':True,'customer_expiration':True,'regional_customer_scope':True,'node_agent_available':node_actions['agent_online']}
    print(json.dumps(result,indent=2,ensure_ascii=False),flush=True)
    return 0

if __name__=='__main__':
    try:sys.exit(run())
    except Exception as e:print('TESTE NANDBANK FALHOU:',repr(e),flush=True);sys.exit(1)
