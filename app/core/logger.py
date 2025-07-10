# app/core/logger.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
ENV = os.getenv("ENV", "development")

# Ensure logs directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Formatters
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

# Configure sys.stdout to use UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(LOG_LEVEL)
console_handler.setFormatter(formatter)

# File handler with rotation
file_handler = RotatingFileHandler(
    filename=LOG_FILE,
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=3
)
file_handler.setLevel(LOG_LEVEL)
file_handler.setFormatter(formatter)

# Base logger configuration
logger = logging.getLogger("emma")
logger.setLevel(LOG_LEVEL)
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.propagate = False

def get_module_logger(name: str) -> logging.Logger:
    module_logger = logging.getLogger(name)
    module_logger.setLevel(LOG_LEVEL)
    if not module_logger.handlers:
        module_logger.addHandler(console_handler)
        module_logger.addHandler(file_handler)
    return module_logger