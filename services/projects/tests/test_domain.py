import pytest

from app.domain import Modulo, Rol, editable_modules


def test_gerencia_puede_editar_todos_los_modulos():
    assert editable_modules(Rol.GERENCIA) == {
        Modulo.COMERCIAL,
        Modulo.REG_MAESTRO,
        Modulo.IMPORTACIONES,
        Modulo.TECNICO,
    }


def test_tecnico_solo_edita_tecnico_y_reg_maestro():
    assert editable_modules(Rol.TECNICO) == {Modulo.TECNICO, Modulo.REG_MAESTRO}


def test_administrativo_solo_edita_reg_maestro():
    assert editable_modules(Rol.ADMINISTRATIVO) == {Modulo.REG_MAESTRO}


@pytest.mark.parametrize(
    "role,modulo",
    [
        (Rol.COMERCIAL, Modulo.COMERCIAL),
        (Rol.IMPORTACIONES, Modulo.IMPORTACIONES),
        (Rol.TECNICO, Modulo.TECNICO),
    ],
)
def test_cada_rol_edita_su_propio_modulo(role, modulo):
    assert modulo in editable_modules(role)
