"""El autoarmado en GRUB (adopted/opt-in/etc_grub.d_09_bb_zautoarmado): sintaxis y logica, SIN arrancar nada.

- SINTAXIS: el bloque que la plantilla emite (y el mismo bloque detras de la cabecera y de 09_bb_etapa) pasa por el
  `grub-script-check` real; el control negativo es el mismo texto con un `fi` de menos, que tiene que rechazar.
- LOGICA: un interprete minimo del subconjunto de lenguaje GRUB que usan las plantillas (if/elif/else/fi, set,
  save_env, load_env, [ -n | -z | = | != ]) ejecuta EL TEXTO EMITIDO por las plantillas -- no una copia del
  algoritmo -- sobre un grubenv modelado como dict, arranque tras arranque. Una instruccion que el interprete no
  conoce es un error: una plantilla que cambie de forma rompe la prueba en vez de pasar en silencio.
- La tabla de verdad del contador se imprime (pytest -s) y se compara con la esperada; cada mutante de la plantilla
  (umbral, reinicio del contador, entrada elegida) cambia la tabla y la prueba lo detecta.

Lo que NO se prueba aqui ni en ningun sitio todavia: GRUB de verdad en un arranque de la ATOM (could_not_run;
procedimiento para Luis en docs/PANIC.md).
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
AUTOARMADO = REPO / "adopted/opt-in/etc_grub.d_09_bb_zautoarmado"
MARCA = REPO / "adopted/opt-in/etc_grub.d_09_bb_etapa"
PUNTO = "gnulinux-advanced-U>gnulinux-6.17.0-1032-nvidia-advanced-U"
SAVED = "gnulinux-advanced-U>gnulinux-7.0.0-1024-nvidia-advanced-U"
# Lo que 00_header de GRUB 2.12-1ubuntu7.3 emite con GRUB_DEFAULT=saved, reducido a lo que el autoarmado lee
# (/etc/grub.d/00_header: `if [ -s $prefix/grubenv ]` ... `set default="${saved_entry}"`).
CABECERA = """if [ -n "${hay_grubenv}" ]; then
  set have_grubenv=true
  load_env
fi
set default="${saved_entry}"
"""


def emite(plantilla: Path, texto: str | None = None) -> str:
    """Lo que grub-mkconfig pondria en grub.cfg: la plantilla corrida con GRUB_FS=ext2."""
    if texto is not None:
        return subprocess.run(["sh", "-c", texto], env={"PATH": "/usr/bin:/bin", "GRUB_FS": "ext2"},
                              capture_output=True, text=True, check=True).stdout
    return subprocess.run(["sh", str(plantilla)], env={"PATH": "/usr/bin:/bin", "GRUB_FS": "ext2"},
                          capture_output=True, text=True, check=True).stdout


# --- interprete del subconjunto de GRUB ---------------------------------------------------------------------------


class Grub:
    def __init__(self, grubenv: dict[str, str] | None, guardar_falla: bool = False) -> None:
        self.grubenv = grubenv  # None = no hay grubenv
        self.vars: dict[str, str] = {"hay_grubenv": "1" if grubenv is not None else ""}
        self.guardar_falla = guardar_falla

    def expande(self, s: str) -> str:
        for k in sorted({*self.vars, "default", "saved_entry", "bb_intentos", "bb_punto_entry", "have_grubenv",
                         "recordfail", "boot_once"}, key=len, reverse=True):
            s = s.replace("${" + k + "}", self.vars.get(k, ""))
        if "${" in s:
            raise AssertionError(f"variable sin modelo: {s}")
        return s

    def cond(self, texto: str) -> bool:
        t = shlex.split(self.expande(texto))
        assert t[0] == "[" and t[-1] == "]", texto
        t = t[1:-1]
        if len(t) == 2 and t[0] in ("-n", "-z"):
            return bool(t[1]) == (t[0] == "-n")
        if len(t) == 3 and t[1] in ("=", "!="):
            return (t[0] == t[2]) == (t[1] == "=")
        raise AssertionError(f"condicion sin modelo: {texto}")

    def corre(self, guion: str) -> None:
        pila: list[dict[str, bool]] = []
        activo = lambda: all(f["activo"] for f in pila)  # noqa: E731
        for crudo in guion.splitlines():
            ln = crudo.strip()
            if not ln or ln.startswith("#"):
                continue
            if ln.startswith("if ") and ln.endswith("; then"):
                padre = activo()
                c = padre and self.cond(ln[3:-6])
                pila.append({"padre": padre, "tomado": c, "activo": c})
            elif ln.startswith("elif ") and ln.endswith("; then"):
                f = pila[-1]
                c = f["padre"] and not f["tomado"] and self.cond(ln[5:-6])
                f["activo"], f["tomado"] = c, f["tomado"] or c
            elif ln == "else":
                f = pila[-1]
                f["activo"], f["tomado"] = f["padre"] and not f["tomado"], True
            elif ln == "fi":
                pila.pop()
            elif not activo():
                continue
            elif ln.startswith("set "):
                k, v = ln[4:].split("=", 1)
                self.vars[k] = shlex.split(self.expande(v))[0] if v else ""
            elif ln.startswith("save_env "):
                if self.grubenv is not None and not self.guardar_falla:
                    for k in ln.split()[1:]:
                        self.grubenv[k] = self.vars.get(k, "")
            elif ln == "load_env":
                self.vars.update(self.grubenv or {})
            else:
                raise AssertionError(f"instruccion sin modelo: {ln}")
        assert not pila, "if sin fi"


def arranca(env: dict[str, str] | None, autoarmado: str, guardar_falla: bool = False) -> str:
    """Un arranque: cabecera, grub-marca y autoarmado sobre el grubenv. Devuelve la entrada que arranca."""
    g = Grub(env, guardar_falla)
    g.corre(CABECERA)
    g.corre(emite(MARCA))
    g.corre(autoarmado)
    return g.vars["default"]


def arranque_ok(env: dict[str, str]) -> None:
    """Lo que hace bb-arranque-ok tras 180 s de un arranque sano (tools/punto_restauracion.arranque_ok)."""
    env["bb_intentos"] = "0"
    env.pop("bb_autoarmado", None)


def secuencia(autoarmado: str, arranques: str, env: dict[str, str] | None = None) -> list[tuple[str, str, str]]:
    """`arranques`: una letra por arranque, c = corto (muere antes de 180 s), l = largo (arranque-ok corre)."""
    env = {"saved_entry": SAVED, "bb_punto_entry": PUNTO} if env is None else env
    filas = []
    for tipo in arranques:
        leido = env.get("bb_intentos", "(no existe)")
        entrada = arranca(env, autoarmado)
        if tipo == "l":
            arranque_ok(env)
        filas.append((leido, "PUNTO" if entrada == PUNTO else "saved" if entrada == SAVED else entrada,
                      env.get("bb_intentos", "(no existe)") + (" autoarmado=1" if env.get("bb_autoarmado") else "")))
    return filas


ESPERADA_CORTOS = [  # (bb_intentos que lee GRUB, entrada que arranca, bb_intentos al acabar el arranque)
    ("(no existe)", "saved", "1"),
    ("1", "saved", "2"),
    ("2", "saved", "3"),
    ("3", "PUNTO", "0 autoarmado=1"),
    ("0", "saved", "1 autoarmado=1"),  # el punto tambien murio pronto: la marca sigue hasta que arranque-ok la lea
]


def test_tabla_de_verdad_de_arranques_cortos_seguidos(capsys):
    filas = secuencia(emite(AUTOARMADO), "ccccc")
    with capsys.disabled():
        print("\n[tabla] arranques cortos seguidos (n, bb_intentos leido, entrada, bb_intentos al acabar):")
        for n, f in enumerate(filas, 1):
            print(f"  {n}  {f[0]:<12} {f[1]:<6} {f[2]}")
    assert filas == ESPERADA_CORTOS


def test_un_arranque_largo_devuelve_el_contador_a_cero(capsys):
    filas = secuencia(emite(AUTOARMADO), "ccl" + "ccc" + "c")
    with capsys.disabled():
        print("\n[tabla] corto, corto, LARGO, corto x4:")
        for n, f in enumerate(filas, 1):
            print(f"  {n}  {f[0]:<12} {f[1]:<6} {f[2]}")
    assert [f[1] for f in filas] == ["saved", "saved", "saved", "saved", "saved", "saved", "PUNTO"]
    assert filas[2] == ("2", "saved", "0")  # el largo: GRUB lo subio a 3 y arranque-ok lo bajo a 0


def test_sin_punto_el_contador_se_queda_en_3_y_no_cambia_el_arranque():
    filas = secuencia(emite(AUTOARMADO), "cccccc", env={"saved_entry": SAVED})
    assert [f[1] for f in filas] == ["saved"] * 6
    assert [f[2] for f in filas] == ["1", "2", "3", "3", "3", "3"]


def test_sin_grubenv_no_hace_nada():
    assert arranca(None, emite(AUTOARMADO)) == ""  # el default que dejo la cabecera, sin tocar


def test_un_contador_con_basura_cae_al_punto():
    env = {"saved_entry": SAVED, "bb_punto_entry": PUNTO, "bb_intentos": "x"}
    assert arranca(env, emite(AUTOARMADO)) == PUNTO and env["bb_intentos"] == "0"


def test_default_vacio_usa_el_punto():
    env = {"bb_punto_entry": PUNTO, "bb_intentos": "0"}  # GRUB_DEFAULT=saved sin saved_entry
    assert arranca(env, emite(AUTOARMADO)) == PUNTO


def test_si_save_env_falla_arranca_lo_de_siempre_y_no_hay_bucle():
    env = {"saved_entry": SAVED, "bb_punto_entry": PUNTO, "bb_intentos": "0"}
    for _ in range(5):
        assert arranca(env, emite(AUTOARMADO), guardar_falla=True) == SAVED
    assert env["bb_intentos"] == "0"


def test_la_marca_sigue_viendo_el_default_de_antes_del_autoarmado():
    """grub-marca corre antes: bb_prev_default = lo que GRUB habria arrancado sin el autoarmado."""
    env = {"saved_entry": SAVED, "bb_punto_entry": PUNTO, "bb_intentos": "3"}
    assert arranca(env, emite(AUTOARMADO)) == PUNTO
    assert env["bb_prev_default"] == SAVED and env["bb_autoarmado"] == "1"


# --- controles negativos: cada mutante de la plantilla cambia la tabla -----------------------------------------


@pytest.mark.parametrize("viejo, nuevo", [
    ('elif [ "${bb_intentos}" = 2 ]; then\n    set bb_intentos=3', 'elif [ "${bb_intentos}" = 2 ]; then\n    set bb_intentos=2'),
    ("    set bb_intentos=0\n    set bb_autoarmado=1", "    set bb_intentos=3\n    set bb_autoarmado=1"),
    ('    set default="${bb_punto_entry}"\n    set bb_intentos=0', '    set default="${saved_entry}"\n    set bb_intentos=0'),
    ("  save_env bb_intentos\n", "\n"),
])
def test_mutante_de_la_plantilla_cambia_la_tabla(viejo, nuevo):
    texto = AUTOARMADO.read_text(encoding="utf-8")
    assert texto.count(viejo) == 1, "la mutacion tiene que caer en un sitio real"
    assert secuencia(emite(AUTOARMADO, texto.replace(viejo, nuevo)), "ccccc") != ESPERADA_CORTOS


def test_control_la_plantilla_sin_mutar_da_la_tabla():
    texto = AUTOARMADO.read_text(encoding="utf-8")
    assert secuencia(emite(AUTOARMADO, texto), "ccccc") == ESPERADA_CORTOS


def test_el_interprete_rechaza_lo_que_no_conoce():
    with pytest.raises(AssertionError, match="sin modelo"):
        Grub({}).corre("if [ -n x ]; then\n  regexp foo bar\nfi\n")


# --- sintaxis: grub-script-check real -------------------------------------------------------------------------


GSC = shutil.which("grub-script-check")


@pytest.mark.skipif(GSC is None, reason="could_not_run: no hay grub-script-check en esta maquina")
def test_grub_script_check_acepta_lo_emitido_y_rechaza_un_mutante(tmp_path, capsys):
    assert GSC is not None
    bloque = emite(AUTOARMADO)
    junto = CABECERA.replace("hay_grubenv", "prefix") + emite(MARCA) + bloque
    roto = bloque.replace("  fi\nfi\n### END", "  fi\n### END")
    assert roto != bloque
    res = {}
    for nombre, texto in (("autoarmado.cfg", bloque), ("cabecera+marca+autoarmado.cfg", junto), ("mutante.cfg", roto)):
        f = tmp_path / nombre
        f.write_text(texto, encoding="utf-8")
        p = subprocess.run([GSC, "-v", str(f)], capture_output=True, text=True, check=False)
        res[nombre] = p.returncode
        with capsys.disabled():
            print(f"\n[grub-script-check -v {nombre}] rc={p.returncode} lineas_leidas={len(p.stdout.splitlines())} "
                  f"stderr={p.stderr.strip()!r}")
    assert res == {"autoarmado.cfg": 0, "cabecera+marca+autoarmado.cfg": 0, "mutante.cfg": 1}


def test_fuera_de_ext2_no_emite_nada():
    sin = subprocess.run(["sh", str(AUTOARMADO)], env={"PATH": "/usr/bin:/bin", "GRUB_FS": "btrfs"},
                         capture_output=True, text=True, check=True).stdout
    assert "save_env" not in sin and "btrfs" in sin
