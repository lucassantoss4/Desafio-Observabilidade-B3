"""Cliente assíncrono para comunicação com o mock provider."""

import logging
import os
import time

import httpx

from app.models.provider import ProviderValidationResponse


logger = logging.getLogger("stream-authorization-api")


class ProviderClient:
    """Responsável somente pela comunicação HTTP com o provider externo.

    A regra de autorização não pertence a este módulo; ele apenas coleta os
    fatores simulados que a API principal usa para decidir a resposta final.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        mode: str | None = None,
    ) -> None:
        # MOCK_PROVIDER_URL permite alternar entre localhost local e a origem do
        # serviço em uma futura execução em container, sem alterar a regra de
        # negócio da API principal.
        self.base_url = base_url or os.getenv("MOCK_PROVIDER_URL", "http://127.0.0.1:8001")

        # PROVIDER_TIMEOUT_SECONDS limita o tempo de espera pela dependência
        # externa sem bloquear a aplicação indefinidamente; o valor padrão é
        # curto para manter a demonstração previsível.
        configured_timeout = os.getenv("PROVIDER_TIMEOUT_SECONDS")
        self.timeout = float(configured_timeout) if configured_timeout is not None else (timeout if timeout is not None else 1.0)

        # MOCK_PROVIDER_MODE existe somente para simular os cenários de sucesso,
        # atraso e falha da dependência externa durante a demonstração.
        self.mode = mode or os.getenv("MOCK_PROVIDER_MODE", "success")

    async def validate(self, user_id: str, movie_id: str) -> ProviderValidationResponse:
        """Consulta o provider usando o modo configurado e converte a resposta em modelo."""
        started_at = time.perf_counter()
        logger.info(
            "provider request started",
            extra={
                "event": "provider_request_started",
                "provider_mode": self.mode,
                "user_id": user_id,
                "movie_id": movie_id,
            },
        )

        # O use de perf_counter mede a duração da chamada externa sem depender de
        # relógios de sistema ou de carregamento de contexto de datetime.
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url.rstrip('/')}/validate",
                    params={
                        "user_id": user_id,
                        "movie_id": movie_id,
                        "mode": self.mode,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                latency_ms = (time.perf_counter() - started_at) * 1000.0
                logger.info(
                    "provider request completed",
                    extra={
                        "event": "provider_request_completed",
                        "provider_mode": self.mode,
                        "provider_status_code": getattr(response, "status_code", 200),
                        "server_region": payload.get("server_region"),
                        "latency_ms": latency_ms,
                    },
                )
                return ProviderValidationResponse(**payload)
        except httpx.TimeoutException as exc:
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            logger.warning(
                "provider request failed",
                extra={
                    "event": "provider_request_failed",
                    "error_type": "timeout",
                    "provider_mode": self.mode,
                    "latency_ms": latency_ms,
                },
            )
            raise exc
        except httpx.ConnectError as exc:
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            logger.warning(
                "provider request failed",
                extra={
                    "event": "provider_request_failed",
                    "error_type": "connect_error",
                    "provider_mode": self.mode,
                    "latency_ms": latency_ms,
                },
            )
            raise exc
        except httpx.HTTPStatusError as exc:
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            logger.warning(
                "provider request failed",
                extra={
                    "event": "provider_request_failed",
                    "error_type": "http_status_error",
                    "provider_mode": self.mode,
                    "provider_status_code": getattr(exc.response, "status_code", None),
                    "latency_ms": latency_ms,
                },
            )
            raise exc
