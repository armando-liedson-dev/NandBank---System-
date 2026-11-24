"""Benchmark sequencial real de consulta de saldo por HTTPS, 10.000 pedidos após warmup.
Não é benchmark CORBA; apenas medições obtidas no novo GlobalScale.
"""
import os,time,statistics,sys,json
import httpx

def run():
    with httpx.Client(verify='/certs/ca.crt',timeout=15.0) as c:
        base='https://gateway:8443'
        login=c.post(base+'/api/auth/login',json={'email':'admin@globalscale.local','password':os.environ['ADMIN_PASSWORD']})
        login.raise_for_status();token=login.json()['access_token']
        headers={'Authorization':'Bearer '+token}
        accounts=c.get(base+'/api/admin/accounts',headers=headers);accounts.raise_for_status()
        if not accounts.json():
            print('SEM CONTAS: crie um cliente primeiro ou execute app.smoke.');return 1
        id_=accounts.json()[0]['id']
        url=base+'/api/accounts/'+id_
        for _ in range(100):c.get(url,headers=headers).raise_for_status()
        samples=[];failed=0;n=int(os.getenv('BENCHMARK_N','10000'))
        for i in range(n):
            t=time.perf_counter_ns()
            try:c.get(url,headers=headers).raise_for_status()
            except Exception:failed+=1
            samples.append((time.perf_counter_ns()-t)/1000000)
        tot=sum(samples)/1000
        print(json.dumps({'operacao':'GET /api/accounts/{id}','pedidos':n,'falhas':failed,
          'tempo_total_s':round(tot,3),'media_ms':round(statistics.mean(samples),3),
          'p95_ms':round(sorted(samples)[int(n*.95)],3),
          'throughput_ops_s':round(n/tot,2) if tot else 0},ensure_ascii=False,indent=2))
        return 0 if failed==0 else 1

if __name__=='__main__':sys.exit(run())
