"""DGX-334: sampler de telemetría de GPU y térmica (tools/atom_gpu_telemetry.py).

Todo lo que toca el sistema real se sustituye: `_correr` (el único punto que
invoca a `nvidia-smi`) y `THERMAL_DIR` (el único punto que lee sysfs). Se
construye un `/sys/class/thermal` falso en `tmp_path` con la misma forma que la
ATOM real —7 zonas `acpitz`, un solo `trip_point_0_temp` de 104.8 °C— en vez de
mockear `open`, para que la prueba ejercite el parseo de sysfs de verdad.
"""
import json
import os

import pytest

from tools import atom_gpu_telemetry as agt

TRIP_MILIC = 104800  # 104.8 °C, medido en vivo en la ATOM el 2026-08-31
SALIDA_NVIDIA_SMI = "77, 93, 41.45, 2502, P0, 0x0000000000000000\n"


def _crear_zona(base, indice: int, temp_c: float, *, con_trip: bool = True) -> None:
    zona = base / f"thermal_zone{indice}"
    zona.mkdir(parents=True)
    (zona / "type").write_text("acpitz\n", encoding="utf-8")
    (zona / "temp").write_text(f"{int(temp_c * 1000)}\n", encoding="utf-8")
    if con_trip:
        (zona / "trip_point_0_temp").write_text(f"{TRIP_MILIC}\n", encoding="utf-8")
        (zona / "trip_point_0_type").write_text("critical\n", encoding="utf-8")


def _fijar_temp(base, indice: int, temp_c: float) -> None:
    (base / f"thermal_zone{indice}" / "temp").write_text(
        f"{int(temp_c * 1000)}\n", encoding="utf-8")


@pytest.fixture
def thermal(tmp_path, monkeypatch):
    """Réplica de la máquina real bajo carga pesada: 7 zonas, la más caliente
    a 86.2 °C, todas con el mismo trip `critical` de 104.8 °C."""
    base = tmp_path / "thermal"
    base.mkdir()
    for i, temp in enumerate([86.2, 76.0, 86.2, 76.5, 85.2, 83.0, 79.1]):
        _crear_zona(base, i, temp)
    monkeypatch.setattr(agt, "THERMAL_DIR", base)
    monkeypatch.setattr(agt, "JSONL_PATH", tmp_path / "telemetria.jsonl")
    return base


@pytest.fixture
def gpu_ok(monkeypatch):
    monkeypatch.setattr(agt, "_correr", lambda *args: SALIDA_NVIDIA_SMI)


# La muestra REAL de las 2026-09-01T02:42:16Z, uno de los 27 minutos previos al
# quinto crash de DGX-342: 87.05 W, por encima de `CARGA_MINIMA_W = 60.0`.
# `SALIDA_NVIDIA_SMI` declara 41.45 W y desde DGX-408 eso es `ocioso`, así que
# ya no puede disparar la mitigación -- un GPU bajo carga es un sujeto distinto
# y necesita su propia salida de `nvidia-smi`.
SALIDA_NVIDIA_SMI_CARGADO = "83, 96, 87.05, 2502, P0, 0x0000000000000000\n"


@pytest.fixture
def gpu_cargado(monkeypatch):
    monkeypatch.setattr(agt, "_correr", lambda *args: SALIDA_NVIDIA_SMI_CARGADO)


# --- DGX-336: vigilancia de pérdida de video ------------------------------
#
# Líneas REALES del journal de la ATOM, no inventadas. La ráfaga es la del
# 2026-08-30 07:38:47 (boot `485fe3f1`), copiada verbatim; el ruido sano sale
# del boot actual y de los tres anteriores.
XID_13 = ("NVRM: Xid (PCI:000f:01:00): 13, Graphics SM Warp Exception on "
          "(GPC 0, TPC 0, SM 0): Out Of Range Address")
XID_13_BIS = ("NVRM: Xid (PCI:000f:01:00): 13, Graphics SM Global Exception on "
              "(GPC 0, TPC 1, SM 2): Multiple Warp Errors")
XID_43 = ("NVRM: Xid (PCI:000f:01:00): 43, pid=39320, name=python3, "
          "channel 0x0000000e")
RUIDO_SANO = [
    "[drm] Initialized nvidia-drm 0.0.0 for 000f:01:00.0 on minor 1",
    "[drm] [nvidia-drm] [GPU ID 0x000f0100] Loading driver",
    "[drm] Initialized simpledrm 1.0.0 for simple-framebuffer.0 on minor 0",
    "simple-framebuffer simple-framebuffer.0: [drm] Registered 1 planes with drm panic",
    "simple-framebuffer simple-framebuffer.0: [drm] fb0: simpledrmdrmfb frame buffer device",
    "ACPI: bus type drm_connector registered",
]
# El falso positivo real que el control negativo del 2026-08-31 cazó: la línea
# de kdump repite la línea de comandos del kernel, donde `plymouth.use-simpledrm`
# y `reset_devices` conviven sin tener nada que ver.
CMDLINE_KDUMP = (
    '/sbin/kexec -p -s --command-line="BOOT_IMAGE=/boot/vmlinuz-6.17.0-1031-nvidia '
    'root=UUID=14775751-e6a7-4614-8ee1-e3aedc5d7ada ro plymouth.use-simpledrm '
    'reset_devices"')
GDM_RUIDO = ("Gdm: on_display_added: assertion "
             "'GDM_IS_REMOTE_DISPLAY (display)' failed")
GDM_CAIDO = "gdm.service: Main process exited, code=exited, status=1/FAILURE"

# `__REALTIME_TIMESTAMP` exacto de la primera línea Xid de la ráfaga, leído del
# journal de esta máquina: 2026-08-30T13:38:47.202868Z (07:38:47 CST).
TS_BASE = 1_788_097_127_202_868


def _entrada(mensaje: str, *, us: int, transporte: str = "kernel",
             ident: str = "kernel", cursor: str | None = None) -> dict:
    return {"MESSAGE": mensaje, "SYSLOG_IDENTIFIER": ident,
            "_TRANSPORT": transporte, "__REALTIME_TIMESTAMP": str(us),
            "__CURSOR": cursor or f"c{us}_{abs(hash(mensaje)) % 10**6}"}


class JournalFalso:
    """Sustituto de `journalctl` que respeta el contrato que el sampler usa:
    `-n 0 --show-cursor` devuelve el cursor de la COLA, y `--after-cursor C`
    devuelve sólo lo posterior a C.

    Reimplementar el avance del cursor —en vez de devolver siempre lo mismo— es
    lo que hace que `test_dos_lecturas_seguidas_no_duplican` pueda FALLAR: con
    un stub que ignorara `--after-cursor`, ese test pasaría aunque el sampler
    releyera el journal entero en cada muestra."""

    def __init__(self, entradas=()):
        self.entradas = list(entradas)
        self.llamadas: list[tuple] = []

    def __call__(self, *args: str) -> str:
        self.llamadas.append(args)
        if "--show-cursor" in args:
            if not self.entradas:
                return "-- No entries --\n"
            return f"-- cursor: {self.entradas[-1]['__CURSOR']}\n"
        cursor = args[args.index("--after-cursor") + 1]
        indice = next((i for i, e in enumerate(self.entradas)
                       if e["__CURSOR"] == cursor), None)
        nuevas = self.entradas if indice is None else self.entradas[indice + 1:]
        return "".join(json.dumps(e) + "\n" for e in nuevas)

    def agregar(self, *entradas: dict) -> None:
        self.entradas.extend(entradas)


@pytest.fixture(autouse=True)
def journal_mudo(monkeypatch):
    """Por defecto: un journal que existe y no tiene nada nuevo que decir. Los
    tests térmicos de DGX-334 no deben tocar el journalctl real de la máquina
    donde corra la suite, y tampoco deben ver `journal_ausente` —que es una
    declaración de instrumento caído, no de silencio—. Los tests de DGX-336
    sustituyen esto por su propio `JournalFalso`."""
    monkeypatch.setattr(agt, "_correr_journalctl",
                        lambda *args: ("-- cursor: silencio\n"
                                       if "--show-cursor" in args else ""))


def _con_journal(monkeypatch, entradas) -> JournalFalso:
    falso = JournalFalso(entradas)
    monkeypatch.setattr(agt, "_correr_journalctl", falso)
    return falso


def _leer_jsonl() -> list[dict]:
    return [json.loads(ln)
            for ln in agt.JSONL_PATH.read_text(encoding="utf-8").splitlines()]


def _estado() -> dict:
    return {"en_alarma": set(), "inicio": {}}


def test_muestra_normal_escribe_la_linea_esperada(thermal, gpu_ok):
    umbrales = agt.leer_umbrales()
    eventos = agt.muestrear(umbrales, _estado(), escribir=True)

    assert len(eventos) == 1  # sólo la muestra, ninguna alarma
    muestra = eventos[0]
    assert muestra["evento"] == "muestra"
    assert muestra["gpu_temp_c"] == 77.0
    assert muestra["gpu_util_pct"] == 93.0
    assert muestra["gpu_power_w"] == 41.45
    assert "gpu_ausente" not in muestra
    assert len(muestra["zonas"]) == 7
    assert muestra["zonas"][0] == {"zona": "thermal_zone0", "type": "acpitz",
                                  "temp_c": 86.2}
    # Los 7 `type` son el mismo string: la lista conserva las 7 lecturas donde
    # un dict tecleado por tipo habría dejado una sola.
    assert [z["type"] for z in muestra["zonas"]] == ["acpitz"] * 7
    assert len({z["temp_c"] for z in muestra["zonas"]}) > 1

    filas = _leer_jsonl()
    assert len(filas) == 1
    assert filas[0]["zonas"][4]["temp_c"] == 85.2


def test_umbral_se_deriva_del_trip_de_cada_zona(thermal):
    umbrales = agt.leer_umbrales()
    assert len(umbrales) == 7
    assert umbrales["thermal_zone0"]["trip_c"] == 104.8
    assert umbrales["thermal_zone0"]["umbral_c"] == 94.8  # 104.8 - MARGEN_TRIP_C


def test_orden_natural_de_zonas_mas_alla_de_la_novena(tmp_path, monkeypatch):
    """`thermal_zone10` va después de `thermal_zone9`, no entre el 1 y el 2."""
    base = tmp_path / "thermal"
    base.mkdir()
    for i in (0, 1, 2, 9, 10, 11):
        _crear_zona(base, i, 50.0)
    monkeypatch.setattr(agt, "THERMAL_DIR", base)
    assert [z["zona"] for z in agt.leer_zonas()] == [
        "thermal_zone0", "thermal_zone1", "thermal_zone2",
        "thermal_zone9", "thermal_zone10", "thermal_zone11"]


def test_control_negativo_temperaturas_sanas_no_disparan_alarma(thermal, gpu_ok):
    """El instrumento TIENE que poder decir 'nada que reportar': las 7 zonas
    bajo carga pesada real (85-86 °C) están lejos del umbral de 94.8 °C."""
    umbrales = agt.leer_umbrales()
    estado = _estado()

    for _ in range(3):
        eventos = agt.muestrear(umbrales, estado, escribir=True)
        assert [e["evento"] for e in eventos] == ["muestra"]

    assert estado["en_alarma"] == set()
    assert all(f["evento"] == "muestra" for f in _leer_jsonl())


def test_control_positivo_cruzar_el_umbral_dispara_una_sola_vez(thermal, gpu_ok):
    """Control positivo + debounce en la misma corrida: el evento aparece en la
    transición y NO se repite mientras la zona siga arriba del umbral."""
    umbrales = agt.leer_umbrales()
    estado = _estado()
    agt.muestrear(umbrales, estado, escribir=True)  # sana

    _fijar_temp(thermal, 3, 96.0)  # cruza 94.8
    eventos = agt.muestrear(umbrales, estado, escribir=True)
    alarmas = [e for e in eventos if e["evento"] == "temp_critica"]
    assert len(alarmas) == 1
    assert alarmas[0]["zona"] == "thermal_zone3"
    assert alarmas[0]["temp_c"] == 96.0
    assert alarmas[0]["umbral_c"] == 94.8
    assert alarmas[0]["trip_c"] == 104.8

    _fijar_temp(thermal, 3, 99.0)  # sigue arriba, incluso más alto
    eventos = agt.muestrear(umbrales, estado, escribir=True)
    assert [e["evento"] for e in eventos] == ["muestra"]

    assert sum(f["evento"] == "temp_critica" for f in _leer_jsonl()) == 1


def test_volver_a_bajar_dispara_temp_normalizada(thermal, gpu_ok):
    umbrales = agt.leer_umbrales()
    estado = _estado()
    _fijar_temp(thermal, 3, 96.0)
    agt.muestrear(umbrales, estado, escribir=True)

    _fijar_temp(thermal, 3, 76.5)
    eventos = agt.muestrear(umbrales, estado, escribir=True)
    normalizadas = [e for e in eventos if e["evento"] == "temp_normalizada"]
    assert len(normalizadas) == 1
    assert normalizadas[0]["zona"] == "thermal_zone3"
    assert normalizadas[0]["segundos_en_alarma"] >= 0
    assert estado["en_alarma"] == set()

    # Y volver a cruzar reabre el episodio: el debounce no deja la zona muda.
    _fijar_temp(thermal, 3, 96.0)
    eventos = agt.muestrear(umbrales, estado, escribir=True)
    assert any(e["evento"] == "temp_critica" for e in eventos)


def test_histeresis_evita_pares_de_eventos_al_oscilar(thermal, gpu_ok):
    """Justo por debajo del umbral pero dentro de la histéresis (94.8 - 2.0):
    la zona sigue en alarma y no se emite `temp_normalizada`."""
    umbrales = agt.leer_umbrales()
    estado = _estado()
    _fijar_temp(thermal, 3, 96.0)
    agt.muestrear(umbrales, estado, escribir=True)

    _fijar_temp(thermal, 3, 94.0)
    eventos = agt.muestrear(umbrales, estado, escribir=True)
    assert [e["evento"] for e in eventos] == ["muestra"]
    assert estado["en_alarma"] == {"thermal_zone3"}


def test_nvidia_smi_ausente_no_tumba_el_sampler(thermal, monkeypatch):
    def _falta(*args):
        raise FileNotFoundError(2, "No such file or directory", "nvidia-smi")

    monkeypatch.setattr(agt, "_correr", _falta)
    eventos = agt.muestrear(agt.leer_umbrales(), _estado(), escribir=True)

    muestra = eventos[0]
    assert muestra["gpu_temp_c"] is None
    assert "nvidia-smi no ejecutable" in muestra["gpu_ausente"]
    # La ausencia se declara, pero las zonas térmicas se siguen registrando.
    assert len(muestra["zonas"]) == 7
    assert _leer_jsonl()[0]["gpu_ausente"]


def test_nvidia_smi_falla_y_devuelve_vacio_declara_la_ausencia(thermal, monkeypatch):
    monkeypatch.setattr(agt, "_correr", lambda *args: "")
    muestra = agt.muestrear(agt.leer_umbrales(), _estado(), escribir=True)[0]
    assert "no devolvió 6 columnas" in muestra["gpu_ausente"]


def test_campo_na_del_gb10_se_declara_no_se_finge(thermal, monkeypatch):
    """En el GB10 la memoria es unificada y `nvidia-smi` devuelve `[N/A]`; un
    `[N/A]` en cualquier columna se registra como hueco, nunca como 0."""
    monkeypatch.setattr(agt, "_correr", lambda *args: "77, [N/A], 41.45, 2502, P0, 0x0000000000000000\n")
    muestra = agt.muestrear(agt.leer_umbrales(), _estado(), escribir=True)[0]
    assert muestra["gpu_util_pct"] is None
    assert "gpu_util_pct" in muestra["gpu_ausente"]
    assert muestra["gpu_temp_c"] == 77.0


def test_sin_zonas_termicas_declara_la_ausencia(tmp_path, monkeypatch, gpu_ok):
    base = tmp_path / "thermal_vacio"
    base.mkdir()
    monkeypatch.setattr(agt, "THERMAL_DIR", base)
    monkeypatch.setattr(agt, "JSONL_PATH", tmp_path / "telemetria.jsonl")

    assert agt.leer_umbrales() == {}
    muestra = agt.muestrear({}, _estado(), escribir=True)[0]
    assert muestra["zonas"] == []
    assert "sin zonas térmicas" in muestra["zonas_ausentes"]


def test_zona_sin_trip_point_no_puede_alarmar_pero_si_se_registra(tmp_path,
                                                                 monkeypatch,
                                                                 gpu_ok):
    base = tmp_path / "thermal"
    base.mkdir()
    _crear_zona(base, 0, 99.0, con_trip=False)
    monkeypatch.setattr(agt, "THERMAL_DIR", base)
    monkeypatch.setattr(agt, "JSONL_PATH", tmp_path / "telemetria.jsonl")

    umbrales = agt.leer_umbrales()
    assert umbrales["thermal_zone0"]["umbral_c"] is None
    eventos = agt.muestrear(umbrales, _estado(), escribir=True)
    assert [e["evento"] for e in eventos] == ["muestra"]
    assert eventos[0]["zonas"][0]["temp_c"] == 99.0


def test_rotacion_trunca_cuando_supera_el_tope(tmp_path, monkeypatch):
    monkeypatch.setattr(agt, "JSONL_PATH", tmp_path / "telemetria.jsonl")
    monkeypatch.setattr(agt, "MAX_LINEAS", 100)
    monkeypatch.setattr(agt, "LINEAS_A_CONSERVAR", 50)
    agt.JSONL_PATH.write_text(
        "".join(json.dumps({"n": i}) + "\n" for i in range(150)),
        encoding="utf-8")

    recortadas = agt.rotar_si_hace_falta()

    assert recortadas == 100
    filas = _leer_jsonl()
    assert len(filas) == 50
    assert filas[0]["n"] == 100  # se conserva la COLA, que es lo reciente
    assert filas[-1]["n"] == 149


def test_control_negativo_rotacion_no_toca_un_archivo_bajo_el_tope(tmp_path,
                                                                  monkeypatch):
    monkeypatch.setattr(agt, "JSONL_PATH", tmp_path / "telemetria.jsonl")
    monkeypatch.setattr(agt, "MAX_LINEAS", 100)
    contenido = "".join(json.dumps({"n": i}) + "\n" for i in range(100))
    agt.JSONL_PATH.write_text(contenido, encoding="utf-8")

    assert agt.rotar_si_hace_falta() is None
    assert agt.JSONL_PATH.read_text(encoding="utf-8") == contenido


def test_rotacion_sin_archivo_previo_no_falla(tmp_path, monkeypatch):
    monkeypatch.setattr(agt, "JSONL_PATH", tmp_path / "no_existe.jsonl")
    assert agt.rotar_si_hace_falta() is None


def test_once_toma_una_muestra_y_sale_sin_loop(thermal, gpu_ok, monkeypatch):
    """`--once` es lo que hace testeable un proceso cuyo modo normal es un loop
    infinito; sin él la única forma de ejercitar `main()` sería un timeout."""
    monkeypatch.setattr(agt.sys, "argv", ["atom_gpu_telemetry.py", "--once"])
    monkeypatch.setattr(agt.time, "sleep",
                        lambda s: pytest.fail("--once no debe dormir nunca"))

    assert agt.main() == 0

    eventos = _leer_jsonl()
    assert [e["evento"] for e in eventos] == ["arranque", "muestra"]
    assert eventos[0]["margen_trip_c"] == 10.0
    assert eventos[0]["umbrales"]["thermal_zone0"]["umbral_c"] == 94.8
    assert eventos[0]["lineas_recortadas"] is None
    assert eventos[1]["gpu_temp_c"] == 77.0


def test_dry_run_no_escribe_el_jsonl(thermal, gpu_ok, monkeypatch, capsys):
    monkeypatch.setattr(agt.sys, "argv",
                        ["atom_gpu_telemetry.py", "--once", "--dry-run"])
    assert agt.main() == 0
    assert not agt.JSONL_PATH.exists()
    assert "muestra" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# DGX-336: pérdida de video sin crash completo
# ---------------------------------------------------------------------------

def test_primera_iteracion_solo_fija_la_linea_base(monkeypatch):
    """Sin semilla, `--after-cursor` no existe y el sampler recorrería los 24
    boots del journal alarmando por crashes ya diagnosticados. La primera
    iteración fija el cursor de la cola y NO emite nada."""
    falso = _con_journal(monkeypatch, [_entrada(XID_43, us=TS_BASE)])
    estado = {}

    eventos, ausente = agt.vigilar_journal(estado)

    assert eventos == []
    assert ausente is None
    assert estado["cursor"] == falso.entradas[-1]["__CURSOR"]
    # Y a partir de ahí sólo mira lo posterior: nada nuevo, ninguna alerta.
    assert agt.vigilar_journal(estado) == ([], None)


def test_rafaga_real_colapsa_en_un_evento_por_codigo_xid(monkeypatch):
    """Las 145 líneas Xid del 2026-08-30 07:38:47 caen en el MISMO segundo.
    Deben contar como dos eventos —uno por código— y no como 145 alertas."""
    entradas = [_entrada(XID_13 if i % 2 else XID_13_BIS, us=TS_BASE + i * 200)
                for i in range(144)]
    entradas.append(_entrada(XID_43, us=TS_BASE + 30_086))
    _con_journal(monkeypatch, entradas)
    estado = {"cursor": "semilla", "anclas": {}}

    eventos, _ = agt.vigilar_journal(estado)

    assert [e["evento"] for e in eventos] == ["hardware_alerta"] * 2
    assert [e["xid"] for e in eventos] == [13, 43]
    # Lo suprimido se cuenta, no se pierde.
    assert eventos[0]["lineas_suprimidas"] == 143
    assert eventos[1]["lineas_suprimidas"] == 0
    assert eventos[1]["pid"] == 39320  # el driver nombra al proceso ofensor
    assert eventos[0]["tipo"] == "xid"
    assert eventos[0]["ts_journal"].startswith("2026-08-30")


def test_dos_lecturas_seguidas_no_duplican_el_mismo_evento(monkeypatch):
    """El mecanismo de 'sólo lo nuevo': la segunda lectura no vuelve a ver la
    línea que la primera ya reportó, porque el cursor avanzó."""
    falso = _con_journal(monkeypatch, [_entrada(XID_43, us=TS_BASE)])
    estado = {"cursor": "semilla", "anclas": {}}

    primeros, _ = agt.vigilar_journal(estado)
    segundos, _ = agt.vigilar_journal(estado)

    assert len(primeros) == 1
    assert segundos == []
    assert estado["cursor"] == falso.entradas[-1]["__CURSOR"]

    # Control positivo del mismo mecanismo: una línea NUEVA sí se reporta, o el
    # test anterior sólo estaría probando que el sampler quedó mudo.
    falso.agregar(_entrada(XID_43, us=TS_BASE + 60_000_000))
    terceros, _ = agt.vigilar_journal(estado)
    assert [e["xid"] for e in terceros] == [43]


def test_control_negativo_boot_sano_no_dispara_nada(monkeypatch):
    """Las líneas `[drm] Initialized ...` y `[drm] Registered ... drm panic` que
    TODO arranque sano escribe no son eventos, son registro de subsistemas."""
    _con_journal(monkeypatch, [_entrada(m, us=TS_BASE + i)
                               for i, m in enumerate(RUIDO_SANO)])

    eventos, ausente = agt.vigilar_journal({"cursor": "semilla", "anclas": {}})

    assert eventos == []
    assert ausente is None


def test_control_negativo_cmdline_de_kdump_no_es_un_reset_de_drm(monkeypatch):
    """Falso positivo REAL medido el 2026-08-31: `plymouth.use-simpledrm` y
    `reset_devices` en la misma línea de comandos del kernel. Aparece una vez
    por boot, así que sin esta exclusión el sampler alarmaría en cada arranque
    sano."""
    assert agt.clasificar_linea(CMDLINE_KDUMP, "kernel") is None
    _con_journal(monkeypatch, [_entrada(CMDLINE_KDUMP, us=TS_BASE,
                                        transporte="syslog",
                                        ident="kdump-tools")])
    eventos, _ = agt.vigilar_journal({"cursor": "semilla", "anclas": {}})
    assert eventos == []


def test_una_linea_de_syslog_no_puede_fingir_un_xid():
    """El texto exacto que el kernel usa, escrito por un proceso cualquiera vía
    `logger`, NO es evidencia de hardware. Caso real: el probe de esta misma
    sesión entró en el control negativo del boot sano hasta que el transporte
    pasó a ser parte del patrón."""
    linea = "NVRM: Xid (PCI:000f:01:00): 79, GPU has fallen off the bus"
    assert agt.clasificar_linea(linea, "syslog") is None
    # Control positivo: la MISMA línea por transporte kernel sí se clasifica.
    hallazgo = agt.clasificar_linea(linea, "kernel")
    assert hallazgo is not None
    assert hallazgo["tipo"] == "gpu_fuera_del_bus"
    assert hallazgo["xid"] == 79


def test_el_patron_ingenuo_de_xid_no_habria_visto_la_rafaga_real():
    """El número va después del paréntesis con la dirección PCI. `Xid\\s+\\d+`
    matchea CERO de las líneas reales de esta máquina -- por eso el patrón del
    catálogo tiene el paréntesis opcional en medio."""
    import re
    assert re.search(r"Xid\s+\d+", XID_13) is None
    hallazgo_13 = agt.clasificar_linea(XID_13, "kernel")
    assert hallazgo_13 is not None
    assert hallazgo_13["xid"] == 13
    # Y la forma pelada de otros drivers sigue entrando.
    hallazgo_62 = agt.clasificar_linea("NVRM: Xid 62: halt", "kernel")
    assert hallazgo_62 is not None
    assert hallazgo_62["xid"] == 62


def test_gdm_caido_dispara_y_su_ruido_de_cada_logout_no(monkeypatch):
    """`gdm_caido` mira al `systemd[1]` que reporta la unidad. El patrón
    intuitivo sobre `gdm3[pid]` daba 73 falsos positivos sobre 348 líneas de
    historia real de gdm en esta máquina."""
    _con_journal(monkeypatch, [
        _entrada(GDM_RUIDO, us=TS_BASE, transporte="syslog", ident="gdm3"),
        _entrada(GDM_CAIDO, us=TS_BASE + 1_000_000, transporte="syslog",
                 ident="systemd"),
    ])

    eventos, _ = agt.vigilar_journal({"cursor": "semilla", "anclas": {}})

    assert [e["tipo"] for e in eventos] == ["gdm_caido"]
    assert "Main process exited" in eventos[0]["linea_cruda"]


def test_una_falla_que_persiste_vuelve_a_alertar_pasada_la_ventana(monkeypatch):
    """La ventana calla la RÁFAGA, no el fenómeno: dos líneas separadas por más
    de `VENTANA_DEDUPE_S` son dos eventos, o una GPU muriendo durante horas se
    reportaría una sola vez y parecería un incidente puntual."""
    lejos = int(TS_BASE + (agt.VENTANA_DEDUPE_S + 1) * 1_000_000)
    _con_journal(monkeypatch, [_entrada(XID_43, us=TS_BASE),
                               _entrada(XID_43, us=lejos)])

    eventos, _ = agt.vigilar_journal({"cursor": "semilla", "anclas": {}})

    assert len(eventos) == 2
    assert all(e["lineas_suprimidas"] == 0 for e in eventos)


def test_journalctl_sin_cursor_declara_la_ausencia(thermal, gpu_ok, monkeypatch):
    """Un journal que no contesta se declara en la muestra, igual que
    `gpu_ausente` -- omitir el campo se leería como 'no pasó nada'."""
    monkeypatch.setattr(agt, "_correr_journalctl", lambda *args: "")

    muestra = agt.muestrear(agt.leer_umbrales(), _estado(), escribir=True)[0]

    assert "no devolvió cursor" in muestra["journal_ausente"]
    assert _leer_jsonl()[0]["journal_ausente"]


def test_mensaje_no_utf8_llega_como_lista_de_bytes(monkeypatch):
    """`-o json` entrega `MESSAGE` como lista de enteros cuando el mensaje no es
    UTF-8 válido. Un `str(list)` metería corchetes y comas en la línea que ven
    los patrones, y el Xid se perdería."""
    crudos = list(XID_43.encode("utf-8")) + [0xC3]  # byte suelto inválido al final
    _con_journal(monkeypatch, [_entrada("", us=TS_BASE) | {"MESSAGE": crudos}])

    eventos, _ = agt.vigilar_journal({"cursor": "semilla", "anclas": {}})

    assert [e["xid"] for e in eventos] == [43]


def test_las_alertas_viajan_al_mismo_jsonl_que_las_muestras(thermal, gpu_ok,
                                                            monkeypatch):
    """No se crea un log nuevo: éste ya es el log de eventos de hardware."""
    _con_journal(monkeypatch, [_entrada(XID_43, us=TS_BASE)])
    estado = {"en_alarma": set(), "inicio": {}, "cursor": "semilla", "anclas": {}}

    agt.muestrear(agt.leer_umbrales(), estado, escribir=True)

    filas = _leer_jsonl()
    assert [f["evento"] for f in filas] == ["muestra", "hardware_alerta"]
    assert filas[1]["tipo"] == "xid"
    assert "journal_ausente" not in filas[0]


# ---------------------------------------------------------------------------
# DGX-342: la alarma ahora mitiga, no sólo loguea
# ---------------------------------------------------------------------------

class _SenalFalsa:
    """Doble de `os.kill`: registra cada llamada en vez de mandar la señal de
    verdad -- un test de este mecanismo no puede pausar procesos reales.

    Clase y no una función con atributo pegado encima: pyright no tipa
    `.llamadas` sobre un `FunctionType` (reportFunctionMemberAccess), y una
    clase con `__call__` es la misma forma que `os.kill(pid, sig)` espera,
    correctamente tipada."""

    def __init__(self) -> None:
        self.llamadas: list[tuple[int, int]] = []

    def __call__(self, pid: int, sig: int) -> None:
        self.llamadas.append((pid, sig))


def _senal_falsa() -> _SenalFalsa:
    return _SenalFalsa()


def test_mitigar_pausa_los_pids_mitigables_al_entrar_en_alarma():
    """Control positivo: un `temp_critica` con procesos vivos manda SIGSTOP a
    cada uno y deja constancia del pids mitigados en el estado."""
    senal = _senal_falsa()
    estado = {"en_alarma": {"thermal_zone0"}, "mitigados": set()}
    eventos = [{"evento": "temp_critica", "zona": "thermal_zone0",
                "carga_gpu": "con_carga", "carga_gpu_pico_w": 90.16}]

    resultado = agt.mitigar(eventos, estado, listar_pids=lambda: [222, 111],
                            enviar_senal=senal)

    # Orden determinista (sorted) para que el jsonl sea legible, no un
    # accidente de en qué orden `pgrep` devolvió los pids.
    assert senal.llamadas == [(111, agt.signal.SIGSTOP), (222, agt.signal.SIGSTOP)]
    assert estado["mitigados"] == {111, 222}
    assert len(resultado) == 1
    assert resultado[0]["evento"] == "mitigacion_pausa"
    assert resultado[0]["pids"] == [111, 222]


def test_mitigar_control_negativo_sin_alarma_no_manda_senal():
    """Si `_alarmas` no devolvió ningún `temp_critica`, `mitigar` no puede
    tener nada que hacer -- sin este control, la prueba de arriba no probaría
    que la señal depende del evento."""
    senal = _senal_falsa()
    estado = {"en_alarma": set(), "mitigados": set()}
    eventos = [{"evento": "muestra"}]

    resultado = agt.mitigar(eventos, estado, listar_pids=lambda: [111],
                            enviar_senal=senal)

    assert senal.llamadas == []
    assert resultado == []


def test_mitigar_no_repite_la_pausa_mientras_la_alarma_sigue_activa():
    """Debounce: dos muestras seguidas en alarma no mandan SIGSTOP dos veces
    a los mismos pids -- eso ensuciaría el jsonl con un evento por muestra en
    vez de uno por transición, y mandar SIGSTOP a un proceso ya parado no es
    gratis (dos entradas de historial en vez de una)."""
    senal = _senal_falsa()
    estado = {"en_alarma": {"thermal_zone0"}, "mitigados": set()}
    eventos = [{"evento": "temp_critica", "zona": "thermal_zone0",
                "carga_gpu": "con_carga", "carga_gpu_pico_w": 90.16}]

    agt.mitigar(eventos, estado, listar_pids=lambda: [111], enviar_senal=senal)
    resultado_2 = agt.mitigar(eventos, estado, listar_pids=lambda: [111],
                              enviar_senal=senal)

    assert senal.llamadas == [(111, agt.signal.SIGSTOP)]  # una sola vez
    assert resultado_2 == []


def test_mitigar_reanuda_solo_cuando_todas_las_zonas_normalizaron():
    """Control positivo del camino de vuelta: sin ningún `temp_critica` en
    esta muestra y con `en_alarma` ya vacío (todas las zonas bajaron), manda
    SIGCONT a lo que había pausado y limpia el estado."""
    senal = _senal_falsa()
    estado = {"en_alarma": set(), "mitigados": {111, 222}}

    resultado = agt.mitigar([{"evento": "muestra"}], estado, enviar_senal=senal)

    assert senal.llamadas == [(111, agt.signal.SIGCONT), (222, agt.signal.SIGCONT)]
    assert estado["mitigados"] == set()
    assert resultado[0]["evento"] == "mitigacion_reanuda"
    assert resultado[0]["pids"] == [111, 222]


def test_mitigar_control_negativo_no_reanuda_si_otra_zona_sigue_en_alarma():
    """Dos zonas en alarma, sólo una normalizó: `en_alarma` sigue con
    contenido, así que NO se reanuda -- reanudar aquí dejaría la carga
    pesada corriendo mientras otra zona todavía está sobre el umbral."""
    senal = _senal_falsa()
    estado = {"en_alarma": {"thermal_zone4"}, "mitigados": {111}}

    resultado = agt.mitigar([{"evento": "muestra"}], estado, enviar_senal=senal)

    assert senal.llamadas == []
    assert estado["mitigados"] == {111}
    assert resultado == []


def test_mitigar_pid_que_ya_murio_no_revienta_la_mitigacion():
    """Un proceso que murió entre `pgrep` y el `kill` (o entre pausarlo y
    reanudarlo) no puede tumbar el sampler -- se salta y sigue con el resto."""
    def enviar_con_uno_muerto(pid: int, sig: int) -> None:
        if pid == 222:
            raise ProcessLookupError()

    estado = {"en_alarma": {"thermal_zone0"}, "mitigados": set()}
    resultado = agt.mitigar(
        [{"evento": "temp_critica", "zona": "thermal_zone0",
          "carga_gpu": "con_carga", "carga_gpu_pico_w": 90.16}], estado,
        listar_pids=lambda: [111, 222], enviar_senal=enviar_con_uno_muerto)

    assert estado["mitigados"] == {111}
    assert resultado[0]["pids"] == [111]


def _proc_falso(monkeypatch, tmp_path, argvs: dict[str, list[str]]):
    """Un /proc de mentira: un directorio por PID y su argv por PID.

    Se monkeypatchea `_argv_tokens` con un dict —mismo patrón que
    `_mock_cmdlines` en tests/test_watchdog_gpu_intruder.py— porque la lectura
    real es la pieza importada de `tools/nightly_kb_consolidation.py` y su
    contrato ya está fijado allá: lista vacía si el proceso murió. Un PID
    listado pero AUSENTE del dict es exactamente ese caso.
    """
    for pid in argvs:
        (tmp_path / pid).mkdir()
    (tmp_path / "no-es-un-pid").mkdir()  # /proc real tiene de estos
    monkeypatch.setattr(agt, "PROC_DIR", tmp_path)
    monkeypatch.setattr(agt, "_argv_tokens", lambda pid: argvs.get(pid, []))


def test_pids_mitigables_junta_y_deduplica_los_tres_patrones(monkeypatch, tmp_path):
    """Control positivo: los procesos legítimos SÍ se eligen, una vez cada uno
    aunque dos patrones distintos vivan en el mismo árbol."""
    _proc_falso(monkeypatch, tmp_path, {
        "111": ["/usr/bin/python3", "/home/l/Atlas/tools/remine_harvest_lens.py",
                "--lote", "9"],
        "333": [".venv/bin/python3", "tools/build_incremental.py", "--full"],
        "555": ["/usr/bin/python3", "/home/l/Atlas/tools/ingest.py",
                "https://example.com/x"],
        "777": ["/usr/bin/python3", "tools/kb_ask.py", "¿qué es el GB10?"],
    })

    assert agt.pids_mitigables() == [111, 333, 555]


def test_control_negativo_el_patron_como_substring_no_es_un_blanco(monkeypatch,
                                                                   tmp_path):
    """EL CONTROL NEGATIVO DEL ENCARGO (DGX-408). Estas cuatro cmdlines
    CONTIENEN un patrón como substring y ninguna es el proceso pesado: un
    dictamen abierto en un pager, un editor sobre un respaldo, un `grep` que
    nombra el archivo, un script homónimo de otro directorio, un respaldo y una
    copia. Los dos filtros están cubiertos por separado a propósito: el `grep`
    —cuyo token ES exactamente el patrón— sólo lo descarta la forma de
    invocación, y los dos últimos —invocados por python de verdad, con el
    patrón como substring de la ruta— sólo los descarta la igualdad de
    segmento. Sin ambos casos el control negativo pasaría con la mitad del
    criterio roto (medido: el mutante que vuelve al substring sobrevivía).

    `pgrep -f` matchea contra la cmdline aplanada y habría devuelto los cuatro
    -- o sea cuatro SIGSTOP sobre procesos reales, incluida la sesión desde la
    que se está mirando el problema.
    """
    _proc_falso(monkeypatch, tmp_path, {
        "111": ["less", "docs/agent_findings/2026-09-01_remine_harvest_lens.py.md"],
        "222": ["vim", "tools/build_incremental.py.bak"],
        "333": ["grep", "-rn", "tools/ingest.py", "docs/"],
        "444": ["/usr/bin/python3", "otro_repo/ingest.py"],
        # Los dos que SOLO mata la igualdad de segmento: los invoca python de
        # verdad, así que el filtro de forma de invocación los deja pasar, y su
        # ruta contiene el patrón como substring.
        "555": ["/usr/bin/python3", "tools/build_incremental.py.bak"],
        "666": ["/usr/bin/python3", "/home/l/copia_de_remine_harvest_lens.py"],
    })

    assert agt.pids_mitigables() == []


def test_las_formas_reales_de_invocacion_si_se_eligen(monkeypatch, tmp_path):
    """Las tres formas con que estos jobs arrancan de verdad en esta máquina:
    por shebang, con banderas del intérprete, y envueltas en el cgroup de
    memoria que la cola les pone. El filtro de «esto es el script invocado» no
    puede costar ninguna de ellas."""
    _proc_falso(monkeypatch, tmp_path, {
        "111": ["./tools/ingest.py", "https://example.com/x"],
        "222": ["/home/l/Atlas/.venv/bin/python3", "-u",
                "tools/build_incremental.py", "--full"],
        "333": ["systemd-run", "--user", "--scope", "-p", "MemoryMax=8G",
                ".venv/bin/python3", "tools/remine_harvest_lens.py"],
    })

    assert agt.pids_mitigables() == [111, 222, 333]


def test_control_negativo_un_bash_c_con_el_patron_dentro_no_es_un_blanco(
        monkeypatch, tmp_path):
    """Un `bash -c '<script>'` mete el script entero en UN argv. Ese blob nunca
    es una invocación real -- misma regla que `matches_heavy_job`."""
    _proc_falso(monkeypatch, tmp_path, {
        "111": ["bash", "-c", "cd /home/l/Atlas && echo tools/ingest.py > /tmp/x"],
    })

    assert agt.pids_mitigables() == []


def test_la_telemetria_nunca_se_elige_a_si_misma(monkeypatch, tmp_path):
    """El self-match es el bug original: el patrón viaja en la cmdline del que
    pregunta. Aquí el propio PID declara un argv que SÍ satisface un patrón y
    aun así queda fuera; el vecino con el mismo argv sí entra, que es lo que
    prueba que la exclusión es por PID y no por el matcheo."""
    yo, padre = str(os.getpid()), str(os.getppid())
    argv_pesado = ["/usr/bin/python3", "tools/build_incremental.py", "--full"]
    _proc_falso(monkeypatch, tmp_path, {
        yo: argv_pesado, padre: argv_pesado, "999999999": argv_pesado,
    })

    assert agt.pids_mitigables() == [999999999]


def test_pid_que_muere_entre_el_listado_y_la_lectura_no_revienta(monkeypatch,
                                                                 tmp_path):
    """`_argv_tokens` devuelve [] cuando el proceso ya no está. El listado no
    puede tumbar al sampler por eso -- y el vecino vivo se sigue eligiendo."""
    _proc_falso(monkeypatch, tmp_path, {
        "111": [],  # murió entre iterdir() y la lectura de cmdline
        "222": ["/usr/bin/python3", "tools/build_incremental.py"],
    })

    assert agt.pids_mitigables() == [222]


def test_vllm_y_nemotron_siguen_fuera_de_alcance(monkeypatch, tmp_path):
    """La garantía que el docstring declara y que este cambio NO altera: no hay
    filtro anti-vLLM, hay una lista corta que no lo nombra. Se prueba con los
    argv reales del gateway y de un servidor de Nemotron."""
    _proc_falso(monkeypatch, tmp_path, {
        "111": ["/usr/bin/python3", "-m", "vllm.entrypoints.openai.api_server",
                "--model", "nvidia/NVIDIA-Nemotron-Nano-9B-v2"],
        "222": ["ollama", "serve"],
    })

    assert agt.pids_mitigables() == []


def test_argv_es_mitigable_devuelve_que_patron_satisfizo():
    """La función pura, interrogada sin procesos vivos -- es la mitad del
    criterio que se puede probar sola (mismo motivo que `matches_heavy_job`)."""
    assert agt.argv_es_mitigable(["python", "tools/ingest.py"]) == "tools/ingest.py"
    assert agt.argv_es_mitigable(
        ["python", "/home/l/Atlas/tools/remine_harvest_lens.py"]
    ) == "remine_harvest_lens.py"
    assert agt.argv_es_mitigable([]) is None
    assert agt.argv_es_mitigable(["python", "remine_harvest_lens.py"],
                                 patrones=("build_incremental.py",)) is None


def test_muestrear_pausa_y_reanuda_de_punta_a_punta(thermal, gpu_cargado,
                                                    monkeypatch):
    """Integración: `muestrear` conecta `_alarmas` con `mitigar` de verdad,
    sin pasar por ningún proceso real. `muestrear` no expone `enviar_senal` --
    esto es exactamente el llamador sin override, así que parchear a nivel de
    módulo ANTES de la primera muestra en alarma es lo que prueba que la
    resolución en tiempo de llamada (no un default ligado al definir) sí
    funciona para el camino real.

    DGX-408: además prueba que el NOMBRE del campo que `mitigar` lee es el
    mismo que `_alarmas` escribe. Un test que sólo arme el evento a mano
    seguiría verde si mañana el campo se renombra en un lado y no en el otro
    -- y el síntoma sería la compuerta apagada en silencio, que es justo lo
    que esta ficha vino a impedir.

    Las dos muestras de calentamiento no son decoración: `_corroboracion`
    exige `DEBOUNCE_MUESTRAS - 1 = 2` muestras previas frescas para
    pronunciarse sobre la carga, y sin ellas el flanco saldría `sin_datos`."""
    senal = _senal_falsa()
    monkeypatch.setattr(agt, "pids_mitigables", lambda: [111])
    monkeypatch.setattr(agt.os, "kill", senal)
    umbrales = agt.leer_umbrales()
    estado = _estado()
    estado["mitigados"] = set()

    agt.muestrear(umbrales, estado, escribir=True)  # dos muestras previas, el
    agt.muestrear(umbrales, estado, escribir=True)  # historial que exige el debounce

    _fijar_temp(thermal, 0, 96.0)  # cruza el umbral -> dispara la mitigación
    eventos = agt.muestrear(umbrales, estado, escribir=True)
    critica = [e for e in eventos if e["evento"] == "temp_critica"]
    assert critica[0]["carga_gpu"] == "con_carga"  # 87.05 W >= CARGA_MINIMA_W
    pausa = [e for e in eventos if e["evento"] == "mitigacion_pausa"]
    assert len(pausa) == 1
    assert pausa[0]["pids"] == [111]
    assert senal.llamadas == [(111, agt.signal.SIGSTOP)]

    _fijar_temp(thermal, 0, 97.0)  # sigue arriba, no dispara temp_critica otra vez
    eventos = agt.muestrear(umbrales, estado, escribir=True)
    assert eventos == [eventos[0]]  # sólo la muestra, nada nuevo que mitigar

    _fijar_temp(thermal, 0, 76.5)  # baja y cruza la histéresis
    eventos = agt.muestrear(umbrales, estado, escribir=True)
    reanuda = [e for e in eventos if e["evento"] == "mitigacion_reanuda"]
    assert len(reanuda) == 1
    assert reanuda[0]["pids"] == [111]
    assert senal.llamadas == [(111, agt.signal.SIGSTOP), (111, agt.signal.SIGCONT)]


# ---------------------------------------------------------------------------
# DGX-335: scrape de métricas vLLM desde /metrics
# ---------------------------------------------------------------------------

TEXTO_VLLM_METRICS = """# HELP vllm:num_requests_running Number of requests in model execution batches.
# TYPE vllm:num_requests_running gauge
vllm:num_requests_running{engine="0",model_name="nemotron-local"} 2.0
# HELP vllm:num_requests_waiting Number of requests waiting to be processed.
# TYPE vllm:num_requests_waiting gauge
vllm:num_requests_waiting{engine="0",model_name="nemotron-local"} 1.0
# HELP vllm:num_requests_waiting_by_reason Number of waiting requests by reason.
# TYPE vllm:num_requests_waiting_by_reason gauge
vllm:num_requests_waiting_by_reason{engine="0",model_name="nemotron-local",reason="capacity"} 1.0
vllm:num_requests_waiting_by_reason{engine="0",model_name="nemotron-local",reason="deferred"} 0.0
# HELP vllm:kv_cache_usage_perc KV-cache usage. 1 means 100 percent usage.
# TYPE vllm:kv_cache_usage_perc gauge
vllm:kv_cache_usage_perc{engine="0",model_name="nemotron-local"} 0.45
# HELP vllm:num_preemptions_total Cumulative number of preemption from the engine.
# TYPE vllm:num_preemptions_total counter
vllm:num_preemptions_total{engine="0",model_name="nemotron-local"} 3.0
"""


class _RespFalsa:
    def __init__(self, texto: str, status: int = 200) -> None:
        self.texto = texto
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None

    def read(self) -> bytes:
        return self.texto.encode("utf-8")


def test_leer_vllm_metrics_exito_parsea_campos_y_reasons(monkeypatch):
    def _mock_urlopen(req, timeout=1.0):
        return _RespFalsa(TEXTO_VLLM_METRICS)

    monkeypatch.setattr(agt.urllib.request, "urlopen", _mock_urlopen)

    metrics = agt.leer_vllm_metrics()

    assert metrics["vllm_num_requests_running"] == 2.0
    assert metrics["vllm_num_requests_waiting"] == 1.0
    assert metrics["vllm_num_requests_waiting_by_reason"] == {"capacity": 1.0, "deferred": 0.0}
    assert metrics["vllm_kv_cache_usage_perc"] == 0.45
    assert metrics["vllm_num_preemptions_total"] == 3.0
    assert "vllm_ausente" not in metrics


def test_leer_vllm_metrics_no_alcanzable_declara_ausencia(monkeypatch):
    def _mock_urlopen_error(req, timeout=1.0):
        raise OSError("Connection refused")

    monkeypatch.setattr(agt.urllib.request, "urlopen", _mock_urlopen_error)

    metrics = agt.leer_vllm_metrics()

    assert metrics["vllm_num_requests_running"] is None
    assert metrics["vllm_num_requests_waiting"] is None
    assert metrics["vllm_kv_cache_usage_perc"] is None
    assert metrics["vllm_num_preemptions_total"] is None
    assert "vllm /metrics no alcanzable" in metrics["vllm_ausente"]


def test_muestrear_incluye_metricas_vllm_en_la_muestra(thermal, gpu_ok, monkeypatch):
    called = []
    def _mock_urlopen(req, timeout=1.0):
        called.append(req.full_url)
        return _RespFalsa(TEXTO_VLLM_METRICS)

    monkeypatch.setattr(agt.urllib.request, "urlopen", _mock_urlopen)

    umbrales = agt.leer_umbrales()
    eventos = agt.muestrear(umbrales, _estado(), escribir=True)

    assert len(called) == 1
    assert "http://127.0.0.1:8000/metrics" in called[0]
    muestra = eventos[0]
    assert muestra["vllm_num_requests_running"] == 2.0
    assert muestra["vllm_num_requests_waiting"] == 1.0
    assert muestra["vllm_kv_cache_usage_perc"] == 0.45
    assert muestra["vllm_num_preemptions_total"] == 3.0



# --- consolidación de gpu_sampler.sh (2026-09-07) --------------------------
#
# Al retirar `/srv/ai/gpu_governance/gpu_sampler.sh` este sampler absorbió sus
# campos. Estos tests fijan que no se pierdan: sin ellos la consolidación
# reduce lo que se registra en vez de unificarlo, y eso no se notaría hasta el
# siguiente crash, que es cuando ya no hay remedio.


def test_absorbe_clocks_pstate_y_throttle_de_gpu_sampler(thermal, gpu_ok):
    """`sm_clk`, `pstate` y `throttle` vienen en la MISMA invocación de
    nvidia-smi que temperatura y potencia: tres columnas más, coste cero."""
    muestra = agt.muestrear(agt.leer_umbrales(), _estado(), escribir=False)[0]
    assert muestra["sm_clk_mhz"] == 2502.0
    assert muestra["pstate"] == "P0"
    assert muestra["throttle"] == "0x0000000000000000"
    assert "gpu_ausente" not in muestra


def test_pstate_vacio_no_declara_ausencia_de_los_numericos(thermal, monkeypatch):
    """Un `pstate` vacío es categórico ausente, no un número roto: no debe
    arrastrar a `gpu_ausente` a los campos numéricos que sí se leyeron."""
    monkeypatch.setattr(agt, "_correr", lambda *args: "77, 93, 41.45, 2502, , \n")
    muestra = agt.muestrear(agt.leer_umbrales(), _estado(), escribir=False)[0]
    assert muestra["pstate"] is None
    assert muestra["gpu_temp_c"] == 77.0
    assert "gpu_ausente" not in muestra


def test_memoria_del_sistema_registra_free_y_available(thermal, gpu_ok):
    """MemFree además de MemAvailable: en el cuelgue del 2026-09-07 el segundo
    decía 28 GB mientras el primero estaba en 4.6 GB."""
    muestra = agt.muestrear(agt.leer_umbrales(), _estado(), escribir=False)[0]
    assert isinstance(muestra["mem_free_mb"], (int, float))
    assert isinstance(muestra["mem_avail_mb"], (int, float))
    assert "mem_ausente" not in muestra


def test_meminfo_ilegible_se_declara_no_se_finge(thermal, gpu_ok, monkeypatch):
    class _RutaRota:
        def read_text(self, **_):
            raise OSError("permiso denegado")

    monkeypatch.setattr(agt, "Path", lambda *_: _RutaRota())
    muestra = agt.muestrear(agt.leer_umbrales(), _estado(), escribir=False)[0]
    assert muestra["mem_free_mb"] is None
    assert "ilegible" in muestra["mem_ausente"]


def test_procesos_gpu_suman_la_memoria_unificada(thermal, monkeypatch):
    """La única vía fiable de memoria de GPU en el GB10: `--query-gpu` da
    `[N/A]`, `--query-compute-apps` sí reporta por proceso."""
    def _falso(*args):
        if "--query-compute-apps=pid,process_name,used_memory" in args:
            return "53873, VLLM::EngineCore, 33813\n1218571, /ruta/larga/python, 10251\n"
        return SALIDA_NVIDIA_SMI

    monkeypatch.setattr(agt, "_correr", _falso)
    muestra = agt.muestrear(agt.leer_umbrales(), _estado(), escribir=False)[0]
    assert muestra["gpu_mem_total_mib"] == 44064
    assert [p["nombre"] for p in muestra["gpu_procs"]] == ["VLLM::EngineCore", "python"]


def test_procesos_gpu_no_se_piden_en_cada_muestra(thermal, gpu_ok):
    """Son una invocación extra de nvidia-smi: 1 de cada 3 muestras mantiene
    la cadencia de 15 s que tenía gpu_sampler.sh."""
    estado = _estado()
    presentes = ["gpu_procs" in agt.muestrear(agt.leer_umbrales(), estado, escribir=False)[0]
                 for _ in range(agt.PROCESOS_GPU_CADA * 2)]
    assert presentes[0] is True
    assert presentes[1] is False
    assert presentes[agt.PROCESOS_GPU_CADA] is True
    assert sum(presentes) == 2


# =====================================================================
# rotacion EN CALIENTE -- el anillo sin esperar a que el proceso reinicie
# =====================================================================


def test_rotacion_en_caliente_recorta_cuando_el_fichero_pasa_del_techo(
        tmp_path, monkeypatch):
    """`rotar_si_hace_falta()` se llama una sola vez, en `main()`. Este servicio
    corre en bucle cada 5 s y solo se reinicia con la maquina, asi que entre que
    el fichero pasa del corte y el siguiente arranque no hay cota ninguna.

    Medido el 2026-09-25: 138.3 MB y 150,040 lineas creciendo 15.9 MB al dia.
    """
    f = tmp_path / "telemetria.jsonl"
    f.write_text("".join(f'{{"n": {i}}}\n' for i in range(60)), encoding="utf-8")
    monkeypatch.setattr(agt, "JSONL_PATH", f)
    monkeypatch.setattr(agt, "MAX_BYTES", 100)      # el fichero lo pasa
    monkeypatch.setattr(agt, "MAX_LINEAS", 40)
    monkeypatch.setattr(agt, "LINEAS_A_CONSERVAR", 10)
    assert agt.rotar_en_caliente() == 50
    assert len(f.read_text(encoding="utf-8").splitlines()) == 10


def test_control_negativo_por_debajo_del_techo_NO_toca_el_fichero(
        tmp_path, monkeypatch):
    """Si recortara igual, la 'rotacion en caliente' seria una perdida de datos
    periodica con otro nombre."""
    f = tmp_path / "telemetria.jsonl"
    original = "".join(f'{{"n": {i}}}\n' for i in range(60))
    f.write_text(original, encoding="utf-8")
    monkeypatch.setattr(agt, "JSONL_PATH", f)
    monkeypatch.setattr(agt, "MAX_BYTES", 10 * 1024 * 1024)
    monkeypatch.setattr(agt, "MAX_LINEAS", 40)
    assert agt.rotar_en_caliente() is None
    assert f.read_text(encoding="utf-8") == original


def test_control_negativo_mira_los_BYTES_y_no_las_lineas(tmp_path, monkeypatch):
    """La diferencia entera del guardia: contar lineas exige LEER el fichero, y
    leer 138 MB cada hora para descubrir que no hay nada que hacer seria
    cambiar un problema por otro. Aqui el fichero pasa de MAX_LINEAS pero NO de
    MAX_BYTES, y no se toca -- prueba que la puerta es el tamano."""
    f = tmp_path / "telemetria.jsonl"
    original = "".join(f'{{"n": {i}}}\n' for i in range(60))
    f.write_text(original, encoding="utf-8")
    monkeypatch.setattr(agt, "JSONL_PATH", f)
    monkeypatch.setattr(agt, "MAX_BYTES", 10 * 1024 * 1024)
    monkeypatch.setattr(agt, "MAX_LINEAS", 5)   # lo pasa de sobra
    assert agt.rotar_en_caliente() is None
    assert f.read_text(encoding="utf-8") == original


def test_control_negativo_sin_fichero_no_revienta(tmp_path, monkeypatch):
    """Corre dentro del bucle del sampler: una excepcion aqui mata la
    telemetria entera para ahorrar un recorte."""
    monkeypatch.setattr(agt, "JSONL_PATH", tmp_path / "no-existe.jsonl")
    assert agt.rotar_en_caliente() is None


def test_el_techo_en_bytes_esta_por_ENCIMA_del_techo_en_lineas(tmp_path):
    """El guardia de bytes no debe adelantarse al de lineas: tiene que actuar
    cuando el de lineas ya deberia haber actuado y no pudo, que es el hueco que
    cierra. A la densidad medida (966 bytes/linea) las MAX_LINEAS del anillo
    ocupan ~184 MB, y el techo esta en 192 MB.
    """
    bytes_por_linea_medidos = 966
    assert agt.MAX_BYTES > agt.MAX_LINEAS * bytes_por_linea_medidos
