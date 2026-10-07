from pydantic import BaseModel, Field


class StreamingAuthorizationResponse(BaseModel):
    user_id: str = Field(..., description="ID do usuário que está solicitando a autorização de streaming")
    movie_id: str = Field(..., description="ID do filme que está sendo solicitado para streaming")
    authorized: bool = Field(..., description="Indica se o usuário está autorizado a assistir ao filme")
    resolution: str = Field(..., description="Resolução do streaming autorizado")
    drm_token: str = Field(..., description="Token DRM para proteger o conteúdo de streaming")
    server_region: str = Field(..., description="Região do servidor que fornecerá o streaming")
