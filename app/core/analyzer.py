"""
多模态视频分析器
负责视频内容分析和异常检测
"""

import asyncio
import logging
import os
import time
import datetime
import cv2
import numpy as np

from app.services.ai_service import AIService  # 导入AIService类
from app.services.rag_service import RAGService
from config.prompts import prompt_detect, prompt_summary, prompt_vieo

logger = logging.getLogger(__name__)

class MultiModalAnalyzer:
    """多模态视频分析器类"""
    
    def __init__(self):
        """初始化多模态分析器"""
        self.message_queue = []
        self.time_step_story = []
        # 不再创建AIService实例，直接使用静态方法
        self.rag_service = RAGService()
    
    def trans_date(self, date_str):
        """格式化日期字符串"""
        year, month, day, hour, minute, second = date_str.split('-')
        am_pm = "上午" if int(hour) < 12 else "下午"
        hour_12 = hour if hour == '12' else str(int(hour) % 12)
        return f"{year}年{int(month)}月{int(day)}日{am_pm}{hour_12}点（{hour}时）{int(minute)}分{int(second)}秒"
    
    async def analyze(self, frames, fps=20, timestamps=None):
        """分析视频帧并检测异常"""
        start_time = time.time()
        
        # 构建历史信息
        histroy = "录像视频刚刚开始。"
        Recursive_summary = ""
        for i in self.message_queue:
            histroy = "历史视频内容总结:" + Recursive_summary + "\n\n当前时间段：" + i['start_time'] + "  - " + i['end_time'] + "\n该时间段视频描述如下：" + i['description'] + "\n\n该时间段异常提醒:" + i['is_alert']
        
        # 并行处理总结和视频描述任务 - 使用静态方法
        time_temp = time.time()
        tasks = [
            AIService.analyze_text(prompt_summary.format(histroy=histroy)), 
            AIService.process_video(frames, fps, prompt_vieo, timestamps)
        ]
        results = await asyncio.gather(*tasks)
        
        Recursive_summary = results[0]
        description = results[1]
        description_time = time.time() - time_temp
        
        # 如果没有时间戳，直接返回描述结果
        if timestamps is None:
            return description
        
        # 保存监控视频描述
        date_flag = self.trans_date(timestamps[0]) + "："
        if self.rag_service.enabled:
            await self.rag_service.insert_text([date_flag + description], 'table_test_table')
        else:
            logger.info("RAG未开启,准备保存到本地")
            with open(self.rag_service.history_file, 'a', encoding='utf-8') as file:
                logger.info("开始保存历史消息")
                file.write(date_flag + description + '\n')
        
        # 检测异常 - 使用静态方法
        text = prompt_detect.format(
            Recursive_summary=Recursive_summary,
            current_time=timestamps[0] + "  - " + timestamps[-1],
            latest_description=description
        )
        
        time_temp = time.time()
        alert = await AIService.analyze_text(text)
        alert_time = time.time() - time_temp
        
        logger.info(f"警告内容：{alert}")    
        logger.info(f"视频分析耗时 {time.time() - start_time:.2f}s")
        
        # 处理异常情况
        # 修改 analyze 方法中处理异常情况的代码部分
        # 修改 analyze 方法中处理异常情况的代码部分
        if "无异常" not in alert:
            current_time = timestamps[0]
            file_str = f"waring_{current_time}"
            picture_path = f"video_warning/{file_str}.jpg"
            video_path = f"video_warning/{file_str}.mp4"
            
            # 确保目录存在
            os.makedirs('video_warning', exist_ok=True)
            
            # 保存警告截图 - 即使视频保存失败也至少有截图
            frame = frames[0].copy()  # 创建副本以避免修改原始数据
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            
            try:
                cv2.imwrite(picture_path, frame)
                picture_file_name = f"{file_str}.jpg"
                logger.info(f"成功保存警告截图: {picture_path}")
            except Exception as e:
                logger.error(f"保存警告截图失败: {str(e)}")
                picture_file_name = None
            
            # 尝试保存视频
            video_file_name = None
            if os.path.exists("./video_warning/output.mp4"):
                try:
                    os.rename("./video_warning/output.mp4", video_path)
                    video_file_name = f"{file_str}.mp4"
                    logger.info(f"成功保存警告视频: {video_path}")
                except Exception as e:
                    logger.error(f"保存警告视频失败: {str(e)}")
            else:
                logger.warning(f"警告视频文件不存在: ./video_warning/output.mp4")
            
            # 无论视频是否保存成功，都返回警告信息
            logger.info(f"返回警告信息到前端: {alert}")
            return {
                "alert": f"<span style=\"color:red;\">{alert}</span>",
                "description": f'当前10秒监控消息描述：\n{description}`\n\n 历史监控内容:\n{Recursive_summary}`',
                "video_file_name": video_file_name,
                "picture_file_name": picture_file_name
            }
        
        # 无异常情况下，更新消息队列
        if timestamps:
            self.message_queue.append({ 
                'start_time': timestamps[0],
                'end_time': timestamps[-1],
                'description': description, 
                'is_alert': alert
            })
            
            # 只保留最近15条消息
            self.message_queue = self.message_queue[-15:]
            
        return {"alert": "无异常"}