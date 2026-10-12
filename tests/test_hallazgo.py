"""bb-hallazgo/1: el esquema, el validador (cada regla con su caso negativo), la publicacion idempotente,
el contrato de Atlas y `bb saber`. Relacion de informacion: nada aqui importa codigo de Atlas."""

import json
import subprocess
from pathlib import Path

import pytest

from tools import hallazgo as h
from tools import saber

pytestmark = pytest.mark.unit

FILA = {
    "boot_id": "54b7161869da4fc99f7becb9571f529d",
    "etiqueta": "CORTE_ABRUPTO",
    "hueco_s": 4231,
    "razones": ["el journal calla sin cierre, sin colapso de memoria y sin panic"],
    "bert_guid": None,
    "bert_palabra_0x14": None,
    "could_not_run": ["observador_externo"],
}


def hallazgo_valido(**kw):
    base = h.Hallazgo(
        id="bb-2026-10-11-corte-abrupto-54b71618",
        tipo="corte_abrupto",
        confianza="medido",
        generado="2026-10-11T12:13:23-06:00",
        por="bb reboots",
        nodo="node-9d835fe3",
        datos="reboots.jsonl#54b7161869da4fc99f7becb9571f529d",
        atlas_refs=("knowledge/investigations/gb10_cortes_2026-10-11/00_INDICE.md",),
        fuentes="- Veredicto de `reboots.jsonl`: CORTE_ABRUPTO.",
        inferencia="- [inferencia] causa indeterminada.",
    )
    return h.construye(h.Hallazgo(**{**base.__dict__, **kw}))


def test_un_hallazgo_bien_formado_no_tiene_faltas():
    assert h.valida(hallazgo_valido()) == []


def test_cada_regla_del_esquema_falla_con_su_caso_negativo():
    ok = hallazgo_valido()
    casos = {
        "falta la clave 'nodo'": ok.replace('nodo: "node-9d835fe3"\n', ""),
        "'confianza' sin comillas": ok.replace(
            'confianza: "medido"', "confianza: medido"
        ),
        "tipo fuera de": hallazgo_valido(tipo="otra_cosa"),
        "confianza fuera de": hallazgo_valido(confianza="seguro"),
        "id no cumple": hallazgo_valido(id="mi-hallazgo"),
        f"falta la seccion literal '{h.H_FUENTES}'": ok.replace(
            h.H_FUENTES, "## Fuentes"
        ),
        f"falta la seccion literal '{h.H_INFERENCIA}'": ok.replace(
            h.H_INFERENCIA, "## Inferencia"
        ),
        "no cita ningun archivo": hallazgo_valido(fuentes="- sin cita alguna."),
        "sin frontmatter": "# solo texto\n",
    }
    for esperado, texto in casos.items():
        faltas = h.valida(texto)
        assert any(esperado in f for f in faltas), (esperado, faltas)


def test_un_valor_sin_comillas_se_reporta_y_no_lanza():
    texto = hallazgo_valido().replace(
        'esquema: "bb-hallazgo/1"', "esquema: bb-hallazgo/1"
    )
    assert any(
        "'esquema' sin comillas" in f for f in h.valida(texto)
    )  # antes habria lanzado JSONDecodeError


def test_publica_es_idempotente_y_no_reescribe_un_id_con_otro_contenido(tmp_path):
    t = hallazgo_valido()
    ruta, estado = h.publica(t, tmp_path)
    assert estado == "publicado" and ruta.read_text(encoding="utf-8") == t
    assert h.publica(t, tmp_path)[1] == "ya_publicado"
    with pytest.raises(FileExistsError):
        h.publica(hallazgo_valido(inferencia="- otra inferencia distinta."), tmp_path)
    with pytest.raises(ValueError):
        h.publica(
            "# invalido\n", tmp_path
        )  # control: un invalido no llega a la bandeja
    assert list(tmp_path.iterdir()) == [ruta]


def test_desde_veredicto_marca_la_inferencia_y_distingue_corte_de_cierre():
    corte = h.desde_veredicto(
        FILA,
        nodo="node-1",
        generado="2026-10-11T12:13:23-06:00",
        datos="reboots.jsonl#x",
    )
    assert (
        h.valida(corte) == []
        and "[inferencia]" in corte
        and 'tipo: "corte_abrupto"' in corte
    )
    cierre = h.desde_veredicto(
        {**FILA, "etiqueta": "CIERRE_ORDENADO_REBOOT"},
        nodo="node-1",
        generado="2026-10-11T12:13:23-06:00",
        datos="reboots.jsonl#x",
    )
    assert (
        h.valida(cierre) == []
        and 'tipo: "reinicio"' in cierre
        and "[inferencia]" not in cierre
    )


def test_el_nodo_anonimo_no_filtra_el_machine_id_y_declara_su_ausencia():
    n = h.nodo_anonimo(lambda _: "abcdef0123456789")
    assert n.startswith("node-") and "abcdef" not in n
    assert h.nodo_anonimo(lambda _: "UNSUPPORTED") == "COLLECTION_FAILED"


ATLAS = Path.home() / "projects/Atlas"


@pytest.mark.skipif(
    not (ATLAS / "tools/kb_investigator.py").exists(),
    reason="Atlas no esta en esta maquina",
)
def test_hallazgo_cumple_el_contrato_de_atlas():
    """Se ejecuta como PROCESO aparte dentro de Atlas: no hay import cruzado y los dos `tools` no se mezclan."""
    texto = h.desde_veredicto(
        FILA,
        nodo="node-1",
        generado="2026-10-11T12:13:23-06:00",
        datos="reboots.jsonl#x",
    )
    codigo = (
        "import sys, json, datetime; sys.path.insert(0, '.')\n"
        "from tools.kb_investigator import _contract_violations as cv, REQUIRED_SOURCES_HEADING as S, REQUIRED_INFERENCE_HEADING as I\n"
        "import rag.indexer as ix\n"
        "t = sys.stdin.read(); fm, _ = ix.split_frontmatter(t)\n"
        "print(json.dumps({'faltas': cv(t), 'S': S, 'I': I, 'sin_citar': [k for k, v in fm.items() if isinstance(v, (datetime.date, datetime.datetime))], 'claves': len(fm)}))\n"
    )
    r = subprocess.run(
        ["python3", "-c", codigo],
        input=texto,
        capture_output=True,
        text=True,
        cwd=ATLAS,
        timeout=90,
    )
    assert r.returncode == 0, r.stderr[-400:]
    d = json.loads(r.stdout.strip().splitlines()[-1])
    assert d["faltas"] == [] and d["sin_citar"] == [] and d["claves"] >= 10
    assert (d["S"], d["I"]) == (
        h.H_FUENTES,
        h.H_INFERENCIA,
    )  # si Atlas cambia sus encabezados, esto lo avisa
    roto = subprocess.run(
        ["python3", "-c", codigo],
        input=texto.replace(h.H_INFERENCIA, "## x"),
        capture_output=True,
        text=True,
        cwd=ATLAS,
        timeout=90,
    )
    assert json.loads(roto.stdout.strip().splitlines()[-1])[
        "faltas"
    ]  # control negativo: el contrato de Atlas SI puede rechazar


# -------------------------------------------------------------------------------- bb saber
def test_saber_encuentra_con_archivo_y_linea_y_salta_las_carpetas_con_guion_bajo(
    tmp_path,
):
    (tmp_path / "a").mkdir()
    (tmp_path / "a/uno.md").write_text(
        "hola\nel codigo MODS-020000600139 aparece\nfin\n",
        encoding="utf-8",
    )
    (tmp_path / "_procedencia").mkdir()
    (tmp_path / "_procedencia/oculto.md").write_text("MODS-020000600139\n", encoding="utf-8")
    r = saber.busca("mods-020000600139", base=tmp_path)
    assert r["estado"] == "ok" and r["total"] == 1 and r["archivos_revisados"] == 1
    assert r["coincidencias"][0] == {
        "archivo": "a/uno.md",
        "linea": 2,
        "texto": "el codigo MODS-020000600139 aparece",
    }


def test_saber_declara_el_cero_con_su_alcance_y_la_ruta_ausente_como_no_se_pudo_correr(
    tmp_path, capsys, monkeypatch
):
    (tmp_path / "x.md").write_text("nada\n", encoding="utf-8")
    monkeypatch.setenv("ATLAS_KNOWLEDGE", str(tmp_path))
    assert (
        saber.main(["inexistente"]) == 1
        and "0 coincidencias en" in capsys.readouterr().err
    )
    monkeypatch.setenv("ATLAS_KNOWLEDGE", str(tmp_path / "no_existe"))
    assert (
        saber.main(["x"]) == 2 and "COULD_NOT_RUN" in capsys.readouterr().err
    )  # ausente != cero
    monkeypatch.setenv("ATLAS_KNOWLEDGE", str(tmp_path))
    assert (
        saber.busca("(", base=tmp_path, regex=True)["estado"] == "COULD_NOT_RUN"
    )  # regex invalida no es "sin resultados"


def test_saber_trunca_y_lo_dice(tmp_path):
    (tmp_path / "m.md").write_text("\n".join(["clave"] * 10), encoding="utf-8")
    r = saber.busca("clave", base=tmp_path, maximo=3)
    assert r["total"] == 10 and r["mostradas"] == 3 and r["truncado"] is True
