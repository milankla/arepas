"""
Centralized logging configuration for the Arepas project.
"""

import sys
import os
from loguru import logger

def setup_logging(level="INFO", log_to_file=False, log_file="arepas.log"):
    """Configure logging for the entire application."""
    logger.remove()
    
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    if log_to_file:
        logger.add(log_file, level=level, format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}")

PRESETS = {
    "quiet": {"level": "WARNING", "description": "Only warnings and errors"},
    "normal": {"level": "INFO", "description": "Standard informational messages"},
    "verbose": {"level": "DEBUG", "description": "Detailed debugging information"},
    "trace": {"level": "TRACE", "description": "Maximum verbosity"}
}

def use_preset(preset_name="normal", log_to_file=False):
    """Use a predefined logging configuration."""
    if preset_name not in PRESETS:
        preset_name = "normal"
    
    config = PRESETS[preset_name]
    setup_logging(config["level"], log_to_file=log_to_file)
