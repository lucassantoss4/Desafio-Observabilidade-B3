from fastapi import APIRouter, Query

from app.models.streaming import StreamingAuthorizationResponse


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "stream-authorization-api"}


# O response_model fixa o contrato da rota e valida a resposta antes de
# devolvê-la ao cliente.
@router.get("/stream/authorize", response_model=StreamingAuthorizationResponse)
def authorize_streaming(
    user_id: str = Query(min_length=1, max_length=100),
    movie_id: str = Query(min_length=1, max_length=100),
) -> StreamingAuthorizationResponse:
    return StreamingAuthorizationResponse(
        user_id=user_id,
        movie_id=movie_id,
        authorized=True,
        resolution="4K",
        drm_token=f"mock-token-{user_id}-{movie_id}",
        server_region="sa-east-1",
    )
