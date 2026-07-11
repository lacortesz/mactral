import httpx
import pytest

from app.clients import projects_client


class _FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


def test_create_project_devuelve_el_json_en_exito(monkeypatch):
    def _fake_post(url, json, headers, timeout):
        assert headers["Authorization"] == "Bearer tok123"
        return _FakeResponse(201, {"id": "p1", "crp_code": "GM26-01"})

    monkeypatch.setattr(httpx, "post", _fake_post)

    result = projects_client.create_project("tok123", {"crp_prefix": "GM"})

    assert result == {"id": "p1", "crp_code": "GM26-01"}


def test_create_project_lanza_error_si_projects_responde_error(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *args, **kw: _FakeResponse(422, {"detail": "bad"}))

    with pytest.raises(projects_client.ProjectsServiceError, match="422"):
        projects_client.create_project("tok123", {"crp_prefix": "GM"})


def test_create_project_lanza_error_si_no_hay_red(monkeypatch):
    def _raise(*args, **kwargs):
        raise httpx.ConnectError("no route to host")

    monkeypatch.setattr(httpx, "post", _raise)

    with pytest.raises(projects_client.ProjectsServiceError, match="No se pudo contactar"):
        projects_client.create_project("tok123", {"crp_prefix": "GM"})
