"""data/dmem/memacct-580.patch: el contrato del cobro de memoria de GPU por cgroup en GB10 (FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01).

Estatico: lee el parche, no lo compila ni carga el modulo (eso lo prueba `tools/dmem_prueba_completa.sh` en la maquina).
Cada propiedad tiene su control negativo: el mismo chequeo sobre un parche con la linea quitada debe fallar.
"""

from __future__ import annotations

from pathlib import Path

PARCHE = Path(__file__).resolve().parent.parent / "data" / "dmem" / "memacct-580.patch"

COBRO = "status = memacctTryCharge(pRmClient, pGpu->gpuId, pAllocData->size, &pMemory->pCharge);"
TRADUCE = "if (status == NV_ERR_RESOURCE_ACCOUNTING_HARD_LIMIT_EXCEEDED)\n+            return NV_ERR_NO_MEMORY;"
LIBERA = "memacctReleaseCharge(pMemory->pCharge); /* bb-patch: refcounted, covers dup and copy-construct */"
COPIA = "memacctIncrementChargeRefCount(pMemory->pCharge);"
ENVOLTORIO = "+sysmemConstructInner"


def cumple(texto: str) -> dict[str, bool]:
    return {
        "cobra en sysmemConstruct": COBRO in texto,
        "traduce 0x8D a NO_MEMORY": TRADUCE in texto,
        "libera en sysmemDestruct": LIBERA in texto,
        "copy-construct comparte el cobro": COPIA in texto,
        "envuelve el constructor original": ENVOLTORIO in texto,
        "declara el estado 0x8D": "NV_ERR_RESOURCE_ACCOUNTING_HARD_LIMIT_EXCEEDED,  0x0000008D" in texto,
    }


def test_el_parche_cumple_el_contrato() -> None:
    faltan = [k for k, ok in cumple(PARCHE.read_text(encoding="utf-8")).items() if not ok]
    assert faltan == [], faltan


def test_control_negativo_cada_propiedad_se_pierde_si_se_quita_su_linea() -> None:
    texto = PARCHE.read_text(encoding="utf-8")
    for marca in (COBRO, TRADUCE, LIBERA, COPIA, ENVOLTORIO):
        roto = texto.replace(marca, "")
        assert len([k for k, ok in cumple(roto).items() if not ok]) >= 1, marca
