import pytest

from app.domain import LEAD_CODE_PREFIX, LineaNegocio, Rol, can_manage_leads


def test_comercial_puede_gestionar_leads():
    assert can_manage_leads(Rol.COMERCIAL) is True


def test_gerencia_puede_gestionar_leads():
    assert can_manage_leads(Rol.GERENCIA) is True


@pytest.mark.parametrize("role", [Rol.IMPORTACIONES, Rol.TECNICO, Rol.ADMINISTRATIVO])
def test_otros_roles_no_pueden_gestionar_leads(role):
    assert can_manage_leads(role) is False


def test_prefijos_de_codigo_por_linea():
    assert LEAD_CODE_PREFIX[LineaNegocio.MOBILITY] == "MOB"
    assert LEAD_CODE_PREFIX[LineaNegocio.INDUSTRY] == "IND"
