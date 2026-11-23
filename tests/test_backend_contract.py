"""Contract tests without PostgreSQL: FastAPI routing, claims and validation.
All DB/coordinator interfaces are stubbed; do NOT present as integrated banking test.
"""
import sys,types,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))
mockdb=types.ModuleType('app.db')
mockdb.connect=lambda: (_ for _ in ()).throw(RuntimeError('DB mock: no operation permitted'))
sys.modules['app.db']=mockdb
mockco=types.ModuleType('app.coordinator')
mockco.call=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('coordinator mock'))
mockco.process=mockco.process_local=mockco.reconcile_loop=mockco.probe_instance=mockco.call
sys.modules['app.coordinator']=mockco
from app import gateway as g
from fastapi.testclient import TestClient
from fastapi import HTTPException
client=TestClient(g.app)
class Contracts(unittest.TestCase):
    def tearDown(self):g.app.dependency_overrides.clear()
    def test_health_brand(self):
        response=client.get('/api/health')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['app'],'NandBank')
    def test_config_regions(self):
        j=client.get('/api/config').json()
        self.assertEqual(j['name'],'NandBank')
        self.assertEqual(len(j['regions']),6)
    def test_currency_cents(self):
        self.assertEqual(g.cents('3000.00'),300000)
        for invalid in ['0','-1','nan','10.005','100000000000']:
            with self.subTest(value=invalid):
                with self.assertRaises(HTTPException):g.cents(invalid)
    def test_client_cannot_operate_nodes(self):
        g.app.dependency_overrides[g.bearer]=lambda:{'sub':'c','role':'client','region':'af','branch':'MZ-MPM'}
        r=client.post('/api/admin/nodes/af/action',json={'action':'STOP_PRIMARY','reason':'MAINTENANCE'})
        self.assertEqual(r.status_code,403)
    def test_region_scoped_failover_status(self):
        g.app.dependency_overrides[g.bearer]=lambda:{'sub':'r','role':'regional_manager','region':'eu','branch':None}
        j=client.get('/api/failover/status').json()
        self.assertEqual([x['region'] for x in j],['eu'])
    def test_client_sees_all_regional_statuses(self):
        g.app.dependency_overrides[g.bearer]=lambda:{'sub':'c','role':'client','region':'af','branch':'MZ-MPM'}
        j=client.get('/api/failover/status').json()
        self.assertEqual(len(j),6)
    def test_card_requested_model_and_endpoint(self):
        g.app.dependency_overrides[g.bearer]=lambda:{'sub':'c','role':'client','region':'af','branch':'MZ-MPM'}
        # Acesso de cliente ao painel de revisão tem de falhar antes da BD.
        r=client.get('/api/admin/cards')
        self.assertEqual(r.status_code,403)
    def test_manager_cannot_send_money_from_client_account(self):
        g.app.dependency_overrides[g.bearer]=lambda:{'sub':'m','role':'regional_manager','region':'af','branch':None}
        r=client.post('/api/transfers',json={'source_id':'a','destination_id':'b','amount':'1.00','idempotency_key':'validkey123'})
        self.assertEqual(r.status_code,403)
    def test_client_cannot_open_customer_directory(self):
        g.app.dependency_overrides[g.bearer]=lambda:{'sub':'c','role':'client','region':'af','branch':'MZ-MPM'}
        self.assertEqual(client.get('/api/admin/customers').status_code,403)
    def test_teller_cannot_manage_customers(self):
        g.app.dependency_overrides[g.bearer]=lambda:{'sub':'t','role':'teller','region':'af','branch':'MZ-MPM'}
        self.assertEqual(client.patch('/api/admin/customers/test/status',json={'status':'EXPIRED','reason':'Motivo de teste'}).status_code,403)
    def test_customer_status_validation(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):g.CustomerStatusChange(status='EXPIRED',reason='a')
    def test_customer_edit_validation(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):g.CustomerUpdate(name='a',email='ab@example.invalid')
    def test_agent_needs_secret(self):
        r=client.get('/api/agent/jobs')
        self.assertEqual(r.status_code,403)
if __name__=='__main__':unittest.main()
