"""
API路由和WebSocket处理
"""

import logging
import asyncio
import os
import shutil
import glob
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocketState

from app.core.processor import VideoProcessor
from app.services.alert_service import AlertService
from config.base import MoonshotConfig, OllamaConfig, QwenConfig, VideoConfig, ServerConfig, update_config

logger = logging.getLogger(__name__)

# 全局变量，存储处理器实例
_processor: Optional[VideoProcessor] = None

def register_processor(processor: VideoProcessor):
    """注册处理器实例"""
    global _processor
    _processor = processor

def create_app(processor: VideoProcessor = None, alert_service: AlertService = None) -> FastAPI:
    """创建FastAPI应用实例"""
    app = FastAPI(title="智能视频监控预警系统")
    
    # 挂载静态文件
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
    app.mount("/video_warning", StaticFiles(directory="video_warning"), name="video_warning")
    
    # 注册处理器实例
    global _processor
    _processor = processor
    
    @app.get("/", response_class=HTMLResponse)
    async def get_index():
        """返回前端首页"""
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return f.read()
    
    @app.websocket("/alerts")
    async def alert_websocket(websocket: WebSocket):
        """预警消息WebSocket"""
        await alert_service.register(websocket)
        try:
            while True:
                # 维持连接活跃
                await websocket.receive_text()
        except WebSocketDisconnect:
            logger.info("客户端断开预警WebSocket连接")
        finally:
            alert_service.remove(websocket)
    
    @app.websocket("/video_feed")
    async def video_feed(websocket: WebSocket):
        """视频流WebSocket"""
        try:
            await websocket.accept()
            logger.info("客户端连接到视频流WebSocket")
            
            # 启用视频推送
            processor.start_push_queue = 1
            
            # 开始流式传输视频
            await processor.video_streamer(websocket)
        except WebSocketDisconnect:
            logger.info("客户端断开视频流WebSocket连接")
        except Exception as e:
            logger.error(f"视频流WebSocket错误: {str(e)}")
        finally:
            # 禁用视频推送并清空队列
            processor.start_push_queue = 0
            processor.frame_queue = asyncio.Queue(maxsize=VideoConfig.MAX_WS_QUEUE)
    
    @app.get("/api/settings")
    async def get_settings():
        """获取当前系统设置"""
        return {
            "video_source": VideoConfig.VIDEO_SOURCE,
            "analysis_interval": VideoConfig.ANALYSIS_INTERVAL,
            "buffer_duration": VideoConfig.BUFFER_DURATION,
            "jpeg_quality": VideoConfig.JPEG_QUALITY
        }
    
    @app.post("/api/settings")
    async def update_settings(settings: Dict[str, Any]):
        """更新系统设置"""
        global _processor
        
        try:
            # 更新配置
            update_config(settings)
            
            # 记录配置更改
            logger.info(f"系统设置已更新: {settings}")
            
            # 如果处理器正在运行，重启它
            if _processor and _processor._running:
                logger.info("重启视频处理器以应用新设置")
                await _processor.stop_processing()
                # 短暂等待确保资源释放
                await asyncio.sleep(1)
                await _processor.start_processing()
            
            return {"status": "success", "message": "设置已更新"}
            
        except Exception as e:
            logger.error(f"更新设置失败: {str(e)}")
            return {"status": "error", "message": f"更新设置失败: {str(e)}"}
    
    @app.get("/api/videos")
    async def list_videos():
        """列出可用的视频文件"""
        video_files = []
        
        # 搜索视频目录
        video_dirs = ["测试视频", "videos", "video_samples"]
        
        for dir_name in video_dirs:
            if os.path.exists(dir_name):
                # 查找常见视频格式
                for ext in ["*.mp4", "*.avi", "*.mkv", "*.mov"]:
                    files = glob.glob(f"{dir_name}/{ext}")
                    video_files.extend(files)
        
        return {"videos": video_files}
    
    @app.post("/api/upload")
    async def upload_video(file: UploadFile = File(...)):
        """上传视频文件"""
        try:
            # 确保目录存在
            os.makedirs("测试视频", exist_ok=True)
            
            # 验证文件类型
            valid_extensions = ['.mp4', '.avi', '.mkv', '.mov']
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext not in valid_extensions:
                raise HTTPException(status_code=400, detail="不支持的文件类型，请上传MP4、AVI、MKV或MOV格式的视频")
            
            # 保存文件
            file_path = f"测试视频/{file.filename}"
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            logger.info(f"视频文件已上传: {file_path}")
            
            return {"status": "success", "file_path": file_path}
            
        except HTTPException as e:
            logger.warning(f"上传视频失败: {e.detail}")
            return {"status": "error", "message": e.detail}
            
        except Exception as e:
            logger.error(f"上传视频失败: {str(e)}")
            return {"status": "error", "message": f"上传视频失败: {str(e)}"}
    
    @app.get("/api/health")
    async def health_check():
        """健康检查端点"""
        return {
            "status": "ok", 
            "version": "1.0.0",
            "processor_running": _processor._running if _processor else False
            
        }
    

    @app.get("/api/settings")
    async def get_settings():
        """获取当前系统设置"""
        return {
            "video_source": VideoConfig.VIDEO_SOURCE,
            "analysis_interval": VideoConfig.ANALYSIS_INTERVAL,
            "buffer_duration": VideoConfig.BUFFER_DURATION,
            "jpeg_quality": VideoConfig.JPEG_QUALITY,
            "enable_ollama": OllamaConfig.ENABLE_OLLAMA,
            "ollama_model": OllamaConfig.OLLAMA_MODEL,
            "ollama_api_url": OllamaConfig.OLLAMA_API_URL
        }
    @app.post("/api/switch-model")
    async def switch_model(settings: Dict[str, Any]):
        """切换AI服务模式（远程API或本地Ollama）"""
        try:
            # 设置通义千问
            if "qwen_use_ollama" in settings:
                QwenConfig.USE_OLLAMA = settings["qwen_use_ollama"]
                
            # 设置Moonshot
            if "moonshot_use_ollama" in settings:
                MoonshotConfig.USE_OLLAMA = settings["moonshot_use_ollama"]
                
            # 如果需要，更新Ollama模型名称
            if "ollama_qwen_model" in settings and settings["ollama_qwen_model"]:
                OllamaConfig.QWEN_MODEL = settings["ollama_qwen_model"]
                
            if "ollama_moonshot_model" in settings and settings["ollama_moonshot_model"]:
                OllamaConfig.MOONSHOT_MODEL = settings["ollama_moonshot_model"]
                
            # 记录变更
            logger.info(f"AI服务模式已切换: 通义千问使用Ollama = {QwenConfig.USE_OLLAMA}, 模型 = {OllamaConfig.QWEN_MODEL}")
            logger.info(f"AI服务模式已切换: Moonshot使用Ollama = {MoonshotConfig.USE_OLLAMA}, 模型 = {OllamaConfig.MOONSHOT_MODEL}")
            
            # 返回结果
            return {
                "status": "success",
                "message": "AI服务模式已成功切换",
                "qwen_use_ollama": QwenConfig.USE_OLLAMA,
                "moonshot_use_ollama": MoonshotConfig.USE_OLLAMA,
                "ollama_qwen_model": OllamaConfig.QWEN_MODEL,
                "ollama_moonshot_model": OllamaConfig.MOONSHOT_MODEL
            }
                
        except Exception as e:
            logger.error(f"切换AI服务模式失败: {str(e)}")
            return {"status": "error", "message": f"切换失败: {str(e)}"}
    
    return app



