"""
基础配置模块
包含视频监控系统的所有可配置参数
"""

import os
import logging
from typing import Dict, Any
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 如果没有安装python-dotenv，就跳过

# 视频处理配置
class VideoConfig:
    # 视频源
    VIDEO_SOURCE = os.getenv('VIDEO_SOURCE', r'data\测试视频\1.mp4')
    
    # 视频分段与分析
    VIDEO_INTERVAL = int(os.getenv('VIDEO_INTERVAL', '1800'))  # 视频分段时长(秒)
    ANALYSIS_INTERVAL = int(os.getenv('ANALYSIS_INTERVAL', '10'))  # 分析间隔(秒)
    BUFFER_DURATION = int(os.getenv('BUFFER_DURATION', '11'))  # 滑窗分析时长
    
    # WebSocket相关
    WS_RETRY_INTERVAL = int(os.getenv('WS_RETRY_INTERVAL', '3'))  # WebSocket重连间隔(秒)
    MAX_WS_QUEUE = int(os.getenv('MAX_WS_QUEUE', '100'))  # 消息队列最大容量
    
    # 视频质量
    JPEG_QUALITY = int(os.getenv('JPEG_QUALITY', '70'))  # JPEG压缩质量

# 通义千问配置（视频分析）
class QwenConfig:
    API_KEY = os.getenv('QWEN_API_KEY', "")
    API_URL = os.getenv('QWEN_API_URL', "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
    MODEL = os.getenv('QWEN_MODEL', "qwen-vl-plus")
    USE_OLLAMA = os.getenv('QWEN_USE_OLLAMA', 'False').lower() in ('true', '1', 't')
    REQUEST_TIMEOUT = float(os.getenv('QWEN_REQUEST_TIMEOUT', '60.0'))  # 请求超时时间（秒）

# Moonshot配置（文本分析）
class MoonshotConfig:
    API_KEY = os.getenv('MOONSHOT_API_KEY', "")
    API_URL = os.getenv('MOONSHOT_API_URL', "https://api.moonshot.cn/v1/chat/completions")
    MODEL = os.getenv('MOONSHOT_MODEL', "moonshot-v1-8k")
    USE_OLLAMA = os.getenv('MOONSHOT_USE_OLLAMA', 'False').lower() in ('true', '1', 't')
    REQUEST_TIMEOUT = float(os.getenv('MOONSHOT_REQUEST_TIMEOUT', '30.0'))  # 请求超时时间（秒）
    TEMPERATURE = float(os.getenv('TEMPERATURE', '0.5'))  # 温度
    TOP_P = float(os.getenv('TOP_P', '0.01'))
    TOP_K = int(os.getenv('TOP_K', '20'))
    REPETITION_PENALTY = float(os.getenv('REPETITION_PENALTY', '1.05'))

# Ollama配置
class OllamaConfig:
    OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434/api')
    QWEN_MODEL = os.getenv('OLLAMA_QWEN_MODEL', 'llama3')  # 视频分析模型
    MOONSHOT_MODEL = os.getenv('OLLAMA_MOONSHOT_MODEL', 'llama3')  # 文本分析模型
    TIMEOUT = float(os.getenv('OLLAMA_TIMEOUT', '30.0'))  # 超时时间

# RAG系统配置
class RAGConfig:
    # 知识库配置
    ENABLE_RAG = os.getenv('ENABLE_RAG', 'False').lower() in ('true', '1', 't')
    VECTOR_API_URL = os.getenv('VECTOR_API_URL', "http://localhost:8085/add_text/")
    HISTORY_FILE = os.getenv('HISTORY_FILE', "video_histroy_info.txt")

# 存档配置
ARCHIVE_DIR = os.getenv('ARCHIVE_DIR', "archive")

# 服务器配置
class ServerConfig:
    HOST = os.getenv('HOST', "0.0.0.0")
    PORT = int(os.getenv('PORT', '16532'))
    RELOAD = os.getenv('RELOAD', 'True').lower() in ('true', '1', 't')
    WORKERS = int(os.getenv('WORKERS', '1'))

# 日志配置
LOG_CONFIG = {
    'level': logging.INFO,
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'handlers': [
        {'type': 'file', 'filename': 'data/logs/code.log'},
        {'type': 'stream'}
    ]
}

def update_config(args: Dict[str, Any]) -> None:
    """使用命令行参数更新配置
    
    Args:
        args: 包含命令行参数的字典
    """
    # 更新视频源
    if args.get('video_source'):
        VideoConfig.VIDEO_SOURCE = args['video_source']
    
    # 更新视频处理配置
    for key in ['video_interval', 'analysis_interval', 'buffer_duration',
               'ws_retry_interval', 'max_ws_queue', 'jpeg_quality']:
        if key in args:
            setattr(VideoConfig, key.upper(), args[key])
    
    # 更新服务器配置
    for key in ['host', 'port', 'reload', 'workers']:
        if key in args:
            setattr(ServerConfig, key.upper(), args[key])
            
    # 更新通义千问配置
    for key in ['qwen_api_key', 'qwen_api_url', 'qwen_model', 'qwen_request_timeout']:
        if key in args:
            attr_name = key.replace('qwen_', '').upper()
            setattr(QwenConfig, attr_name, args[key])
    
    # 更新Moonshot配置
    for key in ['moonshot_api_key', 'moonshot_api_url', 'moonshot_model', 
               'moonshot_request_timeout', 'temperature', 'top_p', 'top_k',
               'repetition_penalty']:
        if key in args:
            attr_name = key.replace('moonshot_', '').upper()
            setattr(MoonshotConfig, attr_name, args[key])
            
    # 更新Ollama配置
    for key in ['ollama_api_url', 'ollama_qwen_model', 'ollama_moonshot_model', 'ollama_timeout']:
        if key in args:
            attr_name = key.replace('ollama_', '').upper()
            setattr(OllamaConfig, attr_name, args[key])
            
    # 更新AI服务模式配置
    if 'qwen_use_ollama' in args:
        value = args['qwen_use_ollama']
        if isinstance(value, str):
            value = value.lower() in ('true', '1', 't')
        QwenConfig.USE_OLLAMA = value
        
    if 'moonshot_use_ollama' in args:
        value = args['moonshot_use_ollama']
        if isinstance(value, str):
            value = value.lower() in ('true', '1', 't')
        MoonshotConfig.USE_OLLAMA = value
            
    # 更新RAG配置
    for key in ['enable_rag', 'vector_api_url', 'history_file']:
        if key in args:
            setattr(RAGConfig, key.upper(), args[key])