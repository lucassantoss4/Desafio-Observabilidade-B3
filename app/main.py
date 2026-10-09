import logging
import time

import httpx
from fastapi import FastAPI
from fastapi import HTTPException, Query

from app.logging import configure_json_logging
from app.provider import ProviderClient
from app.schemas import StreamingAuthorizationResponse


configure_json_logging(service="stream-authorization-api", level=logging.INFO, logger_name="stream-authorization-api")
app = FastAPI(title="stream-authorization-api")

logger = logging.getLogger("stream-authorization-api")
provider_client = ProviderClient()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "stream-authorization-api"}


# O provider fornece os fatores externos, mas a API principal decide a
# autorização final e a resolução do stream.
@app.get("/stream/authorize", response_model=StreamingAuthorizationResponse)
async def authorize_streaming(
    user_id: str = Query(min_length=1, max_length=100),
    movie_id: str = Query(min_length=1, max_length=100),
) -> StreamingAuthorizationResponse:
    """Consulta o provider e aplica a regra de negócio do contrato atual."""
    started_at = time.perf_counter()
    logger.info(
        "stream authorization started",
        extra={
            "event": "stream_authorization_started",
            "user_id": user_id,
            "movie_id": movie_id,
        },
    )

    try:
        provider_response = await provider_client.validate(user_id, movie_id)
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
        # Somente exceções específicas do cliente HTTP são convertidas em 503,
        # porque essas falhas representam indisponibilidade da dependência externa.
        # Não usamos except Exception para não mascarar erros que devem ser
        # observados e tratados de forma explícita.
        raise HTTPException(
            status_code=503,
            detail="External validation service unavailable",
        ) from exc

    authorized = provider_response.subscription_active
    if not authorized:
        # Uma assinatura inativa bloqueia o acesso antes de considerar a rede ou
        # a carga do servidor; isso não é uma degradação técnica porque o acesso
        # foi explicitamente negado pela regra de negócio.
        resolution = "none"
    elif provider_response.bandwidth_mbps >= 25 and provider_response.server_load_percent < 80:
        # Boa banda e carga abaixo do limite permitem a qualidade máxima
        # prevista pela regra de negócio.
        resolution = "4K"
    else:
        # Quando a autorização continua válida, porém não atende ao limiar de 4K,
        # a qualidade cai para um nível funcional e estável.
        resolution = "1080p"

    latency_ms = (time.perf_counter() - started_at) * 1000.0
    response = StreamingAuthorizationResponse(
        user_id=user_id,
        movie_id=movie_id,
        authorized=authorized,
        resolution=resolution,
        drm_token=f"mock-token-{user_id}-{movie_id}",
        server_region=provider_response.server_region,
    )

    logger.info(
        "stream authorization completed",
        extra={
            "event": "stream_authorization_completed",
            "user_id": user_id,
            "movie_id": movie_id,
            "authorized": response.authorized,
            "resolution": response.resolution,
            "server_region": response.server_region,
            "latency_ms": latency_ms,
        },
    )

    if authorized and resolution == "1080p":
        reason_candidates = []
        if provider_response.bandwidth_mbps < 25:
            reason_candidates.append("insufficient_bandwidth")
        if provider_response.server_load_percent >= 80:
            reason_candidates.append("high_server_load")
        reason = reason_candidates[0] if len(reason_candidates) == 1 else reason_candidates

        logger.warning(
            "stream authorization degraded",
            extra={
                "event": "stream_authorization_degraded",
                "user_id": user_id,
                "movie_id": movie_id,
                "resolution": resolution,
                "bandwidth_mbps": provider_response.bandwidth_mbps,
                "server_load_percent": provider_response.server_load_percent,
                "reason": reason,
            },
        )

    return response
