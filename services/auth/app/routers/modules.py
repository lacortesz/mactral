"""Endpoints stub por módulo, usados para ejercer el guard de autorización
de E1-H2 (escenario 3: acceso a módulo no autorizado). El contenido real
de cada módulo pertenece a otras épicas; aquí solo se expone lo mínimo
para que la restricción de acceso sea real y verificable.
"""
from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, require_module_access
from app.domain import Modulo

router = APIRouter(tags=["modules"])

_MODULE_LABELS = {
    Modulo.COMERCIAL: "Comercial",
    Modulo.REG_MAESTRO: "Reg. maestro",
    Modulo.IMPORTACIONES: "Importaciones",
    Modulo.TECNICO: "Técnico",
    Modulo.STOCK: "Stock",
    Modulo.FINANCIERO: "Financiero",
}


def _make_stub_route(module: Modulo):
    async def _handler(current_user: CurrentUser = Depends(require_module_access(module))):
        return {
            "module": module.value,
            "label": _MODULE_LABELS[module],
            "message": f"Módulo {_MODULE_LABELS[module]} (contenido pendiente de otras épicas)",
        }

    return _handler


for _module in _MODULE_LABELS:
    router.add_api_route(
        f"/modules/{_module.value}",
        _make_stub_route(_module),
        methods=["GET"],
    )
