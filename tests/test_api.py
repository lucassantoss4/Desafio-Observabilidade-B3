"""Testes de contrato da API principal com o provider simulado."""

import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ProviderValidationResponse


# TestClient executa a aplicação ASGI em memória e permite validar a API sem
# iniciar um processo Uvicorn real.
client = TestClient(app)


@pytest.fixture
def mock_provider_success(monkeypatch):
    """Substitui a dependência externa pelo cenário padrão de sucesso."""

    # A substituição mantém os testes determinísticos e independentes da porta 8001.
    async def fake_validate(_user_id: str, _movie_id: str):
        return ProviderValidationResponse(
            user_id="usr_99823",
            movie_id="mov_dune_part2",
            subscription_active=True,
            bandwidth_mbps=120,
            server_load_percent=35,
            server_region="sa-east-1",
        )

    monkeypatch.setattr("app.routes.streaming.provider_client.validate", fake_validate)


def _raise_provider_exception(monkeypatch, exc: Exception) -> None:
    """Simula uma falha específica da dependência externa sem tocar a porta 8001."""

    # Os testes documentam o comportamento da API quando a dependência externa
    # falha, sem iniciar um servidor real para a demonstração.
    async def fake_validate(_user_id: str, _movie_id: str):
        raise exc

    monkeypatch.setattr("app.routes.streaming.provider_client.validate", fake_validate)


def test_health_returns_200() -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_expected_payload() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "stream-authorization-api",
    }


def test_stream_authorize_with_valid_params_returns_200(mock_provider_success) -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 200


def test_stream_authorize_valid_response_contains_all_fields(mock_provider_success) -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )
    payload = response.json()

    expected_fields = {
        "user_id",
        "movie_id",
        "authorized",
        "resolution",
        "drm_token",
        "server_region",
    }

    assert response.status_code == 200
    assert expected_fields.issubset(payload.keys())


def test_stream_authorize_authorized_is_true(mock_provider_success) -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 200
    assert response.json()["authorized"] is True


def test_stream_authorize_resolution_is_4k(mock_provider_success) -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 200
    assert response.json()["resolution"] == "4K"


def test_stream_authorize_server_region_is_sa_east_1(mock_provider_success) -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 200
    assert response.json()["server_region"] == "sa-east-1"


def test_provider_timeout_returns_503(monkeypatch) -> None:
    _raise_provider_exception(monkeypatch, httpx.TimeoutException("provider timed out"))

    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )

    assert response.status_code == 503


def test_provider_connect_error_returns_503(monkeypatch) -> None:
    _raise_provider_exception(monkeypatch, httpx.ConnectError("connection refused"))

    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )

    assert response.status_code == 503


def test_provider_http_status_error_returns_503(monkeypatch) -> None:
    request = httpx.Request("GET", "http://127.0.0.1:8001/validate")
    response = httpx.Response(503, request=request)
    exc = httpx.HTTPStatusError("provider unavailable", request=request, response=response)
    _raise_provider_exception(monkeypatch, exc)

    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )

    assert response.status_code == 503


def test_provider_failure_returns_expected_detail(monkeypatch) -> None:
    _raise_provider_exception(monkeypatch, httpx.ConnectError("connection refused"))

    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )

    assert response.json() == {"detail": "External validation service unavailable"}


def test_health_returns_200_after_provider_failure(monkeypatch) -> None:
    _raise_provider_exception(monkeypatch, httpx.TimeoutException("provider timed out"))

    failed_response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )
    health_response = client.get("/health")

    assert failed_response.status_code == 503
    assert health_response.status_code == 200


def test_stream_authorize_without_user_id_returns_422() -> None:
    response = client.get("/stream/authorize", params={"movie_id": "mov_dune_part2"})
    assert response.status_code == 422


def test_stream_authorize_without_movie_id_returns_422() -> None:
    response = client.get("/stream/authorize", params={"user_id": "usr_99823"})
    assert response.status_code == 422


def test_stream_authorize_with_empty_user_id_returns_422() -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "", "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 422


def test_stream_authorize_with_empty_movie_id_returns_422() -> None:
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": ""},
    )
    assert response.status_code == 422


def test_stream_authorize_with_user_id_larger_than_100_returns_422() -> None:
    # O contrato aceita até 100 caracteres; 101 valida o primeiro valor fora do
    # limite permitido.
    long_user_id = "u" * 101
    response = client.get(
        "/stream/authorize",
        params={"user_id": long_user_id, "movie_id": "mov_dune_part2"},
    )
    assert response.status_code == 422


def test_stream_authorize_with_movie_id_larger_than_100_returns_422() -> None:
    # A mesma regra vale para movie_id: 101 caracteres deve falhar no mesmo
    # limite máximo.
    long_movie_id = "m" * 101
    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": long_movie_id},
    )
    assert response.status_code == 422


# O provider é substituído neste bloco para testar somente a regra de negócio
# da API principal, sem depender de um processo real na porta 8001.
def test_provider_success_with_good_bandwidth_returns_4k_resolution(monkeypatch) -> None:
    async def fake_validate(_user_id: str, _movie_id: str):
        return ProviderValidationResponse(
            user_id="usr_99823",
            movie_id="mov_dune_part2",
            subscription_active=True,
            bandwidth_mbps=120,
            server_load_percent=35,
            server_region="sa-east-1",
        )

    monkeypatch.setattr("app.routes.streaming.provider_client.validate", fake_validate)

    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )

    assert response.status_code == 200
    assert response.json()["authorized"] is True
    assert response.json()["resolution"] == "4K"
    assert response.json()["server_region"] == "sa-east-1"


# A assinatura inativa é um caso crítico porque a regra de negócio deve
# impedir o acesso mesmo quando a rede e a carga do servidor seriam favoráveis.
def test_provider_inactive_subscription_returns_none_resolution(monkeypatch) -> None:
    async def fake_validate(_user_id: str, _movie_id: str):
        return ProviderValidationResponse(
            user_id="usr_99823",
            movie_id="mov_dune_part2",
            subscription_active=False,
            bandwidth_mbps=50,
            server_load_percent=20,
            server_region="sa-east-1",
        )

    monkeypatch.setattr("app.routes.streaming.provider_client.validate", fake_validate)

    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )

    assert response.status_code == 200
    assert response.json()["authorized"] is False
    assert response.json()["resolution"] == "none"


def test_provider_active_with_low_bandwidth_returns_1080p(monkeypatch) -> None:
    async def fake_validate(_user_id: str, _movie_id: str):
        return ProviderValidationResponse(
            user_id="usr_99823",
            movie_id="mov_dune_part2",
            subscription_active=True,
            bandwidth_mbps=10,
            server_load_percent=20,
            server_region="sa-east-1",
        )

    monkeypatch.setattr("app.routes.streaming.provider_client.validate", fake_validate)

    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )

    assert response.status_code == 200
    assert response.json()["resolution"] == "1080p"


def test_provider_active_with_high_load_returns_1080p(monkeypatch) -> None:
    async def fake_validate(_user_id: str, _movie_id: str):
        return ProviderValidationResponse(
            user_id="usr_99823",
            movie_id="mov_dune_part2",
            subscription_active=True,
            bandwidth_mbps=80,
            server_load_percent=90,
            server_region="sa-east-1",
        )

    monkeypatch.setattr("app.routes.streaming.provider_client.validate", fake_validate)

    response = client.get(
        "/stream/authorize",
        params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
    )

    assert response.status_code == 200
    assert response.json()["resolution"] == "1080p"


def test_stream_authorize_success_logs_expected_events(caplog) -> None:
    caplog.set_level(logging.INFO, logger="stream-authorization-api")

    payload = {
        "user_id": "usr_99823",
        "movie_id": "mov_dune_part2",
        "subscription_active": True,
        "bandwidth_mbps": 120,
        "server_load_percent": 35,
        "server_region": "sa-east-1",
    }

    async def fake_get(self, url, params):
        return type("FakeResponse", (), {"status_code": 200, "json": lambda self: payload, "raise_for_status": lambda self: None})()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("httpx.AsyncClient.get", fake_get)
        response = client.get(
            "/stream/authorize",
            params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
        )

    assert response.status_code == 200
    event_names = {getattr(record, "event", None) for record in caplog.records}
    assert "stream_authorization_started" in event_names
    assert "provider_request_started" in event_names
    assert "provider_request_completed" in event_names
    assert "stream_authorization_completed" in event_names

    started = next(record for record in caplog.records if getattr(record, "event", None) == "stream_authorization_started")
    assert started.user_id == "usr_99823"
    assert started.movie_id == "mov_dune_part2"

    completed = next(record for record in caplog.records if getattr(record, "event", None) == "stream_authorization_completed")
    assert completed.authorized is True
    assert completed.resolution == "4K"
    assert completed.server_region == "sa-east-1"
    assert isinstance(completed.latency_ms, float)


def test_stream_authorize_low_bandwidth_logs_degradation(caplog) -> None:
    payload = {
        "user_id": "usr_99823",
        "movie_id": "mov_dune_part2",
        "subscription_active": True,
        "bandwidth_mbps": 10,
        "server_load_percent": 20,
        "server_region": "sa-east-1",
    }

    async def fake_get(self, url, params):
        return type("FakeResponse", (), {"status_code": 200, "json": lambda self: payload, "raise_for_status": lambda self: None})()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("httpx.AsyncClient.get", fake_get)
        caplog.set_level(logging.INFO, logger="stream-authorization-api")
        response = client.get(
            "/stream/authorize",
            params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
        )

    assert response.status_code == 200
    assert response.json()["resolution"] == "1080p"
    degraded = next(record for record in caplog.records if getattr(record, "event", None) == "stream_authorization_degraded")
    assert degraded.resolution == "1080p"
    assert degraded.reason == "insufficient_bandwidth"


def test_stream_authorize_high_load_logs_degradation(caplog) -> None:
    payload = {
        "user_id": "usr_99823",
        "movie_id": "mov_dune_part2",
        "subscription_active": True,
        "bandwidth_mbps": 80,
        "server_load_percent": 90,
        "server_region": "sa-east-1",
    }

    async def fake_get(self, url, params):
        return type("FakeResponse", (), {"status_code": 200, "json": lambda self: payload, "raise_for_status": lambda self: None})()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("httpx.AsyncClient.get", fake_get)
        caplog.set_level(logging.INFO, logger="stream-authorization-api")
        response = client.get(
            "/stream/authorize",
            params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
        )

    assert response.status_code == 200
    assert response.json()["resolution"] == "1080p"
    degraded = next(record for record in caplog.records if getattr(record, "event", None) == "stream_authorization_degraded")
    assert degraded.reason == "high_server_load"


def test_provider_inactive_subscription_is_not_logged_as_degradation(caplog) -> None:
    payload = {
        "user_id": "usr_99823",
        "movie_id": "mov_dune_part2",
        "subscription_active": False,
        "bandwidth_mbps": 80,
        "server_load_percent": 20,
        "server_region": "sa-east-1",
    }

    async def fake_get(self, url, params):
        return type("FakeResponse", (), {"status_code": 200, "json": lambda self: payload, "raise_for_status": lambda self: None})()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("httpx.AsyncClient.get", fake_get)
        caplog.set_level(logging.INFO, logger="stream-authorization-api")
        response = client.get(
            "/stream/authorize",
            params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
        )

    assert response.status_code == 200
    assert response.json()["authorized"] is False
    assert response.json()["resolution"] == "none"
    event_names = {getattr(record, "event", None) for record in caplog.records}
    assert "stream_authorization_degraded" not in event_names


def test_provider_timeout_logs_failed_event_and_returns_503(caplog) -> None:
    async def fake_get(self, url, params):
        raise httpx.TimeoutException("provider timed out")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("httpx.AsyncClient.get", fake_get)
        caplog.set_level(logging.INFO, logger="stream-authorization-api")
        response = client.get(
            "/stream/authorize",
            params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
        )

    assert response.status_code == 503
    assert any(getattr(record, "event", None) == "provider_request_failed" for record in caplog.records)
    failed = next(record for record in caplog.records if getattr(record, "event", None) == "provider_request_failed")
    assert failed.error_type == "timeout"
    assert isinstance(failed.latency_ms, float)


def test_provider_status_error_logs_status_code_and_is_secret_safe(caplog) -> None:
    request = httpx.Request("GET", "http://127.0.0.1:8001/validate")
    response = httpx.Response(503, request=request)

    async def fake_get(self, url, params):
        raise httpx.HTTPStatusError("provider unavailable", request=request, response=response)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("httpx.AsyncClient.get", fake_get)
        caplog.set_level(logging.INFO, logger="stream-authorization-api")
        response = client.get(
            "/stream/authorize",
            params={"user_id": "usr_99823", "movie_id": "mov_dune_part2"},
        )

    assert response.status_code == 503
    failed = next(record for record in caplog.records if getattr(record, "event", None) == "provider_request_failed")
    assert failed.provider_status_code == 503
    assert failed.error_type == "http_status_error"
    serialized = "\n".join(str(record.getMessage()) for record in caplog.records)
    for bad_token in ("drm_token", "password", "secret", "api_key", "cookie", "trace_id", "span_id"):
        assert bad_token not in serialized.lower()
