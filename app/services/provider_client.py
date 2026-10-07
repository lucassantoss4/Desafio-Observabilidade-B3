"""Cliente assíncrono para comunicação com o mock provider."""

import os

import httpx

from app.models.provider import ProviderValidationResponse


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

        # httpx.AsyncClient evita bloquear o processamento enquanto a aplicação
        # aguarda a dependência externa responder.
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
            return ProviderValidationResponse(**response.json())
