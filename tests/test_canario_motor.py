"""canario_motor: tres estados, motor caido = NOT_COLLECTED, una peticion por prueba, sin red, sin hilos, sin sleep."""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest

from tools import canario_motor as c

MODELOS = {"data": [{"id": "nemotron"}]}


def _chat(content: str | None = None, calls: list[Any] | None = None, fin: str = "stop") -> dict[str, Any]:
    return {"choices": [{"message": {"content": content, "tool_calls": calls or []}, "finish_reason": fin}], "usage": {"total_tokens": 10}}


OK_JSON = _chat('{"ok": true}')
OK_TOOL = _chat(None, [{"function": {"name": "suma", "arguments": '{"a": 2, "b": 3}'}}], "tool_calls")


class Resp:
    def __init__(self, obj: Any) -> None:
        self.b = obj if isinstance(obj, bytes) else json.dumps(obj).encode()

    def __enter__(self) -> "Resp":
        return self

    def __exit__(self, *a: Any) -> None:
        return None

    def read(self) -> bytes:
        return self.b


class Falso:
    """`abre` falso: respuestas fijas por URL; cuenta las peticiones."""

    def __init__(self, models: Any = MODELOS, json_: Any = OK_JSON, tool: Any = OK_TOOL) -> None:
        self.models, self.json_, self.tool, self.n = models, json_, tool, []

    def __call__(self, req: Any, timeout: float = 0) -> Resp:
        self.n.append(req.full_url)
        if req.full_url == c.URL_MODELOS:
            r = self.models
        else:
            r = self.tool if "tools" in json.loads(req.data) else self.json_
        if isinstance(r, Exception):
            raise r
        return Resp(r)


def test_todo_ok() -> None:
    f = Falso()
    r = c.ronda(f, "nemotron", reloj=iter([0.0, 1.5]).__next__)
    assert r["estado_general"] == "OK" and r["habria_actuado"] is False
    assert r["latencia_s"] == 1.5 and r["tokens"] == 20 and len(f.n) == 3


def test_nombre_distinto_del_esperado_falla() -> None:
    r = c.ronda(Falso(), "otro")
    assert r["estado_general"] == "FALLA" and r["pruebas"]["modelo"]["estado"] == "FALLA" and r["habria_actuado"] is True


def test_sin_esperado_solo_registra() -> None:
    assert c.evalua(MODELOS, OK_JSON, OK_TOOL)["pruebas"]["modelo"]["servido"] == "nemotron"


def test_json_invalido_falla() -> None:
    assert c.ronda(Falso(json_=_chat("hola")))["pruebas"]["json"]["estado"] == "FALLA"


def test_json_valido_pero_distinto_falla() -> None:
    assert c.ronda(Falso(json_=_chat('{"ok": false}')))["pruebas"]["json"]["estado"] == "FALLA"


def test_json_sin_contenido_falla() -> None:
    assert c.evalua(MODELOS, _chat(None), OK_TOOL)["pruebas"]["json"]["estado"] == "FALLA"


def test_tool_calls_vacio_con_stop_falla_y_el_caso_ok_pasa() -> None:
    assert c.ronda(Falso())["pruebas"]["tool"]["estado"] == "OK"  # control negativo
    p = c.ronda(Falso(tool=_chat("3", [], "stop")))["pruebas"]["tool"]
    assert p["estado"] == "FALLA" and p["n_tool_calls"] == 0


def test_tool_argumentos_invalidos_o_finish_reason_malo_o_no_objeto() -> None:
    mal = _chat(None, [{"function": {"arguments": "{no"}}], "tool_calls")
    assert c.evalua(MODELOS, OK_JSON, mal)["pruebas"]["tool"]["estado"] == "FALLA"
    stop = _chat(None, [{"function": {"arguments": "{}"}}], "stop")
    assert "finish_reason" in c.evalua(MODELOS, OK_JSON, stop)["pruebas"]["tool"]["motivo"]
    lista = _chat(None, [{"function": {"arguments": "[1]"}}], "tool_calls")
    assert c.evalua(MODELOS, OK_JSON, lista)["pruebas"]["tool"]["estado"] == "FALLA"


def test_motor_caido_es_not_collected_y_no_envia_las_otras() -> None:
    f = Falso(models=urllib.error.URLError("caido"))
    r = c.ronda(f)
    assert r["estado_general"] == "NOT_COLLECTED" and r["habria_actuado"] is False
    assert f.n == [c.URL_MODELOS] and r["tokens"] is None


def test_chat_caido_con_models_vivo_no_es_falla() -> None:
    assert c.ronda(Falso(json_=TimeoutError(), tool=TimeoutError()))["estado_general"] == "NOT_COLLECTED"


def test_falla_pesa_mas_que_not_collected() -> None:
    assert c.evalua(MODELOS, _chat("x"), None)["estado_general"] == "FALLA"


def test_models_vacio_o_basura() -> None:
    f = Falso(models={"data": []})
    assert c.ronda(f)["pruebas"]["modelo"]["estado"] == "FALLA" and len(f.n) == 1
    assert c.consulta(c.URL_MODELOS, None, Falso(models=b"[1]")) is None
    assert c.consulta(c.URL_MODELOS, None, Falso(models=b"no json")) is None
    assert c._choice({}) == {}


def test_paso_off_no_consulta_ni_escribe(tmp_path: Path) -> None:
    f = Falso()
    assert c.paso("off", f, directorio=tmp_path / "d") is None
    assert f.n == [] and not (tmp_path / "d").exists()


def test_paso_observar_registra(tmp_path: Path) -> None:
    r = c.paso("observar", Falso(json_=_chat("x")), directorio=tmp_path)
    fila = json.loads((tmp_path / "canario_motor.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert r is not None and fila["modo"] == "observar" and fila["estado_general"] == "FALLA" and fila["habria_actuado"] is True


def test_paso_actuar_unsupported(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError, match="UNSUPPORTED"):
        c.paso("actuar", Falso(), directorio=tmp_path)


def test_main_exit_codes_y_sin_escribir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    for f, rc in ((Falso(), 0), (Falso(json_=_chat("x")), 1), (Falso(models=OSError()), 2)):
        monkeypatch.setattr(c.urllib.request, "urlopen", f)
        assert c.main([]) == rc
    assert json.loads(capsys.readouterr().out.split("\n}\n")[0] + "\n}")["modo"] == "observar"
    assert not (tmp_path / "interruptores").exists()


def test_main_paso(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    monkeypatch.setenv("BLACKBOX_MOTOR_MODELO", "nemotron")
    assert c.main(["--paso"]) == 0  # interruptor off por defecto: no consulta la red
    assert "off" in capsys.readouterr().out
    (tmp_path / "interruptores.json").write_text(json.dumps({"modos": {"canario_motor": "observar"}}), encoding="utf-8")
    monkeypatch.setattr(c.urllib.request, "urlopen", Falso())
    assert c.main(["--paso"]) == 0
    assert (tmp_path / "interruptores" / "canario_motor.jsonl").exists()


def test_consulta_envia_post_json() -> None:
    visto: list[Any] = []

    def abre(req: Any, timeout: float = 0) -> Resp:
        visto.append((req.get_method(), timeout))
        return Resp({"a": 1})

    assert c.consulta("http://x", {"k": 1}, abre, 7) == {"a": 1} and visto == [("POST", 7)]
