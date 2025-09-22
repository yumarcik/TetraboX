import logging

_LOG_FORMAT = "[%(levelname)s] %(asctime)s %(name)s - %(message)s"

def get_logger(name: str = "tetrabox"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(h)
    return logger

__all__ = ["get_logger"]
