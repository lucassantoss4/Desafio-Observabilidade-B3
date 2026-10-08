import logging

from fastapi import FastAPI

from app.observability.logging import configure_json_logging
from app.routes.streaming import router as streaming_router


configure_json_logging(service="stream-authorization-api", level=logging.INFO, logger_name="stream-authorization-api")
app = FastAPI(title="stream-authorization-api")

# Mantém a aplicação principal enxuta e separa as rotas por módulo.
app.include_router(streaming_router)
