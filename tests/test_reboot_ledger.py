"""Control del contrato append-only de `reboots.jsonl`."""

from __future__ import annotations

import json

from tools import reboot_ledger


def _fila(boot_id: str, **extra):
    return {"boot_id": boot_id, **extra}


def test_rectificacion_valida_anula_y_la_reposicion_mas_reciente_gana(tmp_path):
    ruta = tmp_path / "reboots.jsonl"
    ruta.write_text(
        "\n".join(
            [
                json.dumps(_fila("x1", etiqueta="CORTE_ABRUPTO")),
                json.dumps(_fila("x2", etiqueta="CIERRE_ORDENADO")),
                json.dumps(_fila("x1", anula=True, corrige_linea=2)),
                json.dumps(_fila("x1", etiqueta="CIERRE_ORDENADO_REBOOT")),
                json.dumps(_fila("x1", anula=True, corrige_linea=4)),
                json.dumps(_fila("x1", etiqueta="PANIC_KERNEL")),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    avisos: list[str] = []
    filas = reboot_ledger.leer_filas([ruta], avisos)
    assert filas == {"x1": _fila("x1", etiqueta="PANIC_KERNEL"), "x2": _fila("x2", etiqueta="CIERRE_ORDENADO")}
    assert avisos == ["reboots.jsonl:3 ilegible (anulacion con corrige_linea sin referencia vigente del mismo boot)"]


def test_rechaza_relacion_invalida_y_preserva_bytes_originales(tmp_path):
    ruta = tmp_path / "reboots.jsonl"
    ruta.write_bytes(
        b'{"boot_id":"x1","boot_id_siguiente":"good"}\n'
        b'{"boot_id":"x2","boot_id_siguiente":"other"}\n'
        b'{"boot_id":"x1","anula":true,"corrige_linea":2}\n'
        b'{"boot_id":"x1","anula":true,"corrige_linea":99}\n'
        b'{"boot_id":"x1","anula":true,"corrige_linea":1}\n'
        b'{"boot_id":"x1","boot_id_siguiente":"wrong"}\n'
        b'{"boot_id":"x1","corrige_linea":6,"boot_id_siguiente":"bad"}\n'
    )
    antes = ruta.read_bytes()
    avisos: list[str] = []
    filas = reboot_ledger.leer_filas([ruta], avisos)
    assert filas["x1"]["boot_id_siguiente"] == "wrong"
    assert len(avisos) == 3
    assert ruta.read_bytes() == antes


def test_tiene_sucesor_ignora_fila_supersedida_y_acepta_reposicion(tmp_path):
    ruta = tmp_path / "reboots.jsonl"
    ruta.write_text(
        '{"boot_id":"x1","boot_id_siguiente":"este"}\n'
        '{"boot_id":"x1","anula":true,"corrige_linea":1}\n'
        '{"boot_id":"x1","boot_id_siguiente":"otro"}\n',
        encoding="utf-8",
    )
    assert not reboot_ledger.tiene_sucesor(ruta, "este")
    ruta.write_text(ruta.read_text(encoding="utf-8") + '{"boot_id":"x1","boot_id_siguiente":"este"}\n', encoding="utf-8")
    assert reboot_ledger.tiene_sucesor(ruta, "este")


def test_rechaza_anula_cero_unicode_invalido_y_sucesor_vacio(tmp_path):
    ruta = tmp_path / "reboots.jsonl"
    ruta.write_text(
        '{"boot_id":"x1","etiqueta":"CORTE_ABRUPTO"}\n'
        '{"boot_id":"x1","anula":0,"corrige_linea":1}\n'
        '{"boot_id":"x1","anula":true,"corrige_linea":2}\n'
        '{"boot_id":"---","etiqueta":"CORTE_ABRUPTO"}\n',
        encoding="utf-8",
    )
    avisos: list[str] = []
    filas = reboot_ledger.leer_filas([ruta], avisos)
    assert filas["x1"]["etiqueta"] == "CORTE_ABRUPTO"
    assert len(avisos) == 3 and "tras normalizar" in avisos[-1]
    assert not reboot_ledger.tiene_sucesor(ruta, "")
    rota = tmp_path / "rota.jsonl"
    rota.write_bytes(b'{"boot_id":"x1"}\n\xff\n')
    avisos = []
    assert reboot_ledger.leer_filas([rota], avisos) == {}
    assert len(avisos) == 1 and "no se pudo leer" in avisos[0]


def test_fila_incompleta_no_eclipsa_la_valida_para_calibracion(tmp_path):
    ruta = tmp_path / "reboots.jsonl"
    ruta.write_text(
        '{"boot_id":"x1","etiqueta":"CORTE_ABRUPTO"}\n'
        '{"boot_id":"x1","boot_id_siguiente":"otro"}\n',
        encoding="utf-8",
    )
    avisos: list[str] = []
    filas = reboot_ledger.leer_filas([ruta], avisos, campos_requeridos=("etiqueta",))
    assert filas["x1"]["etiqueta"] == "CORTE_ABRUPTO"
    assert any("falta etiqueta" in aviso for aviso in avisos)
