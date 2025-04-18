"""
Logging system for HTTPy.

This module provides a centralized logging configuration for the HTTPy server.
It defines custom loggers, handlers, and formatters to ensure consistent
logging across the application.
"""

import logging
import sys
import os
from typing import Optional, Dict, Any, Union

# Default log format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Logger instances cache
_loggers: Dict[str, logging.Logger] = {}

def get_logger(name: str = "httpy") -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: The name of the logger (default: "httpy")
        
    Returns:
        A configured logger instance
    """
    if name in _loggers:
        return _loggers[name]
    
    logger = logging.getLogger(name)
    
    # Only configure the logger if it hasn't been configured yet
    if not logger.handlers:
        # Set default level
        logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(DEFAULT_FORMAT)
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
    
    _loggers[name] = logger
    return logger

def configure_logging(
    level: Union[int, str] = logging.INFO,
    format_str: str = DEFAULT_FORMAT,
    log_file: Optional[str] = None,
    log_to_console: bool = True
) -> None:
    """
    Configure the logging system.
    
    Args:
        level: The logging level (default: INFO)
        format_str: The log format string (default: DEFAULT_FORMAT)
        log_file: Optional path to a log file
        log_to_console: Whether to log to console (default: True)
    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(format_str)
    
    # Add console handler if requested
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Add file handler if requested
    if log_file:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Update all cached loggers
    for name, logger in _loggers.items():
        logger.setLevel(level)

# Initialize default logger
logger = get_logger()