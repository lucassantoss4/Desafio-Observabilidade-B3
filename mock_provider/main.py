import asyncio
from enum import Enum

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.logging import configure_tracing


class ValidationMode(str, Enum):
    success = "success"
    slow = "slow"
    error = "error"


class MockValidationResponse(BaseModel):
    user_id: str = Field(..., description="Identificador do usuário.")
    movie_id: str = Field(..., description="Identificador do filme.")
    subscription_active: bool = Field(..., description="Indica se a assinatura está ativa.")
    bandwidth_mbps: int = Field(..., description="Largura de banda simulada, em Mbps.")
    server_load_percent: int = Field(..., description="Carga simulada do servidor, em percentual.")
    server_region: str = Field(..., description="Região do servidor.")


app = FastAPI(title="mock-provider")
configure_tracing(service="mock-provider", app=app)


@app.get("/validate", response_model=MockValidationResponse)
async def validate(
    user_id: str = Query(..., min_length=1, max_length=100),
    movie_id: str = Query(..., min_length=1, max_length=100),
    mode: ValidationMode = Query(default=ValidationMode.success),
) -> MockValidationResponse:
    if mode == ValidationMode.error:
        raise HTTPException(
            status_code=503,
            detail="External validation service unavailable",
        )

    if mode == ValidationMode.slow:
        # Simula dependência externa lenta.
        await asyncio.sleep(3)

    return MockValidationResponse(
        user_id=user_id,
        movie_id=movie_id,
        subscription_active=True,
        bandwidth_mbps=120,
        server_load_percent=35,
        server_region="sa-east-1",
    )
