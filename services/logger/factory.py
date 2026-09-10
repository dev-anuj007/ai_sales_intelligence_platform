"""Factory for creating logger instances based on configuration."""

from typing import Literal
from fastapi import Depends

from services.logger.abstractions import Logger
from services.logger.implementations.logfire_logger import LogfireLogger
from services.logger.implementations.stdlib_logger import StdlibLogger
from services.logger.implementations.noop_logger import NoopLogger


def create_logger(backend: Literal["logfire", "stdlib", "noop"]) -> Logger:
    """Create logger instance for specified backend."""
    if backend == "logfire":
        return LogfireLogger()
    elif backend == "stdlib":
        return StdlibLogger()
    else:
        return NoopLogger()


def get_logger() -> Logger:
    """Dependency injection function for FastAPI.

    Returns logger instance configured via settings.
    """
    from config import settings

    backend: Literal["logfire", "stdlib", "noop"]
    if settings.log_backend == "logfire":
        backend = "logfire"
    elif settings.log_backend == "stdlib":
        backend = "stdlib"
    else:
        backend = "noop"
    return create_logger(backend)


def get_logger_sync() -> Logger:
    """Synchronous getter for use outside of FastAPI context."""
    from config import settings

    backend: Literal["logfire", "stdlib", "noop"]
    if settings.log_backend == "logfire":
        backend = "logfire"
    elif settings.log_backend == "stdlib":
        backend = "stdlib"
    else:
        backend = "noop"
    return create_logger(backend)
