"""Testes adicionais de cartões e permissões. Exige serviços Docker activos."""
import os,uuid,sys,json
import httpx
from .smoke import api,login,register,BASE,CONTEXT

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
    node_actions=api('GET','/api/admin/node-actions',manager)
    assert isinstance(node_actions['agent_online'],bool)
    with httpx.Client(**CONTEXT) as h:
        no_control=h.post(BASE+'/api/admin/nodes/af/action',headers={'Authorization':'Bearer '+token},json={'action':'STOP_PRIMARY','reason':'MAINTENANCE'})
        assert no_control.status_code==403,('cliente não pode desligar nós',no_control.status_code)
        # Teste sem executar qualquer STOP real no servidor.
        favicon=h.get(BASE+'/lion-mark.png')
        assert favicon.status_code==200 and favicon.headers['content-type'].startswith('image/'),('logo HTTP',favicon.status_code,favicon.headers.get('content-type'))
        css=h.get(BASE+'/theme.css')
        assert css.status_code==200 and 'NandBank' in css.text,('tema HTTP',css.status_code)
        homepage=h.get(BASE+'/')
        assert homepage.status_code==200 and 'NandBank' in homepage.text
    result={'result':'PASSOU','card_request':True,'regional_authorization':True,'card_approval':True,'card_freeze_unfreeze':True,'client_cannot_operate_nodes':True,'frontend_assets':True,'node_agent_available':node_actions['agent_online']}
    print(json.dumps(result,indent=2,ensure_ascii=False),flush=True)
    return 0

if __name__=='__main__':
    try:sys.exit(run())
    except Exception as e:print('TESTE NANDBANK FALHOU:',repr(e),flush=True);sys.exit(1)
