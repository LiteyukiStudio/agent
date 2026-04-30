"""推送适配器基类与注册表。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class PushAdapter(ABC):
    """推送通道适配器基类。"""

    name: ClassVar[str] = ""
    display_name: ClassVar[str] = ""
    # 配置 schema：{field_name: description}，用于引导用户配置
    config_schema: ClassVar[dict[str, str]] = {}

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    @abstractmethod
    async def send(self, title: str, content: str, content_type: str = "text") -> str:
        """发送通知。

        Args:
            title: 通知标题
            content: 通知内容
            content_type: "text" | "markdown" | "html"

        Returns:
            成功返回 "ok"，失败返回错误信息。
        """

    def validate_config(self) -> str | None:
        """验证配置是否完整。返回 None 表示通过，否则返回缺失字段提示。"""
        missing = [k for k in self.config_schema if not self.config.get(k)]
        if missing:
            return f"缺少必填配置: {', '.join(missing)}"
        return None


# 适配器注册表：type_name → adapter_class
_registry: dict[str, type[PushAdapter]] = {}


def register_adapter(cls: type[PushAdapter]) -> type[PushAdapter]:
    """装饰器：注册适配器到全局表。"""
    _registry[cls.name] = cls
    return cls


def get_adapter_class(type_name: str) -> type[PushAdapter] | None:
    """根据类型名获取适配器类。"""
    return _registry.get(type_name)


def list_adapter_types() -> list[dict[str, Any]]:
    """列出所有可用的适配器类型及其配置要求。"""
    return [
        {
            "type": cls.name,
            "display_name": cls.display_name,
            "config_fields": cls.config_schema,
        }
        for cls in _registry.values()
    ]


# 导入所有适配器以触发注册
from . import (  # noqa: E402
    feishu as _feishu,
    gotify as _gotify,
    onebot as _onebot,
    smtp as _smtp,
    wecom as _wecom,
)
