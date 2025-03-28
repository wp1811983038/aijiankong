"""
视频处理工具函数
"""

import base64
import httpx
import requests
import cv2 
import logging
import os
import numpy as np

from config.base import APIConfig, RAGConfig, VideoConfig

logger = logging.getLogger(__name__)

def frames_to_base64(frames, fps, timestamps=None):
    """将视频帧转换为base64编码的视频"""
    try:
        logger.info(f"处理 {len(frames)} 帧，帧率 {fps}")
        
        # 确保输出目录存在
        output_dir = './video_warning'
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'output.mp4')
        
        # 如果已存在同名文件，先删除
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
                logger.info(f"删除已存在的视频文件: {output_path}")
            except OSError as e:
                logger.warning(f"无法删除已存在的视频文件: {e}")
        
        width = frames[0].shape[1]
        height = frames[0].shape[0]    
        
        # 尝试多种编解码器
        codecs = ['mp4v', 'avc1', 'XVID']
        video_writer = None
        
        for codec in codecs:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                
                if video_writer.isOpened():
                    logger.info(f"使用编解码器 {codec} 创建视频写入器成功")
                    break
                else:
                    video_writer.release()
            except Exception as e:
                logger.warning(f"尝试编解码器 {codec} 失败: {str(e)}")
        
        if video_writer is None or not video_writer.isOpened():
            logger.error("所有编解码器都失败，无法创建视频")
            return ""
        
        # 写入视频帧
        frames_written = 0
        for frame in frames:
            # 确保帧是正确的数据类型和形状
            frame_copy = frame.copy()  # 创建副本以避免修改原始数据
            if frame_copy.dtype != np.uint8:
                frame_copy = frame_copy.astype(np.uint8)
            if len(frame_copy.shape) == 2:
                frame_copy = cv2.cvtColor(frame_copy, cv2.COLOR_GRAY2BGR)
            video_writer.write(frame_copy)
            frames_written += 1
        
        # 释放写入器
        video_writer.release()
        logger.info(f"视频写入完成: {frames_written}帧已写入 {output_path}")
        
        # 验证文件是否存在且大小正常
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"生成的视频文件大小: {file_size} 字节")
            if file_size == 0:
                logger.error("生成的视频文件大小为0字节")
                return ""
        else:
            logger.error(f"视频文件未能生成: {output_path}")
            return ""
        
        # 读取视频文件为base64
        with open(output_path, 'rb') as video_file:
            video_base64 = base64.b64encode(video_file.read()).decode('utf-8')
        
        return video_base64
    except Exception as e:
        logger.error(f"生成视频base64编码失败: {str(e)}")
        return ""

async def video_chat_async_limit_frame(text, frames, timestamps, fps=20):
    """使用关键帧方式进行视频分析"""
    video_base64 = frames_to_base64(frames, fps, timestamps)

    # 准备请求数据
    url = APIConfig.QWEN_API_URL
    headers = {
        "Content-Type": "application/json",
        "authorization": APIConfig.QWEN_API_KEY
    }
    model = APIConfig.QWEN_MODEL

    # 提取关键帧
    data_image = []
    frame_count = int(min(VideoConfig.BUFFER_DURATION, len(frames)))
    for i in range(frame_count):
        frame = frames[(len(frames)//frame_count)*i]
        image_path = 'output_frame.jpg'
        cv2.imwrite(image_path, frame)
        with open(image_path,'rb') as file:
            image_base64 = "data:image/jpeg;base64,"+ base64.b64encode(file.read()).decode('utf-8')
        data_image.append(image_base64)
        
    content = [{"type": "text", "text": text}] + [{"type": "image_url","image_url": {"url":i}} for i in data_image]
      
    # 构建请求体
    data = {
        "model": model,
        "vl_high_resolution_images": False,
        "messages": [
            {
                "role": "user",
                "content": content,
            }
        ],
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        response = await client.post(url, headers=headers, json=data)
        response_data = response.json()
        return response_data['choices'][0]['message']['content']

async def chat_request(message, stream=False):
    """发送文本分析请求"""
    url = APIConfig.MOONSHOT_API_URL
    model = APIConfig.MOONSHOT_MODEL

    messages = [{"role" : "user", "content" : message}]
    headers = {
        "content-Type" : "application/json",
        "authorization" : APIConfig.MOONSHOT_API_KEY
    }
    data = {
        "messages" : messages,
        "model" : model,
        "repetition_penalty" : APIConfig.REPETITION_PENALTY,
        "temperature" : APIConfig.TEMPERATURE,
        "top_p": APIConfig.TOP_P,
        "top_k": APIConfig.TOP_K,
        "stream" : stream
    }
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(APIConfig.REQUEST_TIMEOUT)) as client:
        response = await client.post(url, headers=headers, json=data)
        response = response.json()
        return response['choices'][0]['message']['content']

def insert_txt(docs, table_name):
    """插入文本到向量数据库"""
    url = RAGConfig.VECTOR_API_URL
    data = {
        "docs": docs,
        "table_name": table_name
    }
    response = requests.post(url, json=data)
    return response.json()