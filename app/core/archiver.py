"""
视频存档模块
负责保存和管理视频存档
"""

import cv2
import os
import logging
from datetime import datetime
import numpy as np

from config.base import VideoConfig, ARCHIVE_DIR

logger = logging.getLogger(__name__)

class VideoArchiver:
    """视频存档管理类"""
    
    def __init__(self, width, height, fps):
        """初始化视频存档管理器"""
        self.width = width
        self.height = height
        self.fps = fps
        self.current_writer = None
        self.last_split = datetime.now()
        
        # 确保存档目录存在
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        
        logger.info(f"视频存档管理器初始化完成")
    
    async def write_frame(self, frame):
        """异步写入视频帧"""
        # 检查是否需要分割视频文件
        if self._should_split():
            self._create_new_file()
        
        # 写入帧
        if self.current_writer is not None:
            try:
                # 确保帧格式正确
                if frame.dtype != np.uint8:
                    frame = frame.astype(np.uint8)
                if len(frame.shape) == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                
                self.current_writer.write(frame)
            except Exception as e:
                logger.error(f"写入视频帧失败: {str(e)}")
    
    def _should_split(self):
        """检查是否应该分割视频文件"""
        return (datetime.now() - self.last_split).total_seconds() >= VideoConfig.VIDEO_INTERVAL
    
    def _create_new_file(self):
        """创建新的视频文件"""
        # 释放当前写入器
        if self.current_writer is not None:
            self.current_writer.release()
        
        # 创建新文件
        filename = f"{ARCHIVE_DIR}/{datetime.now().strftime('%Y%m%d_%H%M')}.mp4"
        
        # 尝试不同的编解码器
        for codec in ['mp4v', 'avc1', 'XVID']:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                writer = cv2.VideoWriter(filename, fourcc, self.fps, (self.width, self.height))
                
                if writer.isOpened():
                    self.current_writer = writer
                    self.last_split = datetime.now()
                    logger.info(f"使用编解码器 {codec} 创建视频文件: {filename}")
                    return
                else:
                    writer.release()
            except Exception as e:
                logger.warning(f"尝试编解码器 {codec} 失败: {str(e)}")
        
        logger.error("所有编解码器都失败，无法创建视频文件")