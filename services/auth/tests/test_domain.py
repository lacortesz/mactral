import pytest

from app.domain import Modulo, Rol, accessible_modules, can_access_module, can_manage_users


def test_solo_gerencia_puede_gestionar_usuarios():
    assert can_manage_users(Rol.GERENCIA) is True


@pytest.mark.parametrize(
    "role", [Rol.COMERCIAL, Rol.IMPORTACIONES, Rol.TECNICO, Rol.ADMINISTRATIVO]
)
def test_otros_roles_no_pueden_gestionar_usuarios(role):
    assert can_manage_users(role) is False


def test_gerencia_accede_a_todos_los_modulos():
    for module in Modulo:
        assert can_access_module(Rol.GERENCIA, module) is True


def test_tecnico_no_accede_a_financiero():
    # Escenario 3 de E1-H2: Técnico intenta acceder a Financiero.
    assert can_access_module(Rol.TECNICO, Modulo.FINANCIERO) is False


def test_tecnico_accede_a_tecnico_y_stock():
    assert can_access_module(Rol.TECNICO, Modulo.TECNICO) is True
    assert can_access_module(Rol.TECNICO, Modulo.STOCK) is True


def test_administrativo_accede_a_financiero_stock_logistica_y_reg_maestro():
    # E6-H1/E8-H1: "Bodega"/"Logística" se mapean al rol Administrativo (la
    # plataforma no tiene roles propios para ellos).
    accesibles = set(accessible_modules(Rol.ADMINISTRATIVO))
    assert accesibles == {Modulo.FINANCIERO, Modulo.REG_MAESTRO, Modulo.STOCK, Modulo.LOGISTICA}


def test_comercial_puede_consultar_stock():
    # E6-H1: Comercial consulta disponibilidad (no la edita) para clasificar
    # una venta como Stock — Mobility/Industry.
    accesibles = set(accessible_modules(Rol.COMERCIAL))
    assert Modulo.STOCK in accesibles
