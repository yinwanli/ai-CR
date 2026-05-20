import sys
import os
from loguru import logger

# 移除默认处理器
logger.remove()

# 获取日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 控制台输出格式
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 文件输出格式
FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)

# 添加控制台处理器
logger.add(
    sys.stdout,
    format=CONSOLE_FORMAT,
    level="DEBUG",
    colorize=True
)

# 添加文件处理器
logger.add(
    os.path.join(LOG_DIR, "app_{time:YYYY-MM-DD}.log"),
    format=FILE_FORMAT,
    level="DEBUG",
    rotation="00:00",
    retention="7 days",
    encoding="utf-8"
)

# 添加错误日志文件
logger.add(
    os.path.join(LOG_DIR, "error_{time:YYYY-MM-DD}.log"),
    format=FILE_FORMAT,
    level="ERROR",
    rotation="00:00",
    retention="30 days",
    encoding="utf-8"
)

def get_logger(name: str = None):
    """获取logger实例"""
    if name:
        return logger.bind(name=name)
    return logger
