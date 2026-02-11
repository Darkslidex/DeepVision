import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name="DeepVision", log_file="deepvision.log", level=logging.INFO):
    """
    Sets up a centralized logger with console and file handlers.
    """
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
    handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    
    return logger
