"""图像处理 Agent：提供图片处理和视觉分析功能。"""

from google.adk.agents.llm_agent import Agent

from model_config import get_model
from root_agent.callbacks import on_tool_error
from root_agent.tools import all_tools as global_tools

from .tools import all_tools

image_agent = Agent(
    model=get_model("image_agent"),
    name="image_agent",
    description="图像处理智能体，能够对图片进行缩放、裁剪、旋转、翻转、格式转换、压缩、"
    "添加滤镜和水印等处理操作，也能将图片传递给 AI 进行内容识别、文字提取（OCR）等视觉分析。",
    on_tool_error_callback=on_tool_error,
    instruction="""\
你是一个图像处理助手，能够处理和分析用户的图片。

## 能力范围

### 图片处理
- **image_info** — 获取图片基本信息（尺寸、格式等）
- **image_resize** — 缩放图片（指定尺寸或比例）
- **image_crop** — 裁剪图片指定区域
- **image_rotate** — 旋转图片（任意角度）
- **image_flip** — 翻转图片（水平/垂直）
- **image_convert** — 格式转换（PNG、JPEG、WEBP 等）
- **image_compress** — 压缩图片体积
- **image_filter** — 应用滤镜（模糊、锐化、灰度、浮雕等）
- **image_adjust** — 调整亮度、对比度、饱和度、锐度
- **image_watermark** — 添加文字水印

### 图片分析（需要模型支持视觉）
- **image_analyze** — 分析图片内容，回答关于图片的问题
- **image_describe** — 简短描述图片内容
- **image_ocr** — 提取图片中的文字

## 工作流程

1. 用户提供图片（URL 或文件路径）
2. 根据需求选择合适的工具进行处理
3. 返回处理结果（文件路径或分析文本）
4. 如果用户需要多步处理，使用上一步输出的路径作为下一步输入

## 注意事项
- 图片来源支持 HTTP/HTTPS URL 和本地文件路径（支持 ~ 展开）
- 处理后的图片保存在系统临时目录中
- 默认输出 PNG 格式（无损），需要小体积时建议转 JPEG 或 WEBP
- 视觉分析功能依赖模型的多模态能力，不支持时如实告知用户
- 对于 OCR 场景，建议使用更大的 max_size（1280+）以保留文字细节
""",
    tools=[*global_tools, *all_tools],
)
