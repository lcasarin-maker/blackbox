"""Captura independiente del mapa al declarar COLAPSO; todo filesystem es sintetico."""
import importlib.machinery
import importlib.util
import json
import threading
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[1] / "bin" / "bb-usable"


def modulo(ruta=RUTA):
    loader = importlib.machinery.SourceFileLoader("bb_usable_mapa_colapso", str(ruta))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class Mapa:
    def unidades_de(self, ruta):
        return [ruta / "worker.scope"]

    def lee_clases(self):
        return ()

    def captura(self, rutas, clases):
        self.ultima_entrada = rutas
        rutas = list(rutas)
        if not rutas:
            return {"estado": "NOT_COLLECTED", "motivo": "sin unidades"}
        return {"esquema": "mapa_memoria/1", "unidades": [str(r) for r in rutas]}


def preparar(monkeypatch, tmp_path, ruta=RUTA):
    bbu = modulo(ruta)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path / "datos"))
    monkeypatch.setenv("TMPDIR", str(tmp_path / "tmp"))
    cg = tmp_path / "cgroup" / "user.slice/user-77.slice/user@77.service/app.slice"
    proc = tmp_path / "proc"
    cg.mkdir(parents=True)
    proc.mkdir()
    monkeypatch.setattr(bbu, "CGROUP_ROOT", tmp_path / "cgroup")
    monkeypatch.setattr(bbu, "PROC_ROOT", proc)
    monkeypatch.setattr(bbu, "_MAPA", Mapa())
    monkeypatch.setattr(bbu, "origen_al_declarar_colapso", lambda _s: None)
    monkeypatch.setattr(bbu, "paso_confinado", lambda n: ("retiene", n))
    bbu._mapa_declarado_en_racha = False
    bbu._hilo_mapa.clear()
    bbu._mapas_pendientes.clear()
    return bbu, cg


def test_captura_solo_en_primera_declaracion_y_episodio_siguiente(monkeypatch, tmp_path):
    bbu, cg = preparar(monkeypatch, tmp_path)
    bbu.mapa_al_declarar_colapso(bbu.PSI_ACT_SONDAS - 1)
    assert not (tmp_path / "datos/escalon").exists()
    bbu.mapa_al_declarar_colapso(bbu.PSI_ACT_SONDAS)
    bbu.mapa_al_declarar_colapso(bbu.PSI_ACT_SONDAS + 1)
    _, sostenido, bajas, confinadas = bbu.reaccion_psi_baja(0.5, bbu.PSI_ACT_SONDAS, 0, 0)
    _, sostenido, bajas, confinadas = bbu.reaccion_psi_baja(0.5, sostenido, bajas, confinadas)
    assert sostenido == bajas == 0
    bbu.mapa_al_declarar_colapso(bbu.PSI_ACT_SONDAS)
    archivo = next((tmp_path / "datos/escalon").glob("*.jsonl"))
    filas = [json.loads(x) for x in archivo.read_text().splitlines()]
    assert len(filas) == 2
    assert filas[0]["mapa_memoria"]["unidades"] == [str(cg / "worker.scope")]


def test_fallo_de_mapa_visible_y_no_cambia_cola_de_watchdog(monkeypatch, tmp_path):
    bbu, _ = preparar(monkeypatch, tmp_path)

    def rota(*_args):
        raise OSError("cgroup sintético ilegible")

    monkeypatch.setattr(bbu._MAPA, "unidades_de", rota)
    logs = []
    monkeypatch.setattr(bbu, "log", logs.append)
    caricia, _ = bbu.reaccion_colapso(50, 0.001, bbu.PSI_ACT_SONDAS, 0)
    assert caricia is False
    archivo = next((tmp_path / "datos/escalon").glob("*.jsonl"))
    fila = json.loads(archivo.read_text().splitlines()[0])
    assert fila["mapa_memoria"]["estado"] == "NOT_COLLECTED"
    assert any("NOT_COLLECTED" in linea for linea in logs)


def test_confinado_que_acaricia_no_declara_colapso(monkeypatch, tmp_path):
    bbu, _ = preparar(monkeypatch, tmp_path)
    monkeypatch.setattr(bbu, "paso_confinado", lambda n: ("acaricia", n + 1))
    assert bbu.reaccion_colapso(50, 0.001, bbu.PSI_ACT_SONDAS, 0) == (True, 1)
    assert not (tmp_path / "datos/escalon").exists()


def test_unidades_ilegibles_llegan_como_none_a_captura(monkeypatch, tmp_path):
    bbu, _ = preparar(monkeypatch, tmp_path)
    monkeypatch.setattr(bbu._MAPA, "unidades_de", lambda _ruta: None)
    bbu.mapa_al_declarar_colapso(bbu.PSI_ACT_SONDAS)
    archivo = next((tmp_path / "datos/escalon").glob("*.jsonl"))
    fila = json.loads(archivo.read_text().splitlines()[0])
    assert bbu._MAPA.ultima_entrada is None
    assert fila["mapa_memoria"]["estado"] == "NOT_COLLECTED"


def test_rama_ilegible_entre_dos_apps_no_se_confunde_con_ausente(monkeypatch, tmp_path):
    bbu, cg = preparar(monkeypatch, tmp_path)
    segunda = tmp_path / "cgroup/user.slice/user-88.slice/user@88.service/app.slice"
    segunda.mkdir(parents=True)
    original = bbu._subdirectorios

    def ilegible_en_segunda(ruta, patron="*"):
        if ruta.name == "user-88.slice":
            raise PermissionError("permiso sintético denegado")
        return original(ruta, patron)

    monkeypatch.setattr(bbu, "_subdirectorios", ilegible_en_segunda)
    assert len(original(cg.parents[2])) == 2  # dos ramas sintéticas; una falla en el límite de enumeración
    bbu.mapa_al_declarar_colapso(bbu.PSI_ACT_SONDAS)
    archivo = next((tmp_path / "datos/escalon").glob("*.jsonl"))
    fila = json.loads(archivo.read_text().splitlines()[0])
    assert bbu._MAPA.ultima_entrada is None
    assert fila["mapa_memoria"]["estado"] == "NOT_COLLECTED"


def test_mutante_semantico_sin_llamada_falla_asercion_de_efecto(monkeypatch, tmp_path):
    fuente = RUTA.read_text(encoding="utf-8")
    llamada = "    mapa_al_declarar_colapso(sostenido)\n"
    assert fuente.count(llamada) == 1
    mutante = tmp_path / "bb-usable-mutante"
    mutante.write_text(fuente.replace(llamada, "    pass  # mutante: no publica mapa al declarar\n"), encoding="utf-8")
    bbu, _ = preparar(monkeypatch, tmp_path / "mutante", mutante)
    assert hasattr(bbu, "mapa_al_declarar_colapso")  # el helper sigue presente
    bbu.reaccion_colapso(50, 0.001, bbu.PSI_ACT_SONDAS, 0)
    assert not (tmp_path / "mutante/datos/escalon").exists()
    with pytest.raises(AssertionError, match="COLAPSO debe publicar su mapa"):
        assert list((tmp_path / "mutante/datos/escalon").glob("*.jsonl")), "COLAPSO debe publicar su mapa"


def test_append_que_escribe_y_luego_falla_no_se_reintenta(monkeypatch, tmp_path):
    bbu, _ = preparar(monkeypatch, tmp_path)
    append = bbu._anexar
    llamadas = []

    def escribir_y_fallar(ruta, fila):
        llamadas.append(fila)
        append(ruta, fila)
        raise OSError("fallo posterior a write")

    monkeypatch.setattr(bbu, "_anexar", escribir_y_fallar)
    bbu.mapa_al_declarar_colapso(bbu.PSI_ACT_SONDAS)
    assert len(llamadas) == 1
    archivo = next((tmp_path / "datos/escalon").glob("*.jsonl"))
    assert len(archivo.read_text().splitlines()) == 1


def test_captura_bloqueada_no_detiene_lazo_y_publica_not_collected_original(monkeypatch, tmp_path):
    bbu, _ = preparar(monkeypatch, tmp_path)
    entrando, liberar = threading.Event(), threading.Event()

    def bloquear(_rutas, _clases):
        entrando.set()
        liberar.wait(5)
        return {"esquema": "mapa_memoria/1"}

    monkeypatch.setattr(bbu._MAPA, "captura", bloquear)
    logs = []
    monkeypatch.setattr(bbu, "log", logs.append)
    bbu.mapa_al_declarar_colapso(bbu.PSI_ACT_SONDAS)
    assert entrando.is_set()
    assert any("captura vencida; recibo NOT_COLLECTED pendiente de confirmar" in linea for linea in logs)
    liberar.set()
    bbu._hilo_mapa[-1].join(1)
    archivo = next((tmp_path / "datos/escalon").glob("*.jsonl"))
    fila = json.loads(archivo.read_text().splitlines()[0])
    assert fila["mapa_memoria"]["estado"] == "NOT_COLLECTED"
    assert fila["mapa_memoria"]["motivo"] == "captura no disponible dentro del plazo"


def test_racha_rearmada_con_worker_vivo_persiste_not_collected_con_ts_original(monkeypatch, tmp_path):
    bbu, _ = preparar(monkeypatch, tmp_path)
    entrando, liberar = threading.Event(), threading.Event()

    def bloquear(_rutas, _clases):
        entrando.set()
        liberar.wait(5)
        return {"esquema": "mapa_memoria/1"}

    monkeypatch.setattr(bbu._MAPA, "captura", bloquear)
    logs = []
    monkeypatch.setattr(bbu, "log", logs.append)
    bbu.mapa_al_declarar_colapso(bbu.PSI_ACT_SONDAS)
    assert entrando.is_set()
    _, sostenido, bajas, confinadas = bbu.reaccion_psi_baja(0.5, bbu.PSI_ACT_SONDAS, 0, 0)
    _, sostenido, bajas, confinadas = bbu.reaccion_psi_baja(0.5, sostenido, bajas, confinadas)
    assert sostenido == bajas == 0
    bbu.mapa_al_declarar_colapso(bbu.PSI_ACT_SONDAS)
    assert any("recibo diferido" in linea for linea in logs)
    liberar.set()
    bbu._hilo_mapa[-1].join(1)
    archivo = next((tmp_path / "datos/escalon").glob("*.jsonl"))
    filas = [json.loads(linea) for linea in archivo.read_text().splitlines()]
    assert len(filas) == 2
    assert all(f["mapa_memoria"]["estado"] == "NOT_COLLECTED" for f in filas)
    assert all(f["mapa_memoria"]["motivo"] != "captura pendiente" for f in filas)


def test_cola_acotada_avisa_y_no_apila_workers(monkeypatch, tmp_path):
    bbu, _ = preparar(monkeypatch, tmp_path)
    entrando, liberar = threading.Event(), threading.Event()
    append = bbu._anexar

    def append_bloqueado(ruta, fila):
        entrando.set()
        liberar.wait(5)
        append(ruta, fila)

    monkeypatch.setattr(bbu, "_anexar", append_bloqueado)
    logs = []
    monkeypatch.setattr(bbu, "log", logs.append)
    bbu.mapa_al_declarar_colapso(bbu.PSI_ACT_SONDAS)
    assert entrando.is_set()
    for _ in range(bbu.MAPA_MAX_PENDIENTES + 1):
        _, sostenido, bajas, confinadas = bbu.reaccion_psi_baja(0.5, bbu.PSI_ACT_SONDAS, 0, 0)
        _, sostenido, bajas, confinadas = bbu.reaccion_psi_baja(0.5, sostenido, bajas, confinadas)
        assert sostenido == bajas == 0
        bbu.mapa_al_declarar_colapso(bbu.PSI_ACT_SONDAS)
    assert len(bbu._hilo_mapa) == 1
    assert len(bbu._mapas_pendientes) == bbu.MAPA_MAX_PENDIENTES
    assert any("cola llena" in linea and "no persistido" in linea for linea in logs)
    liberar.set()
    bbu._hilo_mapa[-1].join(1)
    archivo = next((tmp_path / "datos/escalon").glob("*.jsonl"))
    assert len(archivo.read_text().splitlines()) == 1 + bbu.MAPA_MAX_PENDIENTES


def test_escritura_bloqueada_informa_en_curso_y_retorna_al_lazo(monkeypatch, tmp_path):
    bbu, _ = preparar(monkeypatch, tmp_path)
    append, entrando, liberar = bbu._anexar, threading.Event(), threading.Event()

    def append_bloqueado(ruta, fila):
        entrando.set()
        liberar.wait(5)
        append(ruta, fila)

    monkeypatch.setattr(bbu, "_anexar", append_bloqueado)
    logs = []
    monkeypatch.setattr(bbu, "log", logs.append)
    bbu.mapa_al_declarar_colapso(bbu.PSI_ACT_SONDAS)
    assert entrando.is_set()
    assert any("publicación en curso o sin confirmar" in linea for linea in logs)
    liberar.set()
    bbu._hilo_mapa[-1].join(1)
    archivo = next((tmp_path / "datos/escalon").glob("*.jsonl"))
    assert len(archivo.read_text().splitlines()) == 1


def test_transicion_confinado_a_colapso_real_mas_tarde(monkeypatch, tmp_path):
    bbu, _ = preparar(monkeypatch, tmp_path)
    monkeypatch.setattr(bbu, "paso_confinado", lambda n: ("acaricia", n + 1))
    monkeypatch.setattr(bbu, "origen_al_declarar_colapso", lambda _s: None)
    assert bbu.reaccion_colapso(50, 0.001, bbu.PSI_ACT_SONDAS, 0)[0] is True
    monkeypatch.setattr(bbu, "paso_confinado", lambda n: ("retiene", n))
    assert bbu.reaccion_colapso(50, 0.001, bbu.PSI_ACT_SONDAS + 1, 1)[0] is False
    assert list((tmp_path / "datos/escalon").glob("*.jsonl"))
