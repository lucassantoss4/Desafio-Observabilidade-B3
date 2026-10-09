import io
import json
import logging
import os

from opentelemetry import trace

from app.logging import JsonFormatter, configure_json_logging
from app.logging import configure_tracing


def _reset_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    logger.propagate = False
    logger.setLevel(logging.INFO)
    return logger


def _capture_json(logger: logging.Logger, *, message: str, extra: dict | None = None, exc_info: bool = False):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter(service="custom-service"))
    logger.addHandler(handler)
    try:
        if exc_info:
            try:
                raise ValueError("validation failed")
            except ValueError:
                # Desenvolvedores não devem incluir secrets em mensagens de exceção;
                # o traceback serve para diagnóstico sem expor dados sensíveis.
                logger.exception(message, extra=extra or {})
        else:
            logger.info(message, extra=extra or {})
    finally:
        logger.removeHandler(handler)
    payload = json.loads(stream.getvalue().strip())
    return payload


def test_json_output_is_valid_and_contains_required_fields() -> None:
    logger = _reset_logger("tests.logger.required")

    payload = _capture_json(
        logger,
        message="Autorização concluída",
        extra={
            "event": "stream_authorization_completed",
            "authorized": True,
            "resolution": "4K",
        },
    )

    assert set({"timestamp", "level", "service", "event", "message"}) <= payload.keys()
    assert payload["level"] == "INFO"
    assert payload["service"] == "custom-service"
    assert payload["event"] == "stream_authorization_completed"
    assert payload["message"] == "Autorização concluída"
    assert payload["authorized"] is True
    assert payload["resolution"] == "4K"


def test_default_event_is_used_when_missing() -> None:
    logger = _reset_logger("tests.logger.default_event")

    payload = _capture_json(logger, message="Mensagem padrão")

    assert payload["event"] == "application_log"


def test_extra_fields_are_preserved_with_native_types() -> None:
    logger = _reset_logger("tests.logger.types")

    payload = _capture_json(
        logger,
        message="Tipos seguros",
        extra={
            "enabled": True,
            "count": 7,
            "ratio": 1.5,
            "nullable": None,
        },
    )

    assert payload["enabled"] is True
    assert payload["count"] == 7
    assert payload["ratio"] == 1.5
    assert payload["nullable"] is None


def test_non_serializable_values_are_stringified_without_breaking_logs() -> None:
    logger = _reset_logger("tests.logger.unsafe")

    class UnsafeObject:
        def __str__(self) -> str:
            return "unsafe-object"

    payload = _capture_json(logger, message="Objetos em JSON", extra={"unsafe": UnsafeObject()})

    assert payload["unsafe"] == "unsafe-object"


def test_sensitive_fields_are_redacted_case_insensitive() -> None:
    logger = _reset_logger("tests.logger.sensitive")

    payload = _capture_json(
        logger,
        message="Credenciais em log",
        extra={
            "drm_token": "token-123",
            "Authorization": "Bearer secret",
            "api_key": "abc123",
            "safe_value": "keep-me",
        },
    )

    assert payload["drm_token"] == "[REDACTED]"
    assert payload["Authorization"] == "[REDACTED]"
    assert payload["api_key"] == "[REDACTED]"
    assert payload["safe_value"] == "keep-me"


def test_nested_sensitive_fields_are_redacted() -> None:
    logger = _reset_logger("tests.logger.nested")

    payload = _capture_json(
        logger,
        message="Payload aninhado",
        extra={
            "nested": {
                "password": "p@ss",
                "inside": {"access_token": "token-xyz"},
                "keep": "ok",
            }
        },
    )

    assert payload["nested"]["password"] == "[REDACTED]"
    assert payload["nested"]["inside"]["access_token"] == "[REDACTED]"
    assert payload["nested"]["keep"] == "ok"


def test_non_sensitive_fields_remain_and_external_context_is_not_collected() -> None:
    logger = _reset_logger("tests.logger.context")
    os.environ["APP_SECRET"] = "ignored-secret"

    payload = _capture_json(
        logger,
        message="Contexto seguro",
        extra={
            "attempts": 1,
            "latency_ms": 12.5,
            "optional_value": None,
            "event": "stream_authorization_completed",
        },
    )

    assert payload["attempts"] == 1
    assert payload["latency_ms"] == 12.5
    assert payload["optional_value"] is None
    assert payload["event"] == "stream_authorization_completed"
    assert "APP_SECRET" not in payload
    assert "headers" not in payload
    assert "cookies" not in payload
    assert "request" not in payload

    del os.environ["APP_SECRET"]


def test_duplicate_handlers_are_not_added_when_configure_is_called_twice() -> None:
    logger = _reset_logger("tests.logger.duplicate")

    configure_json_logging(service="svc-dup", level=logging.INFO, logger_name="tests.logger.duplicate")
    first_count = len(logger.handlers)

    configure_json_logging(service="svc-dup", level=logging.INFO, logger_name="tests.logger.duplicate")

    assert len(logger.handlers) == first_count
    assert first_count == 1


def test_reserved_log_record_fields_are_not_copied_indiscriminately() -> None:
    logger = _reset_logger("tests.logger.reserved")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter(service="reserved-service"))
    logger.addHandler(handler)

    record = logging.LogRecord(
        name="tests.logger.reserved",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg="Mensagem reservada",
        args=(),
        exc_info=None,
    )
    record.message = "campo incorreto"
    record.levelname = "NOT_INFO"
    record.event = "custom_event"
    record.custom_value = "safe"
    logger.handle(record)
    logger.removeHandler(handler)

    payload = json.loads(stream.getvalue().strip())

    assert payload["message"] == "Mensagem reservada"
    assert "levelname" not in payload
    assert payload["event"] == "custom_event"
    assert payload["custom_value"] == "safe"


def test_service_name_is_taken_from_configuration() -> None:
    logger = _reset_logger("tests.logger.service")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter(service="configured-service"))
    logger.addHandler(handler)

    logger.info("Serviço configurado")
    logger.removeHandler(handler)

    payload = json.loads(stream.getvalue().strip())

    assert payload["service"] == "configured-service"


def test_trace_and_span_ids_are_included_when_span_is_active() -> None:
    logger = _reset_logger("tests.logger.trace")
    configure_tracing(service="tests-logger")
    tracer = trace.get_tracer("tests.logger.trace")

    with tracer.start_as_current_span("span-de-teste") as span:
        payload = _capture_json(logger, message="Mensagem com trace")

    span_context = span.get_span_context()
    assert payload["trace_id"] == f"{span_context.trace_id:032x}"
    assert payload["span_id"] == f"{span_context.span_id:016x}"


def test_exception_info_is_serialized_for_diagnosis() -> None:
    logger = _reset_logger("tests.logger.exception")

    payload = _capture_json(logger, message="Erro de processamento", exc_info=True)

    assert payload["level"] == "ERROR"
    assert "exception" in payload
    assert "ValueError" in payload["exception"]
    assert "validation failed" in payload["exception"]
    assert "secret-value" not in payload["exception"]


def test_configured_logger_uses_selected_level() -> None:
    logger = _reset_logger("tests.logger.level")
    configure_json_logging(service="svc-level", level=logging.WARNING, logger_name="tests.logger.level")

    assert logger.level == logging.WARNING
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0].formatter, JsonFormatter)
