"""
预警服务模块
处理预警消息的管理和推送
"""

import json
import logging
from datetime import datetime
from typing import Set
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)

class AlertService:
    """预警服务类，管理预警消息的处理和推送"""
    
    # 存储活跃的WebSocket连接
    _connections: Set[WebSocket] = set()
    
    @classmethod
    async def register(cls, websocket: WebSocket):
        """注册新的WebSocket连接"""
        await websocket.accept()
        cls._connections.add(websocket)
        logger.info("新的预警WebSocket连接已注册")
    
    @classmethod
    def remove(cls, websocket: WebSocket):
        """移除WebSocket连接"""
        if websocket in cls._connections:
            cls._connections.remove(websocket)
            logger.info("WebSocket连接已移除")
    
    @classmethod
    async def notify(cls, data):
        """向所有连接的客户端推送预警消息"""
        # 添加时间戳
        message = json.dumps({
            "timestamp": datetime.now().isoformat(),
            **data
        })
        
        # 广播消息到所有连接
        for conn in list(cls._connections):
            try:
                if conn.client_state == WebSocketState.CONNECTED:
                    await conn.send_text(message)
                else:
                    cls._connections.remove(conn)
            except Exception as e:
                logger.warning(f"预警消息推送失败: {str(e)}")
                if conn in cls._connections:
                    cls._connections.remove(conn)