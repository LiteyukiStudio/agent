"""用户交互工具：向用户展示选项供其选择。"""

from __future__ import annotations


def present_options(
    question: str,
    options: list[str],
    mode: str = "single",
    icons: list[str] | None = None,
) -> str:
    """向用户展示可点击的选项，等待用户做出选择。

    当你需要用户在多个选项中做出明确选择时使用此工具。
    调用后不要自行假设用户的选择，等待用户实际点击后再继续。

    Args:
        question: 要询问用户的问题，简明扼要。
        options: 可供选择的选项列表，每个选项是一个简短字符串，2-6 个选项为佳。
        mode: 选择模式：
            - "single"：单选，用户只能选一个选项（默认）。
            - "multiple"：多选，用户可以选择多个选项后提交。
            - "free"：自由输入，选项仅作为建议，用户可以直接编写任意内容。
        icons: 每个选项对应的图标，与 options 一一对应（可选但强烈建议提供）。
            **你必须尽最大努力为每个选项提供图标**，优先级如下：

            1. **官方 SVG/PNG 图标 URL（最优先）**：
               大多数知名项目都有公开的图标文件，通常在官网或 CDN 上：
               - 官网 favicon: https://example.com/favicon.svg 或 /favicon.ico
               - 官网 logo: https://example.com/logo.svg
               - GitHub raw: https://raw.githubusercontent.com/org/repo/main/logo.svg
               - CDN 图标服务: https://cdn.simpleicons.org/{品牌名}
               常见示例：
               - Vite: "https://vitejs.dev/logo.svg"
               - React: "https://cdn.simpleicons.org/react"
               - Python: "https://cdn.simpleicons.org/python"
               - Docker: "https://cdn.simpleicons.org/docker"
               - Node.js: "https://cdn.simpleicons.org/nodedotjs"
               - pnpm: "https://cdn.simpleicons.org/pnpm"
               - npm: "https://cdn.simpleicons.org/npm"
               - GitHub: "https://cdn.simpleicons.org/github"
               - Rust: "https://cdn.simpleicons.org/rust"
               - Go: "https://cdn.simpleicons.org/go"

            2. **emoji（次选）**：当无法确定官方图标 URL 时使用。
               选择语义最匹配的 emoji，如 🐳(Docker)、🦀(Rust)、🐍(Python)。

            3. **null**：实在没有合适图标时传 null。

            **重要**：对于知名技术品牌和工具，务必使用 https://cdn.simpleicons.org/{name}
            格式的图标 URL（Simple Icons 是开源图标库，覆盖 3000+ 品牌图标）。
            品牌名全小写、无空格，参考 https://simpleicons.org 查看支持列表。

    Returns:
        提示信息，表示正在等待用户选择。
    """
    return f"已向用户展示 {len(options)} 个选项（模式: {mode}），等待选择中..."
