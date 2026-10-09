"""Formatter e utilitários para logs JSON e tracing OpenTelemetry."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

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
_TRACE_PROVIDER_CONFIGURED = False
_HTTPX_INSTRUMENTED = False
_INSTRUMENTED_APPS: set[int] = set()


def _is_sensitive_field(name: Any) -> bool:
    """Compara nomes de campos ignorando caixa para evitar vazamentos de segredos."""
    return str(name).lower() in SENSITIVE_FIELD_NAMES


def _sanitize_value(value: Any, *, parent_name: Any | None = None) -> Any:
    """Redige campos sensíveis em valores simples e estruturas aninhadas."""
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
        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            payload["trace_id"] = f"{span_context.trace_id:032x}"
            payload["span_id"] = f"{span_context.span_id:016x}"

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_FIELDS or key.startswith("_"):
                continue
            if key in {"timestamp", "level", "service", "event", "message", "trace_id", "span_id"}:
                continue
            if _is_sensitive_field(key):
                payload[key] = REDACTED_VALUE
                continue
            payload[key] = _sanitize_value(value, parent_name=key)

        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            if exc_text:
                # Não há sanitização confiável para texto arbitrário de exceção.
                payload["exception"] = exc_text

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_tracing(*, service: str = DEFAULT_SERVICE_NAME, app: Any | None = None) -> None:
    """Configura tracing mínimo com instrumentação de FastAPI e HTTPX."""
    global _TRACE_PROVIDER_CONFIGURED, _HTTPX_INSTRUMENTED

    if not _TRACE_PROVIDER_CONFIGURED:
        provider = TracerProvider(resource=Resource.create({"service.name": service}))
        traces_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        if traces_endpoint:
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=traces_endpoint)))
        trace.set_tracer_provider(provider)
        _TRACE_PROVIDER_CONFIGURED = True

    provider = trace.get_tracer_provider()

    if not _HTTPX_INSTRUMENTED:
        HTTPXClientInstrumentor().instrument(tracer_provider=provider)
        _HTTPX_INSTRUMENTED = True

    if app is not None and id(app) not in _INSTRUMENTED_APPS:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        _INSTRUMENTED_APPS.add(id(app))


def configure_json_logging(
    *,
    service: str = DEFAULT_SERVICE_NAME,
    level: int = logging.INFO,
    logger_name: str | None = None,
    event: str = DEFAULT_EVENT_NAME,
) -> logging.Logger:
    """Configura logger JSON sem duplicar handlers em chamadas repetidas."""
    target_logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    target_logger.setLevel(level)

    for handler in target_logger.handlers:
        if isinstance(handler.formatter, JsonFormatter):
            return target_logger

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonFormatter(service=service, event=event))
    target_logger.addHandler(stream_handler)

    # Mantém configuração restrita ao logger alvo e não inventa IDs de trace/span.
    return target_logger
