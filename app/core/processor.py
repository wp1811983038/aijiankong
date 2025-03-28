"""
视频处理器模块
负责视频流的读取、缓冲和分析
"""

import cv2
import asyncio
import logging
import time
import os
import numpy as np
from datetime import datetime
from collections import deque
from typing import Optional

from app.core.analyzer import MultiModalAnalyzer
from app.services.alert_service import AlertService
from config.base import VideoConfig

logger = logging.getLogger(__name__)

class VideoProcessor:
    """视频处理器类，负责视频流的读取和处理"""
    
    def __init__(self, video_source, analyzer=None):
        """初始化视频处理器"""
        self.video_source = video_source
        self.analyzer = analyzer or MultiModalAnalyzer()
        
        # 尝试打开视频源
        logger.info(f"正在打开视频源: {video_source}")
        self.cap = cv2.VideoCapture(video_source)
        if not self.cap.isOpened():
            raise IOError(f"无法打开视频源: {video_source}")
        
        # 读取第一帧以获取视频信息
        for i in range(5):
            ret, frame = self.cap.read()
            if ret:
                break
                
        if not ret or frame is None:
            raise IOError("无法读取视频帧")
            
        # 获取视频属性
        self.width = frame.shape[1]
        self.height = frame.shape[0]
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        
        # 重置视频
        cv2.destroyAllWindows()
        self.cap.release()
        
        # 初始化缓冲区和状态
        self.buffer = deque(maxlen=int(self.fps * VideoConfig.BUFFER_DURATION))
        self.lock = asyncio.Lock()
        self.frame_queue = asyncio.Queue(maxsize=VideoConfig.MAX_WS_QUEUE)
        self.last_analysis = datetime.now().timestamp()
        self._running = False
        self.start_push_queue = 0
        
        # 确保输出目录存在
        os.makedirs('video_warning', exist_ok=True)
        
        logger.info(f"视频处理器初始化完成，FPS: {self.fps}")
    
    async def video_streamer(self, websocket):
        """通过WebSocket流式传输视频帧"""
        try:
            logger.info("开始视频流传输")
            while True:
                frame = await self.frame_queue.get()
                
                # 压缩为JPEG格式
                _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), VideoConfig.JPEG_QUALITY])
                
                # 通过WebSocket发送二进制数据
                await websocket.send_bytes(buffer.tobytes())
        except Exception as e:
            logger.error(f"视频流传输错误: {str(e)}")
        finally:
            logger.info("视频流传输停止")
            self.start_push_queue = 0
    
    async def frame_generator(self):
        """异步视频帧生成器"""
        count = 0
        self.cap = cv2.VideoCapture(self.video_source)
        
        while self._running:
            start_time = time.monotonic()
            
            ret, frame = self.cap.read()
            count += 1
            
            if not ret:
                logger.error("视频流中断，尝试重新连接...")
                break
            
            # 处理帧
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                
            # 添加到缓冲区
            self.buffer.append({
                "frame": frame,
                "timestamp": datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            })
            
            # 如果启用，将帧添加到队列
            if self.start_push_queue:
                await self.frame_queue.put(frame)
            
            # 定时触发分析
            if (datetime.now().timestamp() - self.last_analysis) >= VideoConfig.ANALYSIS_INTERVAL and count >= self.fps * VideoConfig.ANALYSIS_INTERVAL:
                logger.info(f"触发分析，已处理 {count} 帧")
                asyncio.create_task(self.trigger_analysis())
                self.last_analysis = datetime.now().timestamp()
                count = 0
            
            # 控制帧生成速度
            elapsed = time.monotonic() - start_time
            await asyncio.sleep(max(0, 1/self.fps - elapsed))
        
        # 视频流中断，尝试重新连接
        await self._reconnect()
    
    async def _reconnect(self):
        """视频流重连逻辑"""
        await asyncio.sleep(VideoConfig.WS_RETRY_INTERVAL)
        self.cap.release()
        self.cap = cv2.VideoCapture(self.video_source)
        ret, frame = self.cap.read()
        if ret:
            logger.info("视频流重新连接成功")
            await self.start_processing()
    
    async def trigger_analysis(self):
        """触发异步视频分析"""
        try:
            async with self.lock:
                clip = list(self.buffer)
                if not clip:
                    logger.warning("缓冲区为空，跳过分析")
                    return
                
                logger.info(f"开始分析视频片段，包含 {len(clip)} 帧")
                
                # 最多重试两次
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        result = await self.analyzer.analyze(
                            [f["frame"] for f in clip], 
                            self.fps, 
                            (clip[0]['timestamp'], clip[-1]['timestamp'])
                        )
                        
                        # 如果检测到异常，触发预警
                        if result.get("alert") != "无异常":
                            logger.warning(f"检测到异常: {result.get('alert')}")
                            await AlertService.notify(result)
                            
                        break
                    except Exception as e:
                        logger.error(f"分析尝试 {attempt+1}/{max_retries} 失败: {str(e)}")
                        if attempt == max_retries - 1:
                            logger.error("达到最大尝试次数，分析失败")
                        # 等待后重试
                        await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"分析失败: {str(e)}")
    
    async def start_processing(self):
        """启动视频处理流水线"""
        self._running = True
        logger.info("启动视频处理")
        await self.frame_generator()
    
    async def stop_processing(self):
        """停止视频处理"""
        self._running = False
        logger.info("停止视频处理")
        # 释放资源
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()