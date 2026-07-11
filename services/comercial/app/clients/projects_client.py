"""E2-H4: cliente HTTP hacia services/projects para crear el Registro
Maestro al clasificar un lead como Vendido. Se reenvía el JWT del vendedor
que cerró la venta (mismo JWT_SECRET compartido entre microservicios)."""
import httpx

from app.config import settings


class ProjectsServiceError(Exception):
    pass


def create_project(token: str, payload: dict) -> dict:
    try:
        response = httpx.post(
            f"{settings.projects_service_url}/projects",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise ProjectsServiceError("No se pudo contactar al servicio de proyectos") from exc

    if response.status_code != 201:
        raise ProjectsServiceError(
            f"El servicio de proyectos respondió con un error ({response.status_code})"
        )

    return response.json()
