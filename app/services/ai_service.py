"""
AI服务模块
处理与AI模型的通信，支持API和Ollama本地大模型的动态切换
"""

import base64
import httpx
import asyncio
import logging
import os
import cv2
import numpy as np
import time
import json

from config.base import QwenConfig, MoonshotConfig, OllamaConfig

logger = logging.getLogger(__name__)

class AIService:
    """AI服务类，处理与AI模型的通信
    
    采用静态方法设计，每次调用时根据当前配置决定使用API还是Ollama
    """
    
    @staticmethod
    async def process_video(frames, fps, prompt, timestamps=None):
        """处理视频并获取分析结果 - 动态决定使用API还是Ollama"""
        try:
            logger.info(f"开始处理视频，共 {len(frames)} 帧，帧率 {fps}")
            
            # 从帧采样生成关键帧图像
            data_image = []
            frame_count = min(len(frames), 10)  # 最多10帧
            step = max(1, len(frames) // frame_count)
            
            for i in range(0, len(frames), step):
                if len(data_image) >= frame_count:
                    break
                    
                frame = frames[i]
                image_path = f'output_frame_{i}.jpg'
                cv2.imwrite(image_path, frame)
                
                with open(image_path, 'rb') as file:
                    image_base64 = "data:image/jpeg;base64," + base64.b64encode(file.read()).decode('utf-8')
                data_image.append(image_base64)
                
                # 删除临时文件
                try:
                    os.remove(image_path)
                except:
                    pass
            
            # 验证API密钥是否有效
            qwen_api_valid = QwenConfig.API_KEY and len(QwenConfig.API_KEY) > 10
            
            # 每次调用时检查当前配置，增加API密钥验证
            if QwenConfig.USE_OLLAMA or not qwen_api_valid:
                logger.info(f"使用Ollama处理视频内容，模型：{OllamaConfig.QWEN_MODEL}")
                return await AIService._process_video_ollama(frames, prompt)
            else:
                logger.info(f"使用通义千问API处理视频内容，模型：{QwenConfig.MODEL}")
                return await AIService._process_video_api(data_image, prompt)
                
        except Exception as e:
            logger.error(f"处理视频时出错: {str(e)}")
            return f"无法处理视频: {str(e)}"
    
    @staticmethod
    async def analyze_text(text):
        """分析文本 - 动态决定使用API还是Ollama"""
        try:
            # 验证API密钥是否有效
            moonshot_api_valid = MoonshotConfig.API_KEY and len(MoonshotConfig.API_KEY) > 10
            
            # 每次调用时检查当前配置，增加API密钥验证
            if MoonshotConfig.USE_OLLAMA or not moonshot_api_valid:
                logger.info(f"使用Ollama分析文本内容，模型：{OllamaConfig.MOONSHOT_MODEL}")
                return await AIService._analyze_text_ollama(text)
            else:
                logger.info(f"使用Moonshot API分析文本内容，模型：{MoonshotConfig.MODEL}")
                try:
                    result = await AIService._analyze_text_api(text)
                    return result
                except Exception as e:
                    if "401 Unauthorized" in str(e):
                        logger.warning("API密钥无效，自动切换到Ollama模式")
                        # 自动切换到Ollama模式
                        MoonshotConfig.USE_OLLAMA = True
                        return await AIService._analyze_text_ollama(text)
                    raise
        except Exception as e:
            logger.error(f"分析文本时出错: {str(e)}")
            return f"无法分析文本: {str(e)}"
    
    @staticmethod
    async def _process_video_api(data_image, prompt):
        """使用通义千问API处理视频"""
        # 构建内容
        content = [{"type": "text", "text": prompt}] + [
            {"type": "image_url", "image_url": {"url": img}} for img in data_image
        ]
        
        # 构建请求
        url = QwenConfig.API_URL
        headers = {
            "Content-Type": "application/json",
            "authorization": QwenConfig.API_KEY
        }
        
        data = {
            "model": QwenConfig.MODEL,
            "vl_high_resolution_images": False,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
        }
        
        # 添加重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                    response = await client.post(url, headers=headers, json=data)
                    
                    if response.status_code == 401:
                        logger.warning("通义千问API密钥无效，自动切换到Ollama模式")
                        # 自动切换到Ollama模式
                        QwenConfig.USE_OLLAMA = True
                        return await AIService._process_video_ollama([], prompt)
                    
                    if response.status_code == 429:  # Too Many Requests
                        wait_time = 2 * (attempt + 1)  # 指数退避
                        logger.warning(f"API请求过多，等待{wait_time}秒后重试")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    response_data = response.json()
                    return response_data['choices'][0]['message']['content']
                    
            except Exception as e:
                logger.error(f"通义千问API处理请求失败 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                if "401 Unauthorized" in str(e):
                    logger.warning("通义千问API密钥无效，自动切换到Ollama模式")
                    # 自动切换到Ollama模式
                    QwenConfig.USE_OLLAMA = True
                    return await AIService._process_video_ollama([], prompt)
                    
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 * (attempt + 1))
                else:
                    raise
        
        raise RuntimeError("通义千问API处理请求失败，所有重试均失败")
    
    @staticmethod
    async def _process_video_ollama(frames, prompt):
        """使用Ollama处理视频"""
        try:
            # 由于Ollama可能不支持直接处理图像，我们需要将图像描述性地转换为文本
            # 首先保存一帧作为参考图像，稍后可以使用其他工具分析
            if frames and len(frames) > 0:
                reference_image_path = 'reference_frame.jpg'
                cv2.imwrite(reference_image_path, frames[0])
                
                # 构建文本提示
                text_prompt = (
                    f"{prompt}\n\n"
                    f"视频共有 {len(frames)} 帧，帧率约为 {len(frames)/10} FPS，时长约 10 秒。"
                    f"这是一个监控视频片段，请分析其中可能的异常情况。"
                )
            else:
                # 如果没有帧数据，提供一个简化的提示
                text_prompt = (
                    f"{prompt}\n\n"
                    f"请分析这个监控视频片段，查找可能的异常情况。"
                )
            
            # 构建Ollama API请求
            url = f"{OllamaConfig.OLLAMA_API_URL}/generate"
            data = {
                "model": OllamaConfig.QWEN_MODEL,
                "prompt": text_prompt,
                "stream": False
            }
            
            # 发送请求
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=httpx.Timeout(OllamaConfig.TIMEOUT)) as client:
                        response = await client.post(url, json=data)
                        
                        if response.status_code == 404:
                            # 模型不存在，尝试使用默认模型
                            logger.warning(f"Ollama模型 {OllamaConfig.QWEN_MODEL} 不存在，尝试使用默认模型")
                            data["model"] = "llama3"
                            continue
                            
                        response.raise_for_status()
                        response_data = response.json()
                        
                        # Ollama API返回格式可能是 {"response": "..."} 或其他格式
                        # 根据实际使用的Ollama版本调整
                        if "response" in response_data:
                            return response_data["response"]
                        else:
                            return str(response_data)
                except Exception as e:
                    logger.error(f"Ollama处理请求失败 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 * (attempt + 1))
                    else:
                        raise
                        
            raise RuntimeError("Ollama处理请求失败，所有重试均失败")
        except Exception as e:
            logger.error(f"Ollama处理视频时出错: {str(e)}")
            return f"Ollama无法处理视频: {str(e)}"
    
    @staticmethod
    async def _analyze_text_api(text):
        """使用Moonshot API分析文本"""
        url = MoonshotConfig.API_URL
        model = MoonshotConfig.MODEL
        
        messages = [{"role": "user", "content": text}]
        headers = {
            "Content-Type": "application/json",
            "authorization": MoonshotConfig.API_KEY
        }
        
        data = {
            "messages": messages,
            "model": model,
            "repetition_penalty": 1.05,
            "temperature": 0.5,
            "top_p": 0.01,
            "top_k": 20,
            "stream": False
        }
        
        # 添加重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                    response = await client.post(url, headers=headers, json=data)
                    
                    if response.status_code == 401:
                        raise ValueError("Moonshot API密钥无效")
                    
                    if response.status_code == 429:  # Too Many Requests
                        wait_time = 2 * (attempt + 1)  # 指数退避
                        logger.warning(f"API请求过多，等待{wait_time}秒后重试")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    response_data = response.json()
                    
                    if 'choices' not in response_data or not response_data['choices']:
                        raise ValueError("API返回结果中没有'choices'字段")
                    
                    return response_data['choices'][0]['message']['content']
            except Exception as e:
                logger.error(f"Moonshot API分析文本请求失败 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 * (attempt + 1))
                else:
                    raise
        
        raise RuntimeError("Moonshot API分析文本请求失败，所有重试均失败")
    
    @staticmethod
    async def _analyze_text_ollama(text):
        """使用Ollama分析文本"""
        try:
            url = f"{OllamaConfig.OLLAMA_API_URL}/generate"
            data = {
                "model": OllamaConfig.MOONSHOT_MODEL,
                "prompt": text,
                "stream": False
            }
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=httpx.Timeout(OllamaConfig.TIMEOUT)) as client:
                        response = await client.post(url, json=data)
                        
                        if response.status_code == 404:
                            # 模型不存在，尝试使用默认模型
                            logger.warning(f"Ollama模型 {OllamaConfig.MOONSHOT_MODEL} 不存在，尝试使用默认模型")
                            data["model"] = "llama3"
                            continue
                            
                        response.raise_for_status()
                        response_data = response.json()
                        
                        if "response" in response_data:
                            return response_data["response"]
                        else:
                            return str(response_data)
                except Exception as e:
                    logger.error(f"Ollama文本分析请求失败 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 * (attempt + 1))
                    else:
                        raise
                        
            raise RuntimeError("Ollama文本分析请求失败，所有重试均失败")
        except Exception as e:
            logger.error(f"Ollama文本分析时出错: {str(e)}")
            return f"由于API错误，无法完成分析。错误: {str(e)}"
            
    @staticmethod
    async def test_ollama_connection():
        """测试Ollama连接"""
        try:
            url = f"{OllamaConfig.OLLAMA_API_URL}/tags"
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return True, "连接成功"
                else:
                    return False, f"连接失败，状态码: {response.status_code}"
        except Exception as e:
            return False, f"连接错误: {str(e)}"