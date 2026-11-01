"""bb-hallazgo/2: el esquema, el validador (cada regla con su caso negativo), la publicacion idempotente y
el contrato con el consumidor, fijado por un fixture DORADO que vive copiado en los dos repos. Relacion de
informacion: nada aqui importa ni ejecuta codigo de otro repo."""

import hashlib
from pathlib import Path

import pytest

from tools import hallazgo as h

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
        refs=("knowledge/investigations/gb10_cortes_2026-10-11/00_INDICE.md",),
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
        'esquema: "bb-hallazgo/2"', "esquema: bb-hallazgo/2"
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


DORADO = Path(__file__).parent / "fixtures" / "contrato" / "bb_hallazgo_2.md"
SHA_DORADO = "b9a6b21741e7a1abda610c824b0658c5da23f206227f47d0b7446a074b33f46c"


def test_el_dorado_es_el_mismo_que_fija_el_consumidor():
    """El consumidor fija el mismo sha256 en su test y valida este archivo con su propio validador."""
    assert hashlib.sha256(DORADO.read_bytes()).hexdigest() == SHA_DORADO


def test_construye_escribe_el_dorado_byte_a_byte():
    """La forma entera del contrato: claves, orden, comillas, encabezados literales y salto final."""
    texto = h.construye(h.Hallazgo(
        id="bb-2026-11-01-corte-abrupto-0123abcd",
        tipo="corte_abrupto",
        confianza="medido",
        generado="2026-11-01T09:30:00-06:00",
        por="bb reboots",
        nodo="node-00000000",
        datos="reboots.jsonl#0123abcd0123abcd0123abcd0123abcd",
        refs=("investigations/cortes/00_INDICE.md",),
        fuentes="- Veredicto de `reboots.jsonl`: **CORTE_ABRUPTO** para el boot `0123abcd`.",
        inferencia="- [inferencia] La causa queda INDETERMINADA.",
    ))
    assert texto == DORADO.read_text(encoding="utf-8")
    assert h.valida(texto) == []


def test_control_negativo_el_dorado_con_la_clave_vieja_no_valida():
    viejo = DORADO.read_text(encoding="utf-8").replace("\nrefs: [", "\nlista_vieja: [")
    assert any("falta la clave 'refs'" in f for f in h.valida(viejo))
