"""
日志系统配置
使用 loguru 进行结构化日志记录
"""

from loguru import logger
import sys
from pathlib import Path
from typing import Dict, Any


def setup_logging(config: Dict[str, Any]):
    """
    配置日志系统
    
    Args:
        config: 日志配置字典
    """
    # 移除默认的 handler
    logger.remove()
    
    # 控制台输出（彩色，简洁格式）
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=config.get('console_level', 'INFO'),
        colorize=True,
        backtrace=False,
        diagnose=False
    )
    
    # 确保日志目录存在
    log_file = config.get('file', 'logs/monitor.log')
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # 文件输出（详细格式）
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level=config.get('level', 'DEBUG'),
        rotation=config.get('rotation', '100 MB'),
        retention=config.get('retention', '7 days'),
        compression=config.get('compression', 'zip'),
        backtrace=True,
        diagnose=True
    )
    
    # 错误日志单独文件
    error_file = config.get('error_file', 'logs/errors.log')
    Path(error_file).parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        error_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}\\n{exception}",
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        backtrace=True,
        diagnose=True
    )
    
    logger.info("日志系统初始化完成")
