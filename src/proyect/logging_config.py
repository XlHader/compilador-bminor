from pathlib import Path

from loguru import logger


def configure_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    _ = logger.add(log_dir / "app.log", rotation="5 MB", retention="7 days")
