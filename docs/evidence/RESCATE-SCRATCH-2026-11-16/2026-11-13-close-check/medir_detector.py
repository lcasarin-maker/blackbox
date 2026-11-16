from pathlib import Path
import subprocess,sys,os,json
s=Path.home()/'scratch/blackbox/2026-11-13-close-check';root=s/'fixture-medidor';(root/'tasks/done').mkdir(parents=True,exist_ok=True)
def card(cmd):return '---\nid: X\nstatus: done\nclose_check: '+json.dumps({'cmd':cmd})+'\n---\n'
f=root/'tasks/done/X.md';f.write_text(card('test -f receipt.json'))
rows=[]
def run(label,policy,*args,path=None):
 env={**os.environ,'PYTHONPATH':str(policy),'PYTHONDONTWRITEBYTECODE':'1'}
 if path is not None:env['PATH']=path
 r=subprocess.run([sys.executable,'-m','simple_policy','close-check','--root',str(root),*args],env=env,text=True,capture_output=True)
 rows.append({'case':label,'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr});print(label,'rc='+str(r.returncode),repr(r.stdout.strip()),repr(r.stderr.strip()))
run('antes_no_ejecutor',Path.home()/'projects/simplecode/policy','--all')
run('despues_no_ejecutor',s/'simplecode-propuesta/policy','--all','--enforce')
run('sin_git',s/'simplecode-propuesta/policy','--base','HEAD^','--head','HEAD','--enforce',path=str(s/'sin_binarios'))
run('detector_retirado',s/'simplecode-sin-detector/policy','--all','--enforce')
(root/'product.py').write_text("from pathlib import Path\nPath('ran').write_text('producto ejecutado')\n")
subprocess.run([sys.executable,'product.py'],cwd=root,check=True)
assert (root/'ran').read_text()=='producto ejecutado'
f.write_text(card('python3 product.py'))
run('producto_real_ejecutado',s/'simplecode-propuesta/policy','--all','--enforce')
assert [r['rc'] for r in rows]==[0,1,2,0,0]
Path('tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/controles.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
