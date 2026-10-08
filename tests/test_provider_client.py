"""Testes da fronteira HTTP do mock provider sem depender de um servidor real."""

import asyncio
import logging
from unittest.mock import patch

from app.models.provider import ProviderValidationResponse
from app.services.provider_client import ProviderClient


class FakeResponse:
    """Resposta mínima para simular a estrutura esperada do httpx."""

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_provider_client_parses_successful_response() -> None:
    """Valida a conversão da resposta do provider para o modelo interno."""

    payload = {
        "user_id": "usr_99823",
        "movie_id": "mov_dune_part2",
        "subscription_active": True,
        "bandwidth_mbps": 120,
        "server_load_percent": 35,
        "server_region": "sa-east-1",
    }

    # A fronteira HTTP é simulada para que o teste valide somente a conversão
    # da resposta, sem depender da porta 8001 ou de um processo Uvicorn.
    async def fake_get(self, url, params):
        assert url == "http://127.0.0.1:8001/validate"
        assert params == {
            "user_id": "usr_99823",
            "movie_id": "mov_dune_part2",
            "mode": "success",
        }
        return FakeResponse(payload)

    with patch("httpx.AsyncClient.get", new=fake_get):
        client = ProviderClient(base_url="http://127.0.0.1:8001")
        result = asyncio.run(client.validate("usr_99823", "mov_dune_part2"))

    assert result == ProviderValidationResponse(**payload)


def test_provider_client_uses_success_mode_and_expected_query_params() -> None:
    """Verifica URL, parâmetros enviados e a semântica do modo success."""

    payload = {
        "user_id": "usr_99823",
        "movie_id": "mov_dune_part2",
        "subscription_active": True,
        "bandwidth_mbps": 120,
        "server_load_percent": 35,
        "server_region": "sa-east-1",
    }
    calls = []

    # O teste valida o contrato de requisição do cliente para garantir que a
    # chamada preserve o endpoint e os parâmetros esperados.
    async def fake_get(self, url, params):
        calls.append({"url": url, "params": params})
        return FakeResponse(payload)

    with patch("httpx.AsyncClient.get", new=fake_get):
        client = ProviderClient(base_url="http://127.0.0.1:8001")
        asyncio.run(client.validate("usr_99823", "mov_dune_part2"))

    assert calls == [
        {
            "url": "http://127.0.0.1:8001/validate",
            "params": {
                "user_id": "usr_99823",
                "movie_id": "mov_dune_part2",
                "mode": "success",
            },
        }
    ]


def test_provider_client_logs_structured_events_without_sensitive_fields(caplog) -> None:
    """Valida que o cliente regista apenas o ciclo HTTP e não expõe segredos."""

    payload = {
        "user_id": "usr_99823",
        "movie_id": "mov_dune_part2",
        "subscription_active": True,
        "bandwidth_mbps": 120,
        "server_load_percent": 35,
        "server_region": "sa-east-1",
    }
    caplog.set_level(logging.INFO, logger="stream-authorization-api")

    async def fake_get(self, url, params):
        return FakeResponse(payload)

    with patch("httpx.AsyncClient.get", new=fake_get):
        client = ProviderClient(base_url="http://127.0.0.1:8001")
        asyncio.run(client.validate("usr_99823", "mov_dune_part2"))

    event_names = {getattr(record, "event", None) for record in caplog.records}
    assert "provider_request_started" in event_names
    assert "provider_request_completed" in event_names

    completed = next(record for record in caplog.records if getattr(record, "event", None) == "provider_request_completed")
    assert completed.provider_mode == "success"
    assert completed.provider_status_code == 200
    assert completed.server_region == "sa-east-1"
    assert isinstance(completed.latency_ms, float)

    serialized = "\n".join(str(record.getMessage()) for record in caplog.records)
    for forbidden in ("drm_token", "authorization", "cookie", "trace_id", "span_id"):
        assert forbidden not in serialized.lower()
