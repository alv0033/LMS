# app/core/logging.py
import json
import logging
from logging import Logger
from typing import Any, Dict, Optional
from contextvars import ContextVar
from .config import settings


# Contexto por request / usuario, usado en dependencies_auth y middleware
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[Optional[int]] = ContextVar("user_id", default=None)


class JsonFormatter(logging.Formatter):
    """
    Formatea los logs como JSON estructurado.

    Respeta los campos extra que pases en `logger.info(..., extra={...})`,
    por eso es compatible con lo que ya estás usando:
    - operation
    - resource
    - user_id
    - loan_id, branch_id, book_id, etc.
    """

    def format(self, record: logging.LogRecord) -> str:
        log: Dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Agregar todos los atributos extra del record
        skip = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        }

        for key, value in record.__dict__.items():
            if key not in skip and key not in log:
                # Solo añadir campos "interesantes" que vengas pasando en `extra=`
                log[key] = value

        # Inyectar request_id y user_id desde el contexto, si existen
        req_id = request_id_ctx.get()
        if req_id is not None and "request_id" not in log:
            log["request_id"] = req_id

        uid = user_id_ctx.get()
        if uid is not None and "user_id" not in log:
            log["user_id"] = uid
            

        # Si hay excepción, serializarla también
        if record.exc_info:
            log["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log, ensure_ascii=False)


def configure_logging() -> None:
    """
    Configura el logging global de la app para usar JSON estructurado.

    Se llama una vez al inicio de la aplicación.
    """
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())

    # Limpia handlers anteriores (por si algo más configuró logging)
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler()
    formatter = JsonFormatter()
    handler.setFormatter(formatter)
    root.addHandler(handler)


def get_logger(name: str) -> Logger:
    """
    Helper para obtener loggers en tu código.
    Ejemplo:
        logger = get_logger("api.loans")
    """
    return logging.getLogger(name)
