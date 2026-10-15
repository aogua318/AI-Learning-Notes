#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fastmcp_demo.py —— 用官方 Python SDK 的 FastMCP 高级 API 写 MCP Server
======================================================================

第 7 章的 server.py 是“手搓协议”：每一步 JSON-RPC 都要自己拼，适合理解原理。
真实开发当然不用这么累——官方 SDK 提供了 FastMCP 高级封装：
写几个带类型标注的 Python 函数，加上 @mcp.tool() 之类的装饰器，
SDK 会自动完成：JSON Schema 生成、协议分发、stdio 传输、结果序列化。

安装依赖（需要联网，请手动执行）：
    pip install mcp
或使用 uv（本项目其他章节推荐的虚拟环境工具）：
    uv add mcp

运行（stdio 传输，供客户端拉起）：
    python fastmcp_demo.py
"""

from mcp.server.fastmcp import FastMCP

# FastMCP("note-demo") 创建一个服务器实例，字符串参数是服务器名（会出现在
# 客户端的 serverInfo 里）。
mcp = FastMCP("note-demo")


# ---------------------------------------------------------------------------
# 工具（Tool）：模型控制的函数。装饰器 @mcp.tool() 是语法糖——
# 它等价于 mcp.tool()(add) 这种“装饰器工厂”调用，即把下面的函数对象注册进
# 服务器的工具表。函数的 docstring 会成为工具的 description，
# 参数类型标注（float/int/str 等）会被 SDK 自动转成 inputSchema。
# ---------------------------------------------------------------------------

@mcp.tool()
def add(a: float, b: float) -> float:
    """计算两个数字的和。

    Args:
        a: 第一个加数
        b: 第二个加数
    """
    return a + b


@mcp.tool()
def echo(text: str) -> str:
    """原样返回一段文本，用于联调测试。

    Args:
        text: 要原样返回的文本
    """
    return text


# ---------------------------------------------------------------------------
# 资源（Resource）：应用控制的上下文。URI 直接写在装饰器参数里。
# ---------------------------------------------------------------------------

@mcp.resource("note://welcome")
def welcome() -> str:
    """一封写给 MCP 学习者的便签。"""
    return "欢迎来到 MCP 世界！这个资源由 FastMCP 提供。"


# ---------------------------------------------------------------------------
# 提示词（Prompt）：用户控制的模板。函数参数就是提示词模板的参数，
# 返回值可以是字符串或消息列表。
# ---------------------------------------------------------------------------

@mcp.prompt()
def greet(name: str) -> str:
    """生成一段让模型向指定对象打招呼的提示词。

    Args:
        name: 要打招呼的对象
    """
    return f"请用热情友好的中文向 {name} 打招呼，一句话即可。"


if __name__ == "__main__":
    # mcp.run() 默认使用 stdio 传输：从 stdin 读 JSON-RPC、向 stdout 写。
    # 与 server.py 的主循环等价，只是 SDK 帮你实现了全部协议细节。
    mcp.run()
