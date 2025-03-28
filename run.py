"""
智能视频监控预警系统启动脚本
支持热重载和多工作进程
"""

import uvicorn
from config.base import ServerConfig
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # 使用导入字符串的方式启动应用
    # 修改为正确的导入路径
    uvicorn.run(
        "main:create_and_get_app",  # 指向main.py中的函数而不是直接对象
        host=ServerConfig.HOST,
        port=ServerConfig.PORT,
        reload=ServerConfig.RELOAD,  # 启用热重载
        workers=ServerConfig.WORKERS if not ServerConfig.RELOAD else 1  # 热重载模式只能用一个worker
    )