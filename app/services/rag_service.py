"""
RAG知识库服务
负责向量数据库的交互
"""

import logging
import httpx
from typing import List, Dict, Any

from config.base import RAGConfig

logger = logging.getLogger(__name__)

class RAGService:
    """RAG知识库服务类"""
    
    def __init__(self):
        """初始化RAG服务"""
        self.enabled = RAGConfig.ENABLE_RAG
        self.api_url = RAGConfig.VECTOR_API_URL
        self.history_file = RAGConfig.HISTORY_FILE
        
        if self.enabled:
            logger.info("RAG知识库服务已启用")
        else:
            logger.info("RAG知识库服务已禁用，使用本地文件存储")
    
    async def insert_text(self, docs: List[str], table_name: str) -> Dict[str, Any]:
        """将文本插入到向量数据库"""
        if not self.enabled:
            logger.warning("RAG服务未启用，无法插入文本到向量数据库")
            return {"status": "error", "message": "RAG服务未启用"}
            
        if not docs:
            logger.warning("没有提供文档，跳过插入")
            return {"status": "error", "message": "没有提供文档"}
            
        try:
            logger.info(f"正在插入 {len(docs)} 条文档到向量数据库表 {table_name}")
            
            data = {
                "docs": docs,
                "table_name": table_name
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, json=data)
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"成功插入文档到向量数据库")
                return result
                
        except Exception as e:
            logger.error(f"向量数据库插入失败: {str(e)}")
            return {"status": "error", "message": str(e)}