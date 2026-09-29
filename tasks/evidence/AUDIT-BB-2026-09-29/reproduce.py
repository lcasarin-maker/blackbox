import importlib.machinery as m, importlib.util as u, sys, tempfile, pathlib, json, subprocess, io, contextlib
from typing import Any
from unittest.mock import patch
R=pathlib.Path(__file__).resolve().parents[3]
def load(name,path) -> Any:
 l=m.SourceFileLoader(name,str(R/path)); s=u.spec_from_loader(name,l); assert s is not None; x: Any=u.module_from_spec(s);sys.modules[name]=x;l.exec_module(x);return x
class Stop(Exception): pass
with tempfile.TemporaryDirectory() as d:
 g=load('guard_audit','bin/bb-guardia-proceso'); g.SAMPLES_DIR=pathlib.Path(d);g.ESTADO=pathlib.Path(d)/'state';g.EVIDENCIA=pathlib.Path(d)/'events';g.DRY_RUN=True;g.log=lambda *a:None
 p=g.SAMPLES_DIR/(g.time.strftime('%Y-%m-%d')+'.jsonl')
 row={'ts':'2000-01-01T00:00:00+0000','top_rss':[{'pid':999999,'comm':'python3','rss_kb':20*1048576}]}
 p.write_text((json.dumps(row)+'\n')*4, encoding='utf-8')
 with patch.object(g.time,'sleep',side_effect=Stop):
  try:g.main()
  except Stop:pass
 print('H1 historical replay:', [json.loads(l)['accion'] for l in g.EVIDENCIA.read_text(encoding='utf-8').splitlines()])
 p.unlink();g.EVIDENCIA.unlink();g.ESTADO.unlink();calls=[0]
 def tick(_):
  calls[0]+=1
  if calls[0]==1:p.write_text((json.dumps(row)+'\n')*4, encoding='utf-8')
  if calls[0]==3:raise Stop
 with patch.object(g.time,'sleep',side_effect=tick):
  try:g.main()
  except Stop:pass
 print('H2 file created after start: polls=%s events=%s'%(calls[0],g.EVIDENCIA.exists()))
 b=load('usable_audit','bin/bb-usable'); states=[]; seq=iter([99.0]*10+[None]); b.notify=states.append;b.probe=lambda:0.001;b.latencia_x_ms=lambda:1;b.psi_memory_full_avg10=lambda:next(seq)
 with patch.object(b.time,'sleep',lambda _:None),contextlib.redirect_stderr(io.StringIO()):
  try:b.main()
  except StopIteration:pass
 print('H3 collapse then unreadable PSI: last_notify=%s heartbeats=%s'%(states[-1],states.count('WATCHDOG=1')))
 src=(R/'bin/bb').read_text(encoding='utf-8')
 def block(marker):
  s=src.index(marker);s=src.index("python3 -c '\n",s)+len("python3 -c '\n");e=src.index("\n' 2>/dev/null",s);return src[s:e]
 def run(marker,rows):
  r=subprocess.run([sys.executable,'-c',block(marker)],input='\n'.join(map(json.dumps,rows)),text=True,capture_output=True);return r.stdout.strip(),r.returncode
 print('H4 old samples CPU:',run('# --- 7b.',[{'ts':'2000-01-01T00:00:00','cpu_jiffies':'cpu0:0:100','red':'eth0:0:0'},{'ts':'2000-01-01T00:01:00','cpu_jiffies':'cpu0:0:200','red':'eth0:1024:1024'}]))
 print('H5 emptied GPU list:',run('# --- 8c.',[{'gpu_util_pct':90,'gpu_procs':[{'nombre':'already-exited','mem_mib':100}]}]+[{'gpu_util_pct':0,'gpu_procs':[]}]*3))
 print('H6 malformed JSON:',run('# --- 7b.',[{},{}]))
 t=load('thermal_audit','tools/atom_gpu_telemetry.py'); signals=[];state={'en_alarma':True}
 t.mitigar([{'evento':'temp_critica','carga_gpu':'con_carga'}],state,listar_pids=lambda:[999999],enviar_senal=lambda *x:signals.append(x))
 t.mitigar([],{},listar_pids=lambda:[],enviar_senal=lambda *x:signals.append(x))
 print('H7 thermal restart state loss:',[(p,s.name) for p,s in signals])
t=load('thermal_dry_audit','tools/atom_gpu_telemetry.py'); seen=[]
with patch.object(sys,'argv',['atom_gpu_telemetry.py','--dry-run','--once']),patch.object(t,'leer_umbrales',lambda:{}),patch.object(t,'leer_zonas',lambda:[]),patch.object(t,'leer_gpu',lambda:{}),patch.object(t,'leer_memoria_sistema',lambda:{}),patch.object(t,'leer_vllm_metrics',lambda:{}),patch.object(t,'leer_procesos_gpu',lambda:{}),patch.object(t,'vigilar_journal',lambda s:([],None)),patch.object(t,'_alarmas',lambda *a:[{'evento':'temp_critica','carga_gpu':'con_carga'}]),patch.object(t,'pids_mitigables',lambda:[999999]),patch.object(t.os,'kill',lambda p,s:seen.append((p,s.name))),contextlib.redirect_stdout(io.StringIO()):
 t.main()
print('H8 --dry-run --once signals:',seen)
