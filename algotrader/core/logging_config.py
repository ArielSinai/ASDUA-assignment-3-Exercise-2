from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(
    *,
    level: int = logging.INFO,
    log_file: str = "algotrader.log",
    logger_name: str = "algotrader",
) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    if getattr(logger, "_configured", False):
        return logger

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    stream = logging.StreamHandler()
    stream.setLevel(level)
    stream.setFormatter(fmt)

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)

    logger.addHandler(stream)
    logger.addHandler(file_handler)
    logger.propagate = False

    setattr(logger, "_configured", True)
    return logger
