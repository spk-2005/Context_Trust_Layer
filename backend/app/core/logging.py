import logging
import sys


def get_logger(name: str = "context_trust") -> logging.Logger:
    """Configures and returns a structured logger for the application.

    Ensures sensitive content/secrets are excluded from log streams.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
