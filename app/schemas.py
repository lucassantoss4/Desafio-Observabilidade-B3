"""Modelos Pydantic usados pela API e pelo provider."""

from pydantic import BaseModel, Field


class ProviderValidationResponse(BaseModel):
    """Payload de validação retornado pelo provider."""

    user_id: str = Field(..., description="Identificador do usuário.")
    movie_id: str = Field(..., description="Identificador do filme.")
    subscription_active: bool = Field(..., description="Indica se a assinatura está ativa.")
    bandwidth_mbps: int = Field(..., description="Largura de banda simulada, em Mbps.")
    server_load_percent: int = Field(..., description="Carga simulada do servidor, em percentual.")
    server_region: str = Field(..., description="Região do servidor.")


class StreamingAuthorizationResponse(BaseModel):
    """Resposta de autorização de streaming."""

    user_id: str = Field(..., description="Identificador do usuário.")
    movie_id: str = Field(..., description="Identificador do filme.")
    authorized: bool = Field(..., description="Indica se o streaming foi autorizado.")
    resolution: str = Field(..., description="Resolução autorizada.")
    drm_token: str = Field(..., description="Token DRM da resposta.")
    server_region: str = Field(..., description="Região do servidor.")
