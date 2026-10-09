"""Formatter e utilitários para logs estruturados em JSON.

A serialização em JSON facilita ingestão, consulta e paralelismo entre serviços,
porque cada linha representa um evento autocontido com os campos essenciais.
Usamos UTC e ISO 8601 para evitar ambiguidades de timezone entre ambientes e
facilitar correlação entre logs gerados em diferentes hosts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

DEFAULT_SERVICE_NAME = "stream-authorization-api"
DEFAULT_EVENT_NAME = "application_log"
REDACTED_VALUE = "[REDACTED]"
SENSITIVE_FIELD_NAMES = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "access_token",
    "refresh_token",
    "drm_token",
    "api_key",
}
_RESERVED_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


def _is_sensitive_field(name: Any) -> bool:
    """Compara nomes de campos ignorando caixa para evitar vazamentos de segredos."""
    return str(name).lower() in SENSITIVE_FIELD_NAMES


def _sanitize_value(value: Any, *, parent_name: Any | None = None) -> Any:
    """Redige campos sensíveis e percorre dicionários aninhados para preservar JSON seguro."""
    if parent_name is not None and _is_sensitive_field(parent_name):
        return REDACTED_VALUE

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive_field(key):
                sanitized[str(key)] = REDACTED_VALUE
            else:
                sanitized[str(key)] = _sanitize_value(item, parent_name=key)
        return sanitized
    return str(value)


class JsonFormatter(logging.Formatter):
    """Serializa LogRecord em uma única linha JSON com campos essenciais."""

    def __init__(
        self,
        service: str = DEFAULT_SERVICE_NAME,
        event: str = DEFAULT_EVENT_NAME,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.service = service
        self.event = event

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        payload: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "service": self.service,
            "event": getattr(record, "event", self.event) or self.event,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_FIELDS or key.startswith("_"):
                continue
            if key in {"timestamp", "level", "service", "event", "message"}:
                continue
            if _is_sensitive_field(key):
                payload[key] = REDACTED_VALUE
                continue
            payload[key] = _sanitize_value(value, parent_name=key)

        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            if exc_text:
                # Mensagens de exceção não devem conter secrets; a intenção aqui é
                # ajudar no diagnóstico sem prometer sanitização automática de texto
                # arbitrário, que sempre deve ser evitado no código do produto.
                payload["exception"] = exc_text

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_json_logging(
    *,
    service: str = DEFAULT_SERVICE_NAME,
    level: int = logging.INFO,
    logger_name: str | None = None,
    event: str = DEFAULT_EVENT_NAME,
) -> logging.Logger:
    """Configura um logger em modo JSON sem duplicar handlers em chamadas repetidas."""
    target_logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    target_logger.setLevel(level)

    for handler in target_logger.handlers:
        if isinstance(handler.formatter, JsonFormatter):
            return target_logger

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonFormatter(service=service, event=event))
    target_logger.addHandler(stream_handler)

    # Não forçamos bibliotecas externas a usar a mesma configuração, apenas o logger
    # alvo da aplicação. Isso evita a substituição silenciosa de loggers de terceiros
    # sem necessidade, preservando o comportamento normal de dependências.
    # trace_id e span_id não são inventados nesta etapa porque exigem contexto real
    # de OpenTelemetry e não devem ser fabricados sem observabilidade verdadeira.
    return target_logger
