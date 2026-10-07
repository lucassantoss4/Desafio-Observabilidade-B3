from fastapi import FastAPI

from app.routes.streaming import router as streaming_router


app = FastAPI(title="stream-authorization-api")

# Mantém a aplicação principal enxuta e separa as rotas por módulo.
app.include_router(streaming_router)
