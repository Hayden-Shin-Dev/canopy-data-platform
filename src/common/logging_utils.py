"""파이프라인에서 공통으로 사용하는 간단한 로깅 설정."""

from __future__ import annotations

import logging
import sys


LOGGER_NAME = "canopy"


def configure_logging(level: int | str = logging.INFO) -> logging.Logger:
    """콘솔 핸들러를 하나만 붙이고 Canopy 로거를 반환한다."""

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    # 파이프라인을 여러 번 호출해도 같은 핸들러가 중복으로 쌓이지 않게 한다.
    if not any(getattr(handler, "_canopy_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler._canopy_handler = True  # type: ignore[attr-defined]
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        logger.addHandler(handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """도메인 모듈에서 사용할 하위 로거를 반환한다."""

    return logging.getLogger(f"{LOGGER_NAME}.{name}" if name else LOGGER_NAME)

