"""图像处理工具：缩放、裁剪、旋转、翻转、格式转换、压缩、滤镜、水印等常用操作。

所有工具均基于 Pillow（PIL）实现，支持通过 URL 或本地路径加载图片。
处理后的图片保存到临时目录并返回路径。
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import httpx
from google.adk.tools import ToolContext
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


def _load_image(source: str) -> Image.Image:
    """从 URL 或本地路径加载图片。"""
    if source.startswith(("http://", "https://")):
        resp = httpx.get(source, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content))
    path = Path(source).expanduser()
    if not path.exists():
        msg = f"文件不存在: {source}"
        raise FileNotFoundError(msg)
    return Image.open(path)


def _save_image(img: Image.Image, fmt: str = "PNG", quality: int = 85) -> str:
    """保存图片到临时文件并返回路径。"""
    suffix = f".{fmt.lower()}"
    if fmt.upper() == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, dir=tempfile.gettempdir()) as tmp:
        save_kwargs: dict = {"format": fmt}
        if fmt.upper() in ("JPEG", "WEBP"):
            save_kwargs["quality"] = quality
        img.save(tmp.name, **save_kwargs)
        return tmp.name


def image_info(source: str, tool_context: ToolContext) -> dict:
    """获取图片的基本信息（尺寸、格式、模式、文件大小）。

    Args:
        source: 图片 URL 或本地文件路径。

    Returns:
        包含 width、height、format、mode、file_size_bytes 的字典。
    """
    img = _load_image(source)
    info = {
        "width": img.width,
        "height": img.height,
        "format": img.format or "unknown",
        "mode": img.mode,
    }
    # 尝试获取文件大小
    if not source.startswith(("http://", "https://")):
        path = Path(source).expanduser()
        if path.exists():
            info["file_size_bytes"] = path.stat().st_size
    return info


def image_resize(
    source: str,
    tool_context: ToolContext,
    width: int = 0,
    height: int = 0,
    scale: float = 0.0,
    output_format: str = "PNG",
) -> str:
    """缩放图片到指定尺寸或比例。

    可以通过 width/height 指定目标尺寸（若只指定其中一个，则等比缩放），
    也可以通过 scale 指定缩放比例（如 0.5 表示缩小一半）。

    Args:
        source: 图片 URL 或本地文件路径。
        width: 目标宽度（像素），0 表示不限制。
        height: 目标高度（像素），0 表示不限制。
        scale: 缩放比例（大于 0 时生效，优先于 width/height）。
        output_format: 输出格式，支持 PNG、JPEG、WEBP。

    Returns:
        处理后的图片文件路径。
    """
    img = _load_image(source)

    if scale > 0:
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
    elif width > 0 and height > 0:
        new_w, new_h = width, height
    elif width > 0:
        ratio = width / img.width
        new_w = width
        new_h = int(img.height * ratio)
    elif height > 0:
        ratio = height / img.height
        new_w = int(img.width * ratio)
        new_h = height
    else:
        return "错误：需要指定 width/height 或 scale 参数。"

    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    path = _save_image(img_resized, output_format)
    return f"已缩放为 {new_w}x{new_h}，保存到: {path}"


def image_crop(
    source: str,
    left: int,
    top: int,
    right: int,
    bottom: int,
    tool_context: ToolContext,
    output_format: str = "PNG",
) -> str:
    """裁剪图片的指定区域。

    坐标系为左上角原点，单位像素。(left, top) 为裁剪区域左上角，(right, bottom) 为右下角。

    Args:
        source: 图片 URL 或本地文件路径。
        left: 裁剪区域左边界 x 坐标。
        top: 裁剪区域上边界 y 坐标。
        right: 裁剪区域右边界 x 坐标。
        bottom: 裁剪区域下边界 y 坐标。
        output_format: 输出格式。

    Returns:
        裁剪后的图片文件路径。
    """
    img = _load_image(source)
    cropped = img.crop((left, top, right, bottom))
    path = _save_image(cropped, output_format)
    return f"已裁剪为 {cropped.width}x{cropped.height}，保存到: {path}"


def image_rotate(
    source: str,
    angle: float,
    tool_context: ToolContext,
    expand: bool = True,
    output_format: str = "PNG",
) -> str:
    """旋转图片指定角度（逆时针）。

    Args:
        source: 图片 URL 或本地文件路径。
        angle: 旋转角度（度），正数为逆时针。
        expand: 是否扩展画布以容纳完整图片，默认 True。
        output_format: 输出格式。

    Returns:
        旋转后的图片文件路径。
    """
    img = _load_image(source)
    rotated = img.rotate(angle, expand=expand, resample=Image.Resampling.BICUBIC)
    path = _save_image(rotated, output_format)
    return f"已旋转 {angle}°，保存到: {path}"


def image_flip(
    source: str,
    direction: str,
    tool_context: ToolContext,
    output_format: str = "PNG",
) -> str:
    """翻转图片。

    Args:
        source: 图片 URL 或本地文件路径。
        direction: 翻转方向，"horizontal"（水平/左右翻转）或 "vertical"（垂直/上下翻转）。
        output_format: 输出格式。

    Returns:
        翻转后的图片文件路径。
    """
    img = _load_image(source)
    if direction == "horizontal":
        flipped = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    elif direction == "vertical":
        flipped = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    else:
        return '错误：direction 参数必须是 "horizontal" 或 "vertical"。'
    path = _save_image(flipped, output_format)
    return f"已{direction}翻转，保存到: {path}"


def image_convert(
    source: str,
    target_format: str,
    tool_context: ToolContext,
    quality: int = 85,
) -> str:
    """转换图片格式。

    Args:
        source: 图片 URL 或本地文件路径。
        target_format: 目标格式，支持 PNG、JPEG、WEBP、BMP、GIF、TIFF。
        quality: JPEG/WEBP 的压缩质量（1-100），默认 85。

    Returns:
        转换后的图片文件路径。
    """
    img = _load_image(source)
    fmt = target_format.upper()
    if fmt == "JPG":
        fmt = "JPEG"
    path = _save_image(img, fmt, quality)
    return f"已转换为 {fmt} 格式，保存到: {path}"


def image_compress(
    source: str,
    tool_context: ToolContext,
    quality: int = 60,
    max_width: int = 0,
    max_height: int = 0,
) -> str:
    """压缩图片以减小文件体积。

    通过降低质量和可选的尺寸限制来压缩图片。输出为 JPEG 或 WEBP 格式。

    Args:
        source: 图片 URL 或本地文件路径。
        quality: 压缩质量（1-100），值越小文件越小，默认 60。
        max_width: 最大宽度限制（0 表示不限制）。
        max_height: 最大高度限制（0 表示不限制）。

    Returns:
        压缩后的图片文件路径。
    """
    img = _load_image(source)

    # 尺寸限制
    if max_width > 0 or max_height > 0:
        w, h = img.size
        ratio = 1.0
        if max_width > 0 and w > max_width:
            ratio = min(ratio, max_width / w)
        if max_height > 0 and h > max_height:
            ratio = min(ratio, max_height / h)
        if ratio < 1.0:
            img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)

    path = _save_image(img, "JPEG", quality)
    file_size = Path(path).stat().st_size
    return f"已压缩（质量={quality}），{img.width}x{img.height}，大小 {file_size} 字节，保存到: {path}"


def image_filter(
    source: str,
    filter_name: str,
    tool_context: ToolContext,
    output_format: str = "PNG",
) -> str:
    """对图片应用滤镜效果。

    Args:
        source: 图片 URL 或本地文件路径。
        filter_name: 滤镜名称，支持: blur（模糊）、sharpen（锐化）、contour（轮廓）、
            detail（细节增强）、edge_enhance（边缘增强）、emboss（浮雕）、
            smooth（平滑）、grayscale（灰度）。
        output_format: 输出格式。

    Returns:
        处理后的图片文件路径。
    """
    img = _load_image(source)
    filter_map = {
        "blur": ImageFilter.BLUR,
        "sharpen": ImageFilter.SHARPEN,
        "contour": ImageFilter.CONTOUR,
        "detail": ImageFilter.DETAIL,
        "edge_enhance": ImageFilter.EDGE_ENHANCE,
        "emboss": ImageFilter.EMBOSS,
        "smooth": ImageFilter.SMOOTH,
    }
    name_lower = filter_name.lower()

    if name_lower == "grayscale":
        img = img.convert("L")
    elif name_lower in filter_map:
        img = img.filter(filter_map[name_lower])
    else:
        supported = ", ".join([*filter_map.keys(), "grayscale"])
        return f'错误：不支持的滤镜 "{filter_name}"。支持的滤镜: {supported}'

    path = _save_image(img, output_format)
    return f"已应用 {filter_name} 滤镜，保存到: {path}"


def image_adjust(
    source: str,
    tool_context: ToolContext,
    brightness: float = 1.0,
    contrast: float = 1.0,
    saturation: float = 1.0,
    sharpness: float = 1.0,
    output_format: str = "PNG",
) -> str:
    """调整图片的亮度、对比度、饱和度和锐度。

    所有参数默认 1.0 表示不变，小于 1.0 减弱，大于 1.0 增强。

    Args:
        source: 图片 URL 或本地文件路径。
        brightness: 亮度系数，0.0 为全黑，1.0 不变，2.0 为两倍亮度。
        contrast: 对比度系数。
        saturation: 饱和度系数，0.0 为灰度。
        sharpness: 锐度系数。
        output_format: 输出格式。

    Returns:
        处理后的图片文件路径。
    """
    img = _load_image(source)

    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(saturation)
    if sharpness != 1.0:
        img = ImageEnhance.Sharpness(img).enhance(sharpness)

    path = _save_image(img, output_format)
    return f"已调整（亮度={brightness}, 对比度={contrast}, 饱和度={saturation}, 锐度={sharpness}），保存到: {path}"


def image_watermark(
    source: str,
    text: str,
    tool_context: ToolContext,
    position: str = "bottom_right",
    font_size: int = 24,
    opacity: int = 128,
    color: str = "white",
    output_format: str = "PNG",
) -> str:
    """给图片添加文字水印。

    Args:
        source: 图片 URL 或本地文件路径。
        text: 水印文字内容。
        position: 水印位置，支持 top_left、top_right、bottom_left、bottom_right、center。
        font_size: 字体大小（像素），默认 24。
        opacity: 不透明度（0-255），默认 128。
        color: 文字颜色，如 white、black、red。
        output_format: 输出格式。

    Returns:
        处理后的图片文件路径。
    """
    img = _load_image(source).convert("RGBA")

    # 创建水印图层
    watermark_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark_layer)

    # 尝试使用系统字体
    try:
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    # 获取文字边界
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # 计算位置
    margin = 20
    positions = {
        "top_left": (margin, margin),
        "top_right": (img.width - text_w - margin, margin),
        "bottom_left": (margin, img.height - text_h - margin),
        "bottom_right": (img.width - text_w - margin, img.height - text_h - margin),
        "center": ((img.width - text_w) // 2, (img.height - text_h) // 2),
    }
    pos = positions.get(position, positions["bottom_right"])

    # 颜色解析
    color_map = {
        "white": (255, 255, 255),
        "black": (0, 0, 0),
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
    }
    rgb = color_map.get(color.lower(), (255, 255, 255))
    fill_color = (*rgb, opacity)

    draw.text(pos, text, font=font, fill=fill_color)

    # 合并图层
    result = Image.alpha_composite(img, watermark_layer)
    if output_format.upper() == "JPEG":
        result = result.convert("RGB")

    path = _save_image(result, output_format)
    return f'已添加水印 "{text}"，保存到: {path}'


all_tools: list = [
    image_info,
    image_resize,
    image_crop,
    image_rotate,
    image_flip,
    image_convert,
    image_compress,
    image_filter,
    image_adjust,
    image_watermark,
]
