"""Rotas da API principal para saúde e autorização de streaming."""

from fastapi import APIRouter, Query

from app.models.streaming import StreamingAuthorizationResponse
from app.services.provider_client import ProviderClient


router = APIRouter()
provider_client = ProviderClient()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "stream-authorization-api"}


# O provider fornece os fatores externos, mas a API principal decide a
# autorização final e a resolução do stream.
@router.get("/stream/authorize", response_model=StreamingAuthorizationResponse)
async def authorize_streaming(
    user_id: str = Query(min_length=1, max_length=100),
    movie_id: str = Query(min_length=1, max_length=100),
) -> StreamingAuthorizationResponse:
    """Consulta o provider e aplica a regra de negócio do contrato atual."""

    provider_response = await provider_client.validate(user_id, movie_id)

    authorized = provider_response.subscription_active
    if not authorized:
        # Uma assinatura inativa bloqueia o acesso antes de considerar a rede ou
        # a carga do servidor.
        resolution = "none"
    elif provider_response.bandwidth_mbps >= 25 and provider_response.server_load_percent < 80:
        # Boa banda e carga abaixo do limite permitem a qualidade máxima
        # prevista pela regra de negócio.
        resolution = "4K"
    else:
        # Quando a autorização continua válida, porém não atende ao limiar de 4K,
        # a qualidade cai para um nível funcional e estável.
        resolution = "1080p"

    return StreamingAuthorizationResponse(
        user_id=user_id,
        movie_id=movie_id,
        authorized=authorized,
        resolution=resolution,
        drm_token=f"mock-token-{user_id}-{movie_id}",
        server_region=provider_response.server_region,
    )
