import logging
import os
from datetime import datetime
from typing import Optional


def setup_logger(log_level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """
    Configure the logging system for the application.
    
    Args:
        log_level: The minimum log level to capture
        log_file: Optional path to a log file. If None, logs will only go to console.
    
    Returns:
        A configured logger instance
    """
    # Create logger
    logger = logging.getLogger("rufus")
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if a log file is specified
    if log_file:
        # Ensure the log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Create a default logger instance
logger = setup_logger()
