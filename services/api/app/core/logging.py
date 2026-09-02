"""Structured JSON logging with a per-request correlation id.

The request id is stored in a ContextVar so any log line emitted while handling a
request carries it, without threading the id through every function call.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar

import structlog

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def _add_request_id(_logger, _method, event_dict):
    rid = request_id_ctx.get()
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def configure_logging(debug: bool = False) -> None:
    """Configure structlog once at startup. Human-readable in debug, JSON otherwise."""
    renderer = (
        structlog.dev.ConsoleRenderer()
        if debug
        else structlog.processors.JSONRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_request_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "pulse.api"):
    return structlog.get_logger(name)
