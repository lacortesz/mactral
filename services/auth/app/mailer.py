"""Stub de envío de correo. No hay proveedor SMTP configurado en este
entorno; el enlace se registra en el log del servicio. Sustituir por una
integración real (SES, Resend, etc.) en producción.
"""
import logging

from app.config import settings

logger = logging.getLogger("mactral.mailer")


def build_activation_link(token: str) -> str:
    return f"{settings.app_base_url}/activar-cuenta?token={token}"


def send_activation_email(email: str, activation_link: str) -> None:
    logger.info("Enlace de activación enviado a %s: %s", email, activation_link)


def send_password_reset_email(email: str, reset_link: str) -> None:
    logger.info("Enlace de recuperación de contraseña enviado a %s: %s", email, reset_link)
