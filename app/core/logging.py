import logging
import sys
from loguru import logger
from app.core.config import settings
import json
from datetime import datetime

class InterceptHandler(logging.Handler):
    """Intercept standard logging and redirect to loguru"""
    
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

def setup_logging():
    """Configure logging for production"""
    
    # Remove default handler
    logger.remove()
    
    # Add JSON formatter for production, pretty for development
    if settings.ENVIRONMENT == "production":
        logger.add(
            sys.stdout,
            format=lambda record: json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "level": record["level"].name,
                "message": record["message"],
                "module": record["module"],
                "function": record["function"],
                "line": record["line"],
                **record.get("extra", {})
            }),
            level=settings.LOG_LEVEL,
            serialize=True
        )
    else:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG",
            colorize=True
        )
    
    # Add file rotation for error logs
    logger.add(
        "logs/error_{time:YYYY-MM-DD}.log",
        level="ERROR",
        rotation="1 day",
        retention="30 days",
        compression="gz"
    )
    
    logger.add(
        "logs/info_{time:YYYY-MM-DD}.log",
        level="INFO",
        rotation="1 day",
        retention="7 days",
        compression="gz"
    )
    
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    
    # Set specific loggers
    for log_name in ["uvicorn", "uvicorn.access", "fastapi"]:
        logging.getLogger(log_name).handlers = [InterceptHandler()]
    
    logger.info(f"Logging configured for {settings.ENVIRONMENT} environment")
    
    return logger

# Export logger instance
app_logger = setup_logging()