from pathlib import Path
import json,subprocess,os,importlib.util
s=Path.home()/'scratch/blackbox/2026-11-13-close-check-r2';os.environ['POLICY_SOURCE']=str(Path.home()/'projects/simplecode/policy')
spec=importlib.util.spec_from_file_location('fixture_report',s/'test_close_check_report_measurement.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
repo=s/'runner-report';base,_=m.fixture(repo)
row=next(x for x in json.loads(Path('simple.json').read_text())['checks'] if x['id']=='close-check');assert row['policy']['args']==[];row['base']=base
(repo/'simple.json').write_text(json.dumps({'version':1,'checks':[row]}));m.git(repo,'add','--','simple.json');m.git(repo,'commit','-qm','contrato report-only')
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(s)}
r=subprocess.run(['simplecode','verify','--hook','pre-push','--no-observe','--fresh'],cwd=repo,env=env,capture_output=True,text=True);(s/'runner-report.json').write_text(r.stdout+r.stderr);j=json.loads(r.stdout);print('reporte_runner_rc='+str(r.returncode),j['counts']);print(j['rows'][0]['stdout'].strip());assert r.returncode==0 and j['counts']['could_not_run']==0 and 'no_ejecuta=1' in j['rows'][0]['stdout']
row['policy']['args']=['--base','missing-ref'];(repo/'simple.json').write_text(json.dumps({'version':1,'checks':[row]}));m.git(repo,'add','--','simple.json');m.git(repo,'commit','-qm','control rango inexistente')
r=subprocess.run(['simplecode','verify','--hook','pre-push','--no-observe','--fresh'],cwd=repo,env=env,capture_output=True,text=True);(s/'runner-cnr.json').write_text(r.stdout+r.stderr);j=json.loads(r.stdout);print('cnr_runner_rc='+str(r.returncode),j['counts']);assert r.returncode==2 and j['counts']['could_not_run']==1 and j['counts']['pass']==0
