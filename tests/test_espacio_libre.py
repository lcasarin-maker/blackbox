"""Pruebas unitarias y controles negativos de tools/espacio_libre.py."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

from tools import espacio_libre as el


def _fake_statvfs(*, total_gb: float = 100.0, uso_pct: float = 50.0, inodes_total: int = 1000, inodes_used: int = 100):
    frsize = 4096
    f_blocks = int((total_gb * (1024**3)) / frsize)
    usados = int(f_blocks * (uso_pct / 100.0))
    libres = max(0, f_blocks - usados)
    return SimpleNamespace(
        f_frsize=frsize,
        f_blocks=f_blocks,
        f_bfree=libres,
        f_bavail=libres,
        f_files=inodes_total,
        f_ffree=max(0, inodes_total - inodes_used),
    )


def test_medir_volumen_local_y_control_negativo_fallo_statvfs(tmp_path: Path) -> None:
    ok = el.medir_volumen_local(tmp_path, statvfs_fn=lambda _p: _fake_statvfs(total_gb=100.0, uso_pct=87.0))
    assert ok["estado"] == "OK"
    assert ok["uso_pct"] == 87.0
    assert ok["inodos_pct"] == 10.0

    def _boom(_p: Path):
        raise PermissionError("sin permiso")

    cnr = el.medir_volumen_local(tmp_path, statvfs_fn=_boom)
    assert cnr["estado"] == "COULD_NOT_RUN"
    assert cnr["uso_pct"] is None
    assert cnr["libre_bytes"] is None


def test_tendencia_con_pocas_muestras_devuelve_not_collected_y_con_tres_calcula() -> None:
    t0 = 1_800_000_000.0
    # Control negativo: 2 muestras o <30 min nunca inventan un numero
    dos = [
        {"ts": t0, "estado": "OK", "usado_bytes": 50 * 1024**3, "libre_bytes": 50 * 1024**3},
        {"ts": t0 + 3600, "estado": "OK", "usado_bytes": 55 * 1024**3, "libre_bytes": 45 * 1024**3},
    ]
    res_2 = el.calcular_tendencia(dos)
    assert res_2["estado"] == "NOT_COLLECTED"
    assert res_2["dias_hasta_llenarse"] is None

    # 3 muestras separadas >= 30 min con crecimiento constante (+10 GiB/dia)
    tres = [
        {"ts": t0, "estado": "OK", "usado_bytes": 50 * 1024**3, "libre_bytes": 50 * 1024**3},
        {"ts": t0 + 43200, "estado": "OK", "usado_bytes": 55 * 1024**3, "libre_bytes": 45 * 1024**3},
        {"ts": t0 + 86400, "estado": "OK", "usado_bytes": 60 * 1024**3, "libre_bytes": 40 * 1024**3},
    ]
    res_3 = el.calcular_tendencia(tres)
    assert res_3["estado"] == "OK"
    assert res_3["dias_hasta_llenarse"] == 4.0


def test_umbrales_y_disciplina_rafaga_unica_con_histeresis() -> None:
    # Cruce a 86 % -> aviso y debe_avisar=True
    a1 = el.evaluar_nivel_y_aviso(86.0, None, estado_previo=None)
    assert a1["nivel"] == "aviso"
    assert a1["debe_avisar"] is True

    # Siguiente muestra sigue en 86.5 % -> no repite aviso
    a2 = el.evaluar_nivel_y_aviso(86.5, None, estado_previo=a1)
    assert a2["nivel"] == "aviso"
    assert a2["debe_avisar"] is False

    # Baja a 84.5 % (dentro de histeresis 2 %) -> mantiene nivel pero no avisa
    a3 = el.evaluar_nivel_y_aviso(84.5, None, estado_previo=a2)
    assert a3["nivel"] == "aviso"
    assert a3["debe_avisar"] is False

    # Sube a 97 % -> nivel critico y vuelve a avisar una vez
    a4 = el.evaluar_nivel_y_aviso(97.0, None, estado_previo=a3)
    assert a4["nivel"] == "critico"
    assert a4["debe_avisar"] is True

    a5 = el.evaluar_nivel_y_aviso(97.2, None, estado_previo=a4)
    assert a5["debe_avisar"] is False


def test_disco_externo_caido_o_vencido_nunca_parece_sano(tmp_path: Path) -> None:
    ahora = 1_800_000_000.0
    ausente = el.leer_disco_externo(tmp_path / "no_existe.json", ahora_ts=ahora)
    assert ausente["estado"] == "COULD_NOT_RUN"
    assert ausente["volumenes"] == []

    ext_file = tmp_path / "estado_externo.json"
    ext_file.write_text(
        json.dumps(
            {
                "esquema": el.ESQUEMA_EXTERNO,
                "ts": ahora - 600.0,
                "vigente": True,
                "disco": {"ok": True, "volumenes": [{"nombre": "data", "total_bytes": 1000, "usado_bytes": 100, "libre_bytes": 900}]},
            }
        ),
        encoding="utf-8",
    )
    vencido = el.leer_disco_externo(ext_file, ahora_ts=ahora, max_edad_s=180.0)
    assert vencido["estado"] == "COULD_NOT_RUN"
    assert vencido["volumenes"] == []

    ext_file.write_text(
        json.dumps(
            {
                "esquema": el.ESQUEMA_EXTERNO,
                "ts": ahora - 10.0,
                "vigente": True,
                "disco": {"ok": True, "volumenes": [{"nombre": "data", "total_bytes": 1000, "usado_bytes": 250, "libre_bytes": 750}]},
            }
        ),
        encoding="utf-8",
    )
    fresco = el.leer_disco_externo(ext_file, ahora_ts=ahora)
    assert fresco["estado"] == "OK"
    assert fresco["volumenes"][0]["uso_pct"] == 25.0


def test_top_directorios_deduplica_hardlinks_y_mide_st_blocks(tmp_path: Path) -> None:
    sub = tmp_path / "proyecto"
    sub.mkdir()
    orig = sub / "blob.bin"
    orig.write_bytes(b"a" * 65536)
    os.link(orig, sub / "blob_hardlink.bin")

    res = el.top_directorios_primer_nivel([tmp_path])
    esperado = os.stat(orig).st_blocks * 512
    assert res["mapa_bytes"][str(sub)] == esperado


def test_ejecutar_muestra_extremo_a_extremo(tmp_path: Path) -> None:
    data_dir = tmp_path / "bb_data"
    raiz_top = tmp_path / "watch"
    (raiz_top / "carpeta_a").mkdir(parents=True)
    (raiz_top / "carpeta_a" / "f.bin").write_bytes(b"x" * 16384)

    doc = el.ejecutar_muestra(
        raiz=tmp_path,
        data_dir=data_dir,
        estado_externo=tmp_path / "ext_ausente.json",
        raices_top=[raiz_top],
        ahora_ts=1_800_000_000.0,
        statvfs_fn=lambda _p: _fake_statvfs(total_gb=100.0, uso_pct=97.0),
    )
    assert doc["esquema"] == el.ESQUEMA_ESTADO
    assert doc["alerta"]["nivel"] == "critico"
    assert doc["alerta"]["debe_avisar"] is True
    assert (data_dir / "disco" / "estado_disco.json").is_file()
    assert (data_dir / "disco" / "espacio_libre.jsonl").is_file()
