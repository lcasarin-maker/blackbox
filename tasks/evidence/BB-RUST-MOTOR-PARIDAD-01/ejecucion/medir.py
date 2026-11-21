#!/usr/bin/python3
"""Medición offline; ejecutar únicamente dentro del bwrap descrito en ejecutar.sh."""
import json, math, os, resource, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path('/repo')
BASE = Path('/work')
ENV = {'PATH': '/work/bin:/usr/bin:/bin', 'HOME': '/work', 'BLACKBOX_DATA': '/work/data',
       'VIGILANTE_UNIDAD': 'ficticia.service', 'VIGILANTE_SNAPSHOT_CMD': '/work/bin/snapshot',
       'BLACKBOX_MOTOR_CONFIG': '/work/config.json', 'LC_ALL': 'C'}
DATA = BASE / 'data'
LOG = BASE / 'effects.log'

def tick():
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.monotonic()
    p = subprocess.run(['/repo/bin/bb-vigilante-motor'], env=ENV, capture_output=True, text=True, timeout=30)
    elapsed = time.monotonic() - start
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
    if p.returncode or p.stderr: raise RuntimeError(f'vigilante rc={p.returncode} stdout={p.stdout} stderr={p.stderr}')
    return elapsed, cpu

def clear():
    import shutil
    shutil.rmtree(DATA, ignore_errors=True)
    LOG.unlink(missing_ok=True)
    DATA.mkdir()

def effect():
    return LOG.read_text().splitlines() if LOG.exists() else []

def request(name, action='reiniciar', seconds=0, **extra):
    path = DATA / 'motor/solicitudes' / (name + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    path.write_text(json.dumps(dict(esquema='bb-motor-solicitud/1', id=name, accion=action,
                                    origen='sintetico', creada=now.isoformat(), plazo_s=900, **extra)))

def response(name):
    return json.loads((DATA / 'motor/respuestas' / (name + '.json')).read_text())

def check(ok, label):
    print(('PASS ' if ok else 'FAIL ') + label, flush=True)
    if not ok: raise AssertionError(label)

def exceeds(rows):
    vals = sorted(x[0] for x in rows)
    return vals[math.ceil(.95 * len(vals)) - 1] > 1.2

def summary(name, rows):
    vals = sorted(x[0] for x in rows)
    cpus = sorted(x[1] for x in rows)
    print(f'{name}: n={len(vals)} p95_s={vals[math.ceil(.95*len(vals))-1]:.6f} max_s={max(vals):.6f} cpu_p95_s={cpus[math.ceil(.95*len(cpus))-1]:.6f} cpu_max_s={max(cpus):.6f}', flush=True)
    return vals[math.ceil(.95*len(vals))-1]

def main():
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == 'diagnostic':
            clear()
            for i in range(100): request(f'r{i:03}')
            cmd=['/usr/bin/strace','-f','-c','-w','-e','trace=fsync,fdatasync,rename,renameat,renameat2','/repo/bin/bb-vigilante-motor']
            print('diagnostic command:', ' '.join(cmd), flush=True)
            p=subprocess.run(cmd,env=ENV,capture_output=True,text=True,timeout=60)
            print('subject stdout:',p.stdout,flush=True); print('strace stderr:',p.stderr,flush=True)
            check(p.returncode==0 and '/repo/bin/bb-vigilante-motor: line' not in p.stderr and len(list((DATA/'motor/respuestas').glob('*.json')))==100, 'diagnostico procesa 100')
        elif mode == 'negative-delay':
            ENV['FAKE_DELAY'] = '1.3'; clear(); elapsed, cpu = tick()
            check(exceeds([(elapsed, cpu)]), f'control demora {elapsed:.6f} > 1.2')
        elif mode == 'negative-functional':
            clear(); request('bad', action='borrar'); tick()
            path=DATA/'motor/respuestas/bad.json'; altered=json.loads(path.read_text()); altered['estado']='hecha'; path.write_text(json.dumps(altered))
            check(response('bad')['estado'] == 'rechazada', 'desvio sintetico detectado')
        elif mode == 'negative-unavailable':
            subprocess.run(['/instrumento-inexistente'], check=True)
        return
    print('ISOLATION_CHECK', flush=True)
    try:
        (ROOT/'.isolation-write-probe').write_text('x')
        readonly = False
    except OSError:
        readonly = True
    (BASE/'write-probe').write_text('ok')
    check(readonly and (BASE/'write-probe').read_text() == 'ok', 'repo solo lectura y destino escribible')
    print('namespaces', *(os.readlink('/proc/self/ns/'+n) for n in ('pid','net','ipc')), flush=True)
    check(not Path('/run/user').exists() and not Path('/var/run').exists(), 'sockets host ausentes')
    check(not Path('/repo/.git').is_dir(), 'git administrativo inaccesible')
    clear()
    normal=[]
    for _ in range(20): normal.append(tick())
    heartbeat=json.loads((DATA/'motor/manejador.json').read_text())
    check(heartbeat['latido_s']==600 and heartbeat['unidad']=='ficticia.service', 'latido')
    check(not any(' restart ' in (' '+x+' ') for x in effect()), 'normal sin reinicio')
    pnormal=summary('normal',normal)
    load=[]
    for iteration in range(20):
        clear()
        for i in range(100): request(f'r{i:03}')
        load.append(tick())
        check(len(list((DATA/'motor/respuestas').glob('*.json')))==100 and all(response(f'r{i:03}')['estado']=='hecha' for i in range(100)), f'carga {iteration} respuestas')
        check(sum(' restart ' in (' '+x+' ') for x in effect())==1, f'carga {iteration} deduplicacion')
    pload=summary('carga_100',load)
    print('carga: 20 vueltas, 100 solicitudes procesadas por vuelta, una accion restart testigo por vuelta',flush=True)
    clear(); request('bad', action='borrar'); request('old',seconds=-901); tick()
    check(response('bad')['estado']=='rechazada' and response('old')['estado']=='rechazada' and not any(' restart ' in (' '+x+' ') for x in effect()), 'rechazo y plazo')
    clear(); request('open',action='ventana',ventana={'duracion_s':3600,'motivo':'sintetico','compensacion':{'accion':'arrancar'}}); tick()
    check(response('open')['estado']=='hecha' and json.loads((DATA/'motor/manejador.json').read_text())['ventana']['id']=='open','ventana vigente')
    request('close',action='ventana',ventana={'duracion_s':0,'motivo':'cierre'}); tick()
    check(response('close')['estado']=='hecha' and any(' start ' in (' '+x+' ') for x in effect()), 'cierre y compensacion')
    clear(); request('open',action='ventana',ventana={'duracion_s':3600,'motivo':'sintetico','compensacion':{'accion':'arrancar'}}); tick()
    ENV['FAKE_CHAT']='000'
    for _ in range(3): tick()
    check(not any(' restart ' in (' '+x+' ') for x in effect()) and not (DATA/'vigilante_motor.presupuesto').exists(), 'ventana suprime reinicio y gasto')
    clear()
    for _ in range(3): tick()
    check(sum(' restart ' in (' '+x+' ') for x in effect())==1 and (DATA/'vigilante_motor.presupuesto').exists(), 'sin ventana reinicia y gasta')
    clear(); request('expired',action='ventana',ventana={'duracion_s':3600,'motivo':'sintetico','compensacion':{'accion':'arrancar'}}); tick()
    window=DATA/'motor/ventana.json'; obj=json.loads(window.read_text()); obj['hasta']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(); window.write_text(json.dumps(obj)); tick()
    check(not window.exists() and any(' start ' in (' '+x+' ') for x in effect()), 'ventana vencida compensa')
    clear(); ENV['FAKE_CHAT']='000'
    for _ in range(12): tick()
    check(sum(' restart ' in (' '+x+' ') for x in effect())==3 and (DATA/'motor_alerta.json').exists(), 'presupuesto tres y cuarto bloqueado')
    check(sum(x.startswith('snapshot ') for x in effect())==1 and sum(x.startswith('notify ') for x in effect())==1, 'alertas secas')
    ENV.pop('FAKE_CHAT')
    print(f'DECISION p95_normal={pnormal:.6f} p95_carga={pload:.6f} criterio_s=1.2 disparador={exceeds(normal) or exceeds(load)}',flush=True)

try: main()
except AssertionError as exc:
    print(f'FAIL {exc}', flush=True); sys.exit(1)
except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
    print(f'COULD_NOT_RUN {type(exc).__name__}: {exc}', flush=True); sys.exit(2)
except Exception as exc:
    print(f'COULD_NOT_RUN {type(exc).__name__}: {exc}', flush=True); sys.exit(2)
