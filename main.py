"""
智能视频监控预警系统
主应用入口点
"""

import os
import sys
import logging
import argparse
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入应用模块
from app.api.routes import create_app, register_processor
from app.core.processor import VideoProcessor
from app.core.analyzer import MultiModalAnalyzer
from app.services.alert_service import AlertService
from config.base import VideoConfig, ServerConfig, update_config, LOG_CONFIG

# 配置日志
logging.basicConfig(
    level=LOG_CONFIG['level'],
    format=LOG_CONFIG['format'],
    handlers=[
        logging.FileHandler(LOG_CONFIG['handlers'][0]['filename'], encoding='utf-8'), 
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 全局变量存储应用实例和处理器
processor = None
alert_service = None

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='智能视频监控系统')
    parser.add_argument('--video_source', type=str, help='视频源路径')
    parser.add_argument('--video_interval', type=int, help='视频分段时长(秒)')
    parser.add_argument('--analysis_interval', type=int, help='分析间隔(秒)')
    parser.add_argument('--buffer_duration', type=int, help='滑窗分析时长')
    parser.add_argument('--host', type=str, help='服务器主机地址')
    parser.add_argument('--port', type=int, help='服务器端口')
    parser.add_argument('--reload', type=bool, help='是否启用热重载')
    parser.add_argument('--workers', type=int, help='工作进程数')
    
    args = parser.parse_args()
    return {k: v for k, v in vars(args).items() if v is not None}

async def startup(app):
    """应用启动初始化"""
    global processor
    # 创建必要的目录
    os.makedirs('data/video_warning', exist_ok=True)
    os.makedirs('data/archive', exist_ok=True)
    os.makedirs('data/logs', exist_ok=True)
    os.makedirs('data/测试视频', exist_ok=True)
    
    # 保存处理器实例，方便API访问
    app.state.processor = processor
    
    # 启动视频处理
    if processor and not processor._running:
        asyncio.create_task(processor.start_processing())
    
    logger.info("应用初始化完成")

async def shutdown(app):
    """应用关闭时的清理"""
    global processor
    if processor:
        await processor.stop_processing()
    logger.info("应用已关闭")

@asynccontextmanager
async def lifespan(app):
    """应用生命周期管理"""
    # 启动事件
    await startup(app)
    yield
    # 关闭事件
    await shutdown(app)

def init_components():
    """初始化系统组件"""
    global processor, alert_service
    try:
        # 初始化组件
        logger.info("正在初始化系统组件...")
        analyzer = MultiModalAnalyzer()
        processor = VideoProcessor(VideoConfig.VIDEO_SOURCE, analyzer)
        alert_service = AlertService()
        
        # 确保前端资源目录存在
        os.makedirs('frontend/assets', exist_ok=True)
        
        # 创建占位图像，如果不存在
        placeholder_path = 'frontend/assets/placeholder.jpg'
        if not os.path.exists(placeholder_path):
            import cv2
            import numpy as np
            # 创建一个黑色图像
            img = np.zeros((360, 640, 3), np.uint8)
            # 添加文字
            cv2.putText(img, 'No Video Signal', (180, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            # 保存图像
            cv2.imwrite(placeholder_path, img)
        
        return True
        
    except Exception as e:
        logger.critical(f"初始化组件时出错: {str(e)}", exc_info=True)
        return False

def create_and_get_app():
    """创建并返回应用实例，供uvicorn导入使用"""
    # 解析命令行参数并更新配置
    args = parse_args()
    update_config(args)
    
    # 初始化组件
    if not init_components():
        sys.exit(1)
    
    # 创建FastAPI应用
    app = create_app(processor, alert_service)
    
    # 设置lifespan
    app.router.lifespan_context = lifespan
    
    return app

def main():
    """主函数"""
    # 创建应用
    app = create_and_get_app()
    
    # 运行服务器
    logger.info(f"启动服务器: {ServerConfig.HOST}:{ServerConfig.PORT}")
    import uvicorn
    uvicorn.run(
        app=app,
        host=ServerConfig.HOST,
        port=ServerConfig.PORT
    )

if __name__ == "__main__":
    # 直接运行不使用热重载
    main()