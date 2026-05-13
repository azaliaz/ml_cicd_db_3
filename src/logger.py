import logging
import os
import sys
from pathlib import Path

FORMATTER = logging.Formatter(
    "%(asctime)s — %(name)s — %(levelname)s — %(message)s"
)
LOG_FILE = str(Path(__file__).resolve().parent.parent / "logfile.log")


class Logger:
    def __init__(self, show: bool) -> None:
        self.show = show

    def get_console_handler(self) -> logging.StreamHandler:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(FORMATTER)
        return console_handler

    def get_file_handler(self) -> logging.FileHandler:
        Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
        file_handler.setFormatter(FORMATTER)
        return file_handler

    def get_logger(self, logger_name: str):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            if self.show:
                logger.addHandler(self.get_console_handler())
            logger.addHandler(self.get_file_handler())
        logger.propagate = False
        return logger


def show_logs_from_env() -> bool:
    return os.environ.get("SHOW_LOG", "true").lower() in ("1", "true", "yes")
