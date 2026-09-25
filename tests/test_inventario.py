"""Suite de tools/inventario.py.

El control negativo es el punto entero: un gate que solo se ha visto pasar no
esta verificado. Cada comprobacion del inventario se ejerce en los dos
sentidos -- con el sujeto sano y con el sujeto mutado.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tools import inventario

SPEC_SANA = """\
# SPEC.md - prueba

## Inventario de funciones

| pieza | que hace |
| --- | --- |
| `bb sample` | muestrea |
| `bb scan ["hace X"]` | informa |
| `tools/otra.py` | otra cosa |
| `bin/bb-usable` | vigila |

## Inventario de propiedad

| desplegado en | por que es de bb |
| --- | --- |
| `/etc/sysctl.d/99-x.conf` | porque si |
| `~/.config/systemd/user/u.service` | porque si |
| `/srv/ai/gpu_governance/s.sh` | porque si |

Deliberadamente fuera: `/etc/systemd/system.conf`, que reescribe el paquete.

## Constraints

nada
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Un repo minimo cuyos inventarios describen exactamente su sujeto."""
    (tmp_path / "SPEC.md").write_text(SPEC_SANA, encoding="utf-8")
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "bb").write_text(
        textwrap.dedent("""\
            #!/usr/bin/env bash
            cmd_sample() { :; }
            cmd_scan() { :; }
        """),
        encoding="utf-8",
    )
    (tmp_path / "bin" / "bb-usable").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "otra.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tools" / "__init__.py").write_text("", encoding="utf-8")
    for sub, nombre in [
        ("system-config", "etc_sysctl.d_99-x.conf"),
        ("systemd-user", "u.service"),
        ("gpu_governance", "s.sh"),
    ]:
        d = tmp_path / "adopted" / sub
        d.mkdir(parents=True)
        (d / nombre).write_text("contenido\n", encoding="utf-8")
    return tmp_path


def test_sujeto_sano_no_da_hallazgos(repo: Path) -> None:
    assert inventario.revisa(repo) == []


def test_subcomando_nuevo_sin_inventariar_lo_caza(repo: Path) -> None:
    bb = repo / "bin" / "bb"
    bb.write_text(bb.read_text(encoding="utf-8") + "cmd_nuevo() { :; }\n", encoding="utf-8")
    fallos = inventario.revisa(repo)
    assert fallos == ["funcion sin inventariar en SPEC.md: bb nuevo"], fallos


def test_fichero_nuevo_en_tools_sin_inventariar_lo_caza(repo: Path) -> None:
    (repo / "tools" / "recien.py").write_text("y = 2\n", encoding="utf-8")
    assert "funcion sin inventariar en SPEC.md: tools/recien.py" in inventario.revisa(repo)


def test_adoptado_nuevo_sin_inventariar_lo_caza(repo: Path) -> None:
    (repo / "adopted" / "system-config" / "etc_default_algo").write_text("z\n", encoding="utf-8")
    fallos = inventario.revisa(repo)
    assert fallos == ["sujeto adoptado sin inventariar en SPEC.md: /etc/default/algo"], fallos


def test_fila_fantasma_en_spec_la_caza(repo: Path) -> None:
    """Lo contrario: SPEC declara propiedad sobre algo que no existe en adopted/."""
    (repo / "adopted" / "system-config" / "etc_sysctl.d_99-x.conf").unlink()
    fallos = inventario.revisa(repo)
    assert "SPEC.md inventaria algo que no esta en adopted/: /etc/sysctl.d/99-x.conf" in fallos


def test_la_prosa_no_se_lee_como_fila(repo: Path) -> None:
    """/etc/systemd/system.conf se nombra en la prosa y NO debe exigirse adoptarlo."""
    assert not any("system.conf" in f for f in inventario.revisa(repo))


def test_subcomando_con_argumentos_cuenta_como_inventariado(repo: Path) -> None:
    """`bb scan [\"hace X\"]` en la tabla cubre el cmd_scan del ejecutable."""
    assert not any("bb scan" in f for f in inventario.revisa(repo))


def test_spec_sin_la_seccion_no_pasa_callada(repo: Path) -> None:
    (repo / "SPEC.md").write_text("# SPEC.md\n\n## Constraints\n\nnada\n", encoding="utf-8")
    with pytest.raises(LookupError, match="Inventario de funciones"):
        inventario.revisa(repo)


def test_main_sale_0_con_sujeto_sano(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert inventario.main(["--root", str(repo), "--check"]) == 0
    assert "HALLAZGOS: 0" in capsys.readouterr().out


def test_main_sale_1_con_sujeto_mutado(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bb = repo / "bin" / "bb"
    bb.write_text(bb.read_text(encoding="utf-8") + "cmd_fantasma() { :; }\n", encoding="utf-8")
    assert inventario.main(["--root", str(repo), "--check"]) == 1
    salida = capsys.readouterr().out
    assert "bb fantasma" in salida
    assert "FAIL" in salida


def test_destino_de_cada_familia_de_adoptados() -> None:
    """El mapeo de rutas es el mismo que usa `bb drift`; si diverge, el gate miente."""
    assert inventario.destino_desplegado(Path("adopted/system-config/etc_a_b.conf")) == "/etc/a/b.conf"
    assert inventario.destino_desplegado(Path("adopted/systemd-user/x.service")) == "~/.config/systemd/user/x.service"
    assert inventario.destino_desplegado(Path("adopted/gpu_governance/y.sh")) == "/srv/ai/gpu_governance/y.sh"
