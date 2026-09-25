"""
Logs estruturados com structlog.
"""
import structlog
import logging
from app.core.config import settings


def configure_logging():
    """Configura logs estruturados para a aplicacao."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer() if settings.debug
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(level=log_level)


def get_logger(name: str = __name__):
    return structlog.get_logger(name)
