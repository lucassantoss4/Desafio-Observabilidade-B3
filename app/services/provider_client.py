"""Cliente assíncrono para comunicação com o mock provider."""

import os

import httpx

from app.models.provider import ProviderValidationResponse


class ProviderClient:
    """Responsável somente pela comunicação HTTP com o provider externo.

    A regra de autorização não pertence a este módulo; ele apenas coleta os
    fatores simulados que a API principal usa para decidir a resposta final.
    """

    def __init__(self, base_url: str | None = None, timeout: float = 5.0) -> None:
        # MOCK_PROVIDER_URL permite alternar entre localhost no ambiente local e
        # o nome do serviço em uma futura rede do Docker Compose sem mudar a
        # lógica da aplicação.
        self.base_url = base_url or os.getenv("MOCK_PROVIDER_URL", "http://127.0.0.1:8001")
        self.timeout = timeout

    async def validate(self, user_id: str, movie_id: str) -> ProviderValidationResponse:
        """Consulta o provider em modo success e converte a resposta em modelo."""

        # httpx.AsyncClient evita bloquear o processamento enquanto a aplicação
        # aguarda a dependência externa responder.
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url.rstrip('/')}/validate",
                params={
                    "user_id": user_id,
                    "movie_id": movie_id,
                    "mode": "success",
                },
            )
            response.raise_for_status()
            return ProviderValidationResponse(**response.json())

        # O tratamento completo de timeout e falhas HTTP será feito na próxima
        # etapa. Nesta integração, o objetivo é validar somente o caminho de sucesso.
