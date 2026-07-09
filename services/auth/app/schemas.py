import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.domain import EstadoUsuario, LineaNegocio, Rol

PASSWORD_RULES = re.compile(r"^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$")
PASSWORD_POLICY_MESSAGE = (
    "La contraseña debe tener mínimo 8 caracteres, una mayúscula, "
    "un número y un carácter especial"
)


def _validate_password_policy(value: str) -> str:
    if not PASSWORD_RULES.match(value):
        raise ValueError(PASSWORD_POLICY_MESSAGE)
    return value


class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    role: Rol
    linea_negocio: LineaNegocio

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("El nombre es obligatorio")
        return stripped

    @field_validator("email")
    @classmethod
    def email_lowercase(cls, value: str) -> str:
        return value.lower()


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: Rol
    linea_negocio: LineaNegocio
    status: EstadoUsuario
    last_access_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserCreateOut(UserOut):
    activation_link: str


class StatusUpdate(BaseModel):
    status: EstadoUsuario


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def email_lowercase(cls, value: str) -> str:
        return value.lower()


class LoginOut(BaseModel):
    access_token: str
    user: UserOut


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def email_lowercase(cls, value: str) -> str:
        return value.lower()


class SetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    password: str

    @field_validator("password")
    @classmethod
    def password_policy(cls, value: str) -> str:
        return _validate_password_policy(value)
