from pathlib import Path
import importlib.util,sys,os,subprocess,json,shutil,runpy
s=Path.home()/'scratch/blackbox/2026-11-13-close-check-r2';policy=Path.home()/'projects/simplecode/policy';sys.path.insert(0,str(policy))
from simple_policy.close_check_lint import classify
repo=s/'casos';repo.mkdir(exist_ok=True);(repo/'product.py').write_text("from pathlib import Path\ndef run():\n    Path('ran').write_text('producto')\nif __name__ == '__main__':\n    run()\n")
rows=[]
def measure(name,command,*,oracle,run=None,control=None,omission=None):
 verdict,why=classify(command);row={'case':name,'command':command,'classification':verdict,'reason':why,'oracle':oracle,'could_not_run':0}
 if run:
  r=subprocess.run(run,cwd=repo,capture_output=True,text=True);row['actual_rc']=r.returncode;row['actual_argv']=run;row['stdout']=r.stdout;row['stderr']=r.stderr
  n=subprocess.run(control,cwd=repo,capture_output=True,text=True);row['negative_rc']=n.returncode;row['negative_argv']=control;row['negative_stdout']=n.stdout;row['negative_stderr']=n.stderr
  assert r.returncode==0 and n.returncode!=0
 else:row.update(could_not_run=1,omission=omission)
 if oracle=='product_runs' and verdict=='no_ejecuta':row['adjudication']='false_alarm_for_future_blocking'
 elif oracle=='metadata_only' and verdict=='no_ejecuta':row['adjudication']='correct_no_product'
 elif oracle=='metadata_only' and verdict=='ejecuta':row['adjudication']='missed_no_product'
 elif oracle=='product_runs':row['adjudication']='correct_product'
 else:row['adjudication']='unadjudicated'
 rows.append(row)
(repo/'good.sh').write_text('#!/bin/sh\nprintf "%s\\n" "$1"\n');(repo/'bad.sh').write_text('#!/bin/sh\nprintf "%s\\n" $1\n')
if shutil.which('shellcheck'):
 measure('shellcheck','shellcheck bin/bb',oracle='product_runs',run=['shellcheck','good.sh'],control=['shellcheck','bad.sh'])
else:measure('shellcheck','shellcheck bin/bb',oracle='unknown',omission='shellcheck unavailable')
cmd="python3 - <<'PY'\nfrom product import run\nrun()\nPY"
measure('python_stdin',cmd,oracle='product_runs',run=['sh','-c',cmd],control=['sh','-c',"python3 - <<'PY'\nfrom product import missing\nmissing()\nPY"])
assert (repo/'ran').read_text()=='producto';(repo/'ran').unlink()
(repo/'receipt').write_text('ok')
measure('receipt_only','test -f receipt',oracle='metadata_only',run=['test','-f','receipt'],control=['test','-f','missing'])
measure('echo_runner_name','echo pytest',oracle='metadata_only',run=['sh','-c','echo pytest'],control=['sh','-c','exit 1'])
measure('python_script','python3 product.py',oracle='product_runs',run=[sys.executable,'product.py'],control=[sys.executable,'missing.py'])
measure('systemctl_query','systemctl is-active sample.service',oracle='unknown',omission='service query forbidden by scope; classification alone does not establish execution')
summary={'controlled_cases':len(rows),'false_alarms':sum(r['adjudication']=='false_alarm_for_future_blocking' for r in rows),'missed_no_product':sum(r['adjudication']=='missed_no_product' for r in rows),'unadjudicated':sum(r['adjudication']=='unadjudicated' for r in rows),'could_not_run':sum(r['could_not_run'] for r in rows),'scope':'controlled sample, not a fleet rate; no blocking threshold voted'}
document={'summary':summary,'cases':rows}
raw=s/'measurement-r2.raw.NO-PUBLICAR.json';raw.write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n');raw.chmod(0o600)
m=runpy.run_path(str(Path('tests/test_sin_datos_privados.py').resolve()))
document['sanitization']='runtime diagnostic paths masked with the signed repository pattern; original local bytes retained in private scratch'
for row in rows:
    for key in ['stdout','stderr','negative_stdout','negative_stderr']:
        if key in row:row[key]=m['PATRON'].sub('<dato-local>',row[key])
Path('tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/measurement-r2.json').write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary));print([(r['case'],r['classification'],r['adjudication'],r.get('actual_rc'),r.get('negative_rc')) for r in rows])
