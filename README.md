# AI智能视频监控预警系统

![版本](https://img.shields.io/badge/版本-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.103.1-orange)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8.0-red)

## 项目概述

AI智能视频监控预警系统是一个基于多模态视觉模型的智能安防监控解决方案。系统能够实时分析监控视频画面，自动检测异常行为并生成预警信息。通过结合视频处理、大语言模型、异常检测和实时预警推送等技术，为安防监控提供智能化解决方案。

## 核心功能

- **实时视频分析**：支持本地视频文件和RTSP视频流
- **多模态行为分析**：使用通义千问VL模型和Moonshot分析视频内容
- **AI引擎灵活切换**：支持在线API模式与Ollama本地部署模式无缝切换
- **多模式预警检测**：智能识别交通违规、人员跌倒、异常物品等多种情况
- **WebSocket实时推送**：低延迟传输视频流和预警消息
- **异常记录存档**：自动保存异常视频片段和截图
- **可视化数据统计**：直观展示预警统计和监控数据

## 系统架构

```
视频源 → 视频处理器 → 多模态分析器 → 异常检测 → 预警服务 → WebSocket推送 → 前端界面
   ↓                                     ↓
存档服务                               知识库存储
```

主要组件:
- **视频处理器**: 负责视频流读取、缓冲和分段
- **多模态分析器**: 结合视觉和语言模型分析视频内容
- **预警服务**: 管理和推送异常检测消息
- **前端界面**: 实时展示监控画面和预警信息

## 环境要求

- Python 3.9+
- OpenCV 4.x
- FastAPI
- 通义千问API密钥（视觉语言模型，可选）
- Moonshot API密钥（语言模型，可选）
- Ollama (本地大模型，可选)

## 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/ai-watchdog.git
cd ai-watchdog

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 创建配置
cp .env.example .env
# 编辑.env文件，填写API密钥和配置
```

### 配置AI服务

系统支持三种AI服务模式：

1. **在线API模式**:
   - 通义千问API: 用于视频内容分析
   - Moonshot API: 用于文本异常检测

2. **本地Ollama模式**:
   - 使用本地部署的大模型进行分析
   - 需要先安装并配置Ollama

3. **混合模式**:
   - 视频分析和文本分析可独立切换AI引擎

编辑`.env`文件配置你的AI服务:

```
# 通义千问配置 (视频分析)
QWEN_USE_OLLAMA=False
QWEN_API_KEY=你的API密钥
QWEN_MODEL=qwen-vl-max-2025-01-25

# Moonshot配置 (文本分析)
MOONSHOT_USE_OLLAMA=False
MOONSHOT_API_KEY=你的API密钥
MOONSHOT_MODEL=moonshot-v1-8k

# Ollama配置 (本地模型)
OLLAMA_API_URL=http://localhost:11434/api
OLLAMA_QWEN_MODEL=llama3
OLLAMA_MOONSHOT_MODEL=llama3
```

### 运行系统

```bash
# 使用本地视频文件
python main.py --video_source "测试视频/test.mp4"

# 或使用RTSP视频流
python main.py --video_source "rtsp://admin:password@192.168.1.100:554/stream"

# 启用热重载模式（开发环境）
python run.py
```

### 访问界面

打开浏览器访问 http://localhost:16532

## 使用指南

1. **连接监控**：点击"连接监控"按钮开始视频分析
2. **设置参数**：通过设置面板调整视频源、分析间隔、AI模式等
3. **查看预警**：右侧面板显示预警列表和统计信息
4. **预警详情**：点击预警项目查看详细信息和截图
5. **上传视频**：可通过设置面板上传本地视频文件进行测试

## 异常检测类型

系统能检测以下类型的异常情况：

- **交通规则**：车辆闯红灯、违规行驶等
- **人员跌倒**：监测到摔倒、意外受伤等情况
- **异常物品**：检测异常或危险物品出现
- **人员聚集**：异常人群聚集或冲突
- **其他异常**：其他可能存在安全隐患的情况

## 自定义配置

### 1. 视频分析参数

在`.env`文件或命令行参数中设置：

```
# 视频处理参数
ANALYSIS_INTERVAL=10    # 分析间隔(秒)
BUFFER_DURATION=11      # 分析缓冲区长度(秒)
JPEG_QUALITY=70         # JPEG压缩质量
```

### 2. 预警规则自定义

编辑`config/prompts.py`文件修改异常检测规则：

```python
# 异常检测提示词
PROMPT_DETECT = """
[系统角色] 你是监控人员，正在分析最新的监控文本，并决定现在是否需要将现在的内容告知同事或者领导。

[历史上下文]
{Recursive_summary}

[当前时段] {current_time}
最新视频段描述：{latest_description}

请阅读上面的视频内容，判断当前视频是否存在以下异常情况，注意是当前的视频内容。
[分析要求]
异常情况1：
   - 人员聚集冲突
   - 异常物品出现
   - 违反安全规程操作
   - 自然灾害
   - 潜在危害
   - 违反交通规则（行人、摩托车、汽车等不遵守交规）
异常情况2
   - 宠物逃跑
   - 东西被盗或被人移动
   - 人员跌倒、摔倒等。
   - 小孩爬到高处
   等常识类异常情况

下面是输出格式要求：
如果没有明显异常情况，则不需要提醒或者预警，那么请直接输出：无异常状况。
如果描述中存在上述异常行为则输出：请注意，出现了xx的情况，需要即时处理或知晓。（xx为具体的异常情况，需要具体描述）
请出现任何异常情况都需要提醒。
输出简洁一点，不要过于繁琐，需要简洁的描述即可。
"""
```

## 故障排除

### 常见问题

1. **找不到视频文件**：
   - 检查视频路径是否正确
   - 确保目录拥有读取权限

2. **API认证失败**：
   - 验证API密钥是否正确
   - 系统会自动切换到Ollama模式（如已配置）

3. **Ollama连接失败**：
   - 确保Ollama服务已启动
   - 检查URL是否正确（默认为http://localhost:11434/api）

4. **预警未显示**：
   - 检查WebSocket连接状态
   - 查看后端日志是否有错误信息
   - 验证保存目录权限

### 日志查看

系统日志位于`data/logs/`目录下：

```bash
# 查看最新日志
cat data/logs/aiwatchdog_$(date +%Y%m%d).log
```

## 定制开发

系统采用模块化设计，可以通过以下方式进行定制：

1. **AI模型替换**：
   - 修改`app/services/ai_service.py`以支持其他AI服务
   - 添加新的模型接口和处理逻辑

2. **前端界面定制**：
   - 修改`frontend/`目录下的HTML/CSS/JS文件
   - 使用框架内的WebSocket接口进行交互

3. **分析规则调整**：
   - 编辑`config/prompts.py`中的提示词模板
   - 可以针对不同场景自定义异常检测规则

## 许可证

本项目采用MIT许可证。

## 致谢

- FastAPI团队提供的高性能Web框架
- OpenCV社区提供的视频处理技术
- 通义千问和Moonshot提供的AI能力
- Ollama项目提供的本地AI部署解决方案

---

© 2025 AI智能视频监控预警系统