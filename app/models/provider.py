"""Contrato recebido do mock provider externo."""

from pydantic import BaseModel, Field


class ProviderValidationResponse(BaseModel):
    """Representa o payload retornado pela dependência externa.

    Os dados são validados e tipados antes de influenciarem a regra de
    negócio da API principal.
    """

    user_id: str = Field(..., description="ID do usuário recebido pelo provider")
    movie_id: str = Field(..., description="ID do filme recebido pelo provider")
    subscription_active: bool = Field(..., description="Se a assinatura do usuário está ativa")
    bandwidth_mbps: int = Field(..., description="Largura de banda simulada pela dependência externa")
    server_load_percent: int = Field(..., description="Carga do servidor simulada pela dependência externa")
    server_region: str = Field(..., description="Região do servidor simulada pela dependência externa")
