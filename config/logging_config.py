"""
日志配置模块
配置系统日志记录方式和格式
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import datetime

# 确保日志目录存在
os.makedirs('data/logs', exist_ok=True)

def setup_logging(level=logging.INFO):
    """设置全局日志配置
    
    Args:
        level: 日志级别，默认为INFO
    """
    # 生成日志文件名，包含日期
    today = datetime.datetime.now().strftime('%Y%m%d')
    log_file = f'data/logs/aiwatchdog_{today}.log'
    
    # 配置根日志记录器
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # 清除现有处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 创建文件处理器(自动轮换)
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 设置特定模块的日志级别
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    return logger

# 默认日志配置，兼容旧代码
LOG_CONFIG = {
    'level': logging.INFO,
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'handlers': [
        {'type': 'file', 'filename': 'data/logs/code.log'},
        {'type': 'stream'}
    ]
}