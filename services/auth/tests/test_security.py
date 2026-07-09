import jwt
import pytest

from app.config import settings
from app.domain import Rol
from app.security import (
    create_session_token,
    decode_session_token,
    generate_token,
    hash_password,
    verify_password,
)


def test_hash_password_permite_verificar_la_contrasena_original():
    hashed = hash_password("Mactral2026!")
    assert hashed != "Mactral2026!"
    assert verify_password("Mactral2026!", hashed) is True


def test_verify_password_rechaza_contrasena_incorrecta():
    hashed = hash_password("Mactral2026!")
    assert verify_password("incorrecta", hashed) is False


def test_generate_token_produce_valores_unicos():
    assert generate_token() != generate_token()


def test_sesion_se_firma_y_verifica_correctamente():
    token = create_session_token("u1", "Maya Lozada", "maya@grupomactral.com", Rol.GERENCIA)
    payload = decode_session_token(token)

    assert payload is not None
    assert payload["sub"] == "u1"
    assert payload["role"] == "GERENCIA"


def test_decode_session_token_devuelve_none_si_es_invalido():
    assert decode_session_token("token-invalido") is None


def test_decode_session_token_devuelve_none_si_expiro():
    expired_payload = {
        "sub": "u1",
        "name": "Maya Lozada",
        "email": "maya@grupomactral.com",
        "role": "GERENCIA",
        "iat": 0,
        "exp": 1,
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret, algorithm="HS256")

    assert decode_session_token(expired_token) is None
