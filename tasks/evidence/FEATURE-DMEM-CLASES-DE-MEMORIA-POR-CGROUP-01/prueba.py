"""Pide 256 MiB de un tipo por la API de driver y reporta dmem.current de user.slice y memory.current del cgroup propio."""
import ctypes, sys, time, os
from pathlib import Path
tipo = sys.argv[1]
N = int(os.environ.get("N_MIB","256")) << 20
REG = "nvidia/0000000F:01:00.0/vidmem"
def dmem_user():
    for l in Path("/sys/fs/cgroup/user.slice/dmem.current").read_text(encoding="utf-8").splitlines():
        a = l.split()
        if a[0] == REG: return int(a[1])
    raise SystemExit("la region dmem no esta en user.slice/dmem.current")
def mem_propia():
    cg = Path("/sys/fs/cgroup" + Path("/proc/self/cgroup").read_text(encoding="utf-8").split("::")[1].strip())
    return int((cg / "memory.current").read_text(encoding="utf-8"))
c = ctypes.CDLL("libcuda.so.1")
assert c.cuInit(0) == 0
d = ctypes.c_int(); x = ctypes.c_void_p()
assert c.cuDeviceGet(ctypes.byref(d), 0) == 0 and c.cuDevicePrimaryCtxRetain(ctypes.byref(x), d) == 0 and c.cuCtxSetCurrent(x) == 0
time.sleep(1)  # blocking-sleep: espera fija de 1 s para que dmem.current y memory.current asienten tras la asignacion; no hay evento que esperar -- DEBT-DOCKER-SLICE-TOPE-VS-TOPES-DE-CONTENEDORES-01  # sunset-reviewed: 4.4 -- re-revisado 2026-10-16 contra 4.3 (`git log -L19,19:tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01/prueba.py bade99f4..HEAD`: 0 commits, la linea no cambio desde el release 4.3.0; la razon sigue valiendo); re-revisado 2026-10-16 contra 4.2 (`git log -L18,18:tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01/prueba.py e3b13369..HEAD`: 1 commit, el que creo la linea el mismo dia, 853ea405; es una espera fija de 1 s de una sonda de una sola corrida y la razon sigue valiendo); sonda de medicion de una sola corrida, sin ciclo; si el kernel ofreciera una notificacion de cambio de contador se cambiaria por ella
d0, m0 = dmem_user(), mem_propia()
p = ctypes.c_void_p()
if tipo == "device":   r = c.cuMemAlloc_v2(ctypes.byref(p), ctypes.c_size_t(N))
elif tipo == "managed": r = c.cuMemAllocManaged(ctypes.byref(p), ctypes.c_size_t(N), 1)
elif tipo == "pinned":  r = c.cuMemHostAlloc(ctypes.byref(p), ctypes.c_size_t(N), 0)
elif tipo == "nada":    r = 0
else: sys.exit(2)
if r == 0 and tipo in ("managed", "pinned"):  # tocar las paginas para que existan
    ctypes.memset(p, 1, N)
if r == 0 and tipo == "device": c.cuMemsetD8_v2(p, 1, ctypes.c_size_t(N)); c.cuCtxSynchronize()
time.sleep(1)  # blocking-sleep: espera fija de 1 s para que dmem.current y memory.current asienten tras la asignacion; no hay evento que esperar -- DEBT-DOCKER-SLICE-TOPE-VS-TOPES-DE-CONTENEDORES-01  # sunset-reviewed: 4.4 -- re-revisado 2026-10-16 contra 4.3 (`git log -L30,30:tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01/prueba.py bade99f4..HEAD`: 0 commits, la linea no cambio desde el release 4.3.0; la razon sigue valiendo); re-revisado 2026-10-16 contra 4.2 (`git log -L29,29:tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01/prueba.py e3b13369..HEAD`: 1 commit, el que creo la linea el mismo dia, 853ea405; es una espera fija de 1 s de una sonda de una sola corrida y la razon sigue valiendo); sonda de medicion de una sola corrida, sin ciclo; si el kernel ofreciera una notificacion de cambio de contador se cambiaria por ella
d1, m1 = dmem_user(), mem_propia()
print(f"{tipo:8s} rc={r} dmem_user_delta={(d1-d0)/2**20:8.1f} MiB  memory_current_delta={(m1-m0)/2**20:8.1f} MiB")
