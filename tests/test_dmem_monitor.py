from typing import Any

from tools import dmem_monitor as m

K = "6.17.0-1032-nvidia"


def est(**kw):
    base: dict[str, Any] = dict(kernel=K, driver_stock="580.178.04", parche_version="580.178.04", parche_vermagic=f"{K} SMP preempt",
                parche_srcversion="AAA", cargado_version="580.178.04", cargado_srcversion="AAA", dmem_con_region=True)
    base.update(kw)
    return m.Estado(**base)


def codigos(e):
    return [x["codigo"] for x in m.evalua(e)]


def test_vigente():
    assert codigos(est()) == ["vigente"]


def test_sin_parche_es_info_no_alarma():
    r = m.evalua(est(parche_version=None, parche_vermagic=None, parche_srcversion=None))
    assert [x["codigo"] for x in r] == ["sin_parche"] and r[0]["gravedad"] == "info"


def test_kernel_nuevo_pide_reconstruir_para_ese_kernel():
    r = m.evalua(est(kernel="6.17.0-1040-nvidia"))
    assert r[0]["codigo"] == "kernel_nuevo" and r[0]["accion"] == "bash tools/dmem_reconstruye.sh 6.17.0-1040-nvidia"


def test_driver_nuevo_pide_la_version():
    r = m.evalua(est(driver_stock="580.190.01"))
    assert r[0]["codigo"] == "driver_nuevo" and r[0]["accion"].endswith("580.190.01") and r[0]["gravedad"] == "alta"


def test_cargado_no_es_el_parche():
    assert codigos(est(cargado_srcversion="BBB")) == ["cargado_no_es_el_parche"]


def test_sin_dato_no_concluye():
    r = m.evalua(est(driver_stock=None))
    assert r[0]["codigo"] == "NOT_COLLECTED"


def test_lee_estado_real_no_revienta():
    e = m.lee_estado()
    assert e.kernel and (e.driver_stock is None or e.driver_stock[0].isdigit())
