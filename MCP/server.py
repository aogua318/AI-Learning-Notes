#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
server.py —— 纯 Python 手写的 MCP Server（零第三方依赖）
========================================================

这个文件演示 MCP（Model Context Protocol）协议在 stdio 传输上的最小可运行实现：
不借助任何 SDK，只用标准库，按 2026-07-28 版规范实现：

  * server/discover   —— 能力发现（客户端连上来的第一个请求）
  * tools/list        —— 列出工具
  * tools/call        —— 调用工具
  * resources/list    —— 列出资源
  * resources/read    —— 读取资源
  * prompts/list      —— 列出提示词模板
  * prompts/get       —— 获取渲染后的提示词

stdio 传输的三条铁律（规范原文要求）：
  1. 服务器从 stdin 逐行读取 JSON-RPC 消息，向 stdout 逐行写出；
  2. 每条消息必须是不含换行符的单行 JSON（json.dumps 默认不换行，天然满足）；
  3. stdout 上只能出现合法 MCP 消息，日志一律写到 stderr。

运行方式：由 MCP 客户端（见 client.py）作为子进程启动，不面向人直接运行。
"""

import json
import sys

# ---------------------------------------------------------------------------
# 协议常量
# ---------------------------------------------------------------------------

# 本服务器实现的协议版本。规范用日期作为版本号，客户端在每个请求的
# _meta.io.modelcontextprotocol/protocolVersion 里带上它想用的版本。
PROTOCOL_VERSION = "2026-07-28"

# JSON-RPC 2.0 标准错误码（规范规定 MCP 复用这些码）
ERR_PARSE = -32700        # JSON 解析失败
ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_INVALID_PARAMS = -32602   # 参数不合法：规范明确要求用这个码拒绝缺少 _meta 的畸形请求
ERR_INTERNAL = -32603


# ---------------------------------------------------------------------------
# 输出工具：所有发给客户端的消息都必须经过这里
# ---------------------------------------------------------------------------

def log(message):
    """日志一律写 stderr。规范明确允许（且只允许）服务器用 stderr 输出日志，
    stdout 是协议信道，混入任何非 MCP 内容都会让客户端解析崩溃。"""
    print("[note-server] " + message, file=sys.stderr, flush=True)


def send(message):
    """向客户端发送一条 JSON-RPC 消息。

    注意 json.dumps 的 ensure_ascii=False：让中文等非 ASCII 字符按 UTF-8 原样
    输出（规范要求消息必须是 UTF-8 编码），而不是转义成 \\uXXXX。
    """
    # 语法糖说明：json.dumps(obj, ensure_ascii=False) 等价于先调用
    # json.dumps(obj) 再把结果里的 \\uXXXX 反转回原文，但更高效也更易读。
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()  # 行缓冲场景下必须手动 flush，否则消息会滞留在管道里


def reply(req_id, result):
    """发送成功响应。2026-07-28 规范要求每个 result 都带 resultType 字段，
    值为 "complete" 表示这是最终结果（另一种是 "input_required"，见文档 MRTR 一节）。"""
    # 语法糖说明：{"resultType": "complete", **result} 是字典解包（dict unpacking），
    # 等价于先创建 {"resultType": "complete"} 再把 result 的所有键值对逐个
    # update 进去：d = {"resultType": "complete"}; d.update(result)。
    # 如果 result 里恰好也有 resultType，后面的 **result 会覆盖前面的值。
    send({"jsonrpc": "2.0", "id": req_id, "result": {"resultType": "complete", **result}})


def reply_error(req_id, code, message):
    """发送错误响应。错误响应不带 resultType（规范只对 result 有此要求）。"""
    send({"jsonrpc": "2.0", "id": req_id,
          "error": {"code": code, "message": message}})


# ---------------------------------------------------------------------------
# 业务数据：本服务器提供 2 个工具、1 个资源、1 个提示词
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "add",
        "title": "加法计算器",
        "description": "计算两个数字的和，并返回结构化结果",
        # inputSchema 用 JSON Schema 描述入参；模型靠它决定怎么传参。
        # 规范默认方言是 JSON Schema 2020-12，省略 $schema 时按它处理。
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "第一个加数"},
                "b": {"type": "number", "description": "第二个加数"},
            },
            "required": ["a", "b"],
        },
        # outputSchema 描述结构化输出的形状，客户端/模型可据此校验。
        "outputSchema": {
            "type": "object",
            "properties": {"sum": {"type": "number", "description": "两数之和"}},
            "required": ["sum"],
        },
    },
    {
        "name": "echo",
        "title": "回声",
        "description": "原样返回一段文本，用于联调测试",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要原样返回的文本"},
            },
            "required": ["text"],
        },
    },
]

# 资源用 URI 标识。URI scheme 可以自定义（这里是 note://），客户端通过
# resources/read 按 URI 读取内容。
RESOURCES = [
    {
        "uri": "note://welcome",
        "name": "welcome",
        "title": "欢迎便签",
        "description": "一封写给 MCP 学习者的便签",
        "mimeType": "text/plain",
    },
]

PROMPTS = [
    {
        "name": "greet",
        "title": "打招呼",
        "description": "生成一段让模型向指定对象打招呼的提示词",
        "arguments": [
            # 规范里 arguments 用 "required": true/false 标注是否必填
            {"name": "name", "description": "要打招呼的对象", "required": True},
        ],
    },
]


# ---------------------------------------------------------------------------
# 各方法的处理器：输入 params 字典，返回 result 字典（不含 resultType，由 reply 补）
# ---------------------------------------------------------------------------

def handle_discover(params):
    """server/discover：规范要求所有服务器必须实现。
    客户端用它一次性拿到：支持的协议版本、能力清单、服务器身份。"""
    return {
        "supportedVersions": [PROTOCOL_VERSION],
        "capabilities": {
            "tools": {},       # 空对象表示支持；若支持列表变更通知可写 {"listChanged": true}
            "resources": {},
            "prompts": {},
        },
        # instructions 是给 LLM 看的自然语言使用说明，宿主通常会塞进系统提示词
        "instructions": "这是一个教学用 MCP 服务器：提供加法、回声两个工具和一份便签资源。",
        # serverInfo 放在 _meta 里，且 key 必须带 io.modelcontextprotocol/ 前缀（保留前缀）
        "_meta": {
            "io.modelcontextprotocol/serverInfo": {
                "name": "note-server",
                "version": "1.0.0",
            },
        },
    }


def handle_tools_list(params):
    return {"tools": TOOLS}


def handle_tools_call(params):
    """调用工具。规范把错误分成两类，这里体现第一种的处理方式：
    协议级错误（工具不存在、参数结构不合法）走 JSON-RPC error；
    业务级错误（入参校验失败等）走 result 里 isError=true，让模型能自我纠正。"""
    name = params.get("name")
    arguments = params.get("arguments") or {}

    if name == "add":
        # isinstance(x, (int, float)) 是语法糖吗？不是——这是 isinstance 支持
        # 传入“类型元组”一次判断多种类型的标准写法。注意 bool 是 int 的子类，
        # 所以要把 True/False 排除掉，否则 add(True, 2) 会静默算出 3。
        a, b = arguments.get("a"), arguments.get("b")
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) \
                or isinstance(a, bool) or isinstance(b, bool):
            # 业务错误：isError=true + 文本说明，模型读到后会明白该怎么改
            return {
                "content": [{"type": "text",
                             "text": "参数错误：a 和 b 必须是数字（boolean 不算）"}],
                "isError": True,
            }
        # 规范建议：返回结构化内容时，同时给一份序列化后的文本，兼容旧客户端
        return {
            "content": [{"type": "text", "text": json.dumps({"sum": a + b})}],
            "structuredContent": {"sum": a + b},
        }

    if name == "echo":
        text = arguments.get("text")
        if not isinstance(text, str):
            return {
                "content": [{"type": "text", "text": "参数错误：text 必须是字符串"}],
                "isError": True,
            }
        return {"content": [{"type": "text", "text": text}]}

    # 协议级错误：工具不存在。这类错误模型较难自行恢复，走 JSON-RPC error。
    raise McpError(ERR_INVALID_PARAMS, "Unknown tool: " + str(name))


def handle_resources_list(params):
    return {"resources": RESOURCES}


def handle_resources_read(params):
    uri = params.get("uri")
    if uri == "note://welcome":
        # resources/read 的结果字段名叫 contents（复数），内容是“内容块”数组
        return {"contents": [{
            "uri": uri,
            "mimeType": "text/plain",
            "text": "欢迎来到 MCP 世界！你刚刚通过 resources/read 读到了我。\n"
                    "资源是“应用控制”的上下文：由客户端/用户决定何时读取，而不是模型。",
        }]}
    raise McpError(ERR_INVALID_PARAMS, "Unknown resource: " + str(uri))


def handle_prompts_list(params):
    return {"prompts": PROMPTS}


def handle_prompts_get(params):
    name = params.get("name")
    arguments = params.get("arguments") or {}
    if name == "greet":
        who = arguments.get("name", "世界")
        # prompts/get 返回的是“消息列表”，直接就是可以发给 LLM 的对话消息
        return {"messages": [{
            "role": "user",
            "content": {"type": "text",
                        "text": "请用热情友好的中文向 %s 打招呼，一句话即可。" % who},
        }]}
    raise McpError(ERR_INVALID_PARAMS, "Unknown prompt: " + str(name))


# ---------------------------------------------------------------------------
# 自定义异常：让处理器用抛异常的方式表达“协议级错误”
# ---------------------------------------------------------------------------

class McpError(Exception):
    """携带 JSON-RPC 错误码的业务异常。"""

    def __init__(self, code, message):
        # 语法糖说明：super().__init__(message) 是调用父类 Exception 的构造函数，
        # 等价于 Exception.__init__(self, message)，但不用显式写 self。
        super().__init__(message)
        self.code = code


# 方法名 → 处理器 的分发表。新增方法只需在这里加一行。
HANDLERS = {
    "server/discover": handle_discover,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
    "resources/list": handle_resources_list,
    "resources/read": handle_resources_read,
    "prompts/list": handle_prompts_list,
    "prompts/get": handle_prompts_get,
}


# ---------------------------------------------------------------------------
# 请求校验与分发
# ---------------------------------------------------------------------------

REQUIRED_META_KEYS = (
    "io.modelcontextprotocol/protocolVersion",
    "io.modelcontextprotocol/clientCapabilities",
)


def validate_meta(params):
    """校验 2026-07-28 规范的强制要求：每个请求都必须在 _meta 里带上
    协议版本和客户端能力（无状态化的体现——服务器不记住任何连接级状态）。"""
    if not isinstance(params, dict):
        raise McpError(ERR_INVALID_PARAMS, "params must be an object")
    meta = params.get("_meta")
    if not isinstance(meta, dict):
        raise McpError(ERR_INVALID_PARAMS, "missing _meta in params")
    missing = [k for k in REQUIRED_META_KEYS if k not in meta]
    if missing:
        raise McpError(ERR_INVALID_PARAMS,
                       "missing required _meta keys: " + ", ".join(missing))
    # 语法糖说明：上面这行是列表推导式（list comprehension），等价于：
    #   missing = []
    #   for k in REQUIRED_META_KEYS:
    #       if k not in meta:
    #           missing.append(k)
    version = meta.get("io.modelcontextprotocol/protocolVersion")
    if version != PROTOCOL_VERSION:
        # 真实实现应返回 -32022 UnsupportedProtocolVersionError 并列出支持的版本，
        # 这里从简：教学服务器只认一个版本。
        raise McpError(ERR_INVALID_PARAMS,
                       "unsupported protocol version: %r (supported: %s)"
                       % (version, PROTOCOL_VERSION))


def handle_request(req_id, method, params):
    """处理一条请求：校验 _meta → 查分发表 → 执行 → 回包。"""
    try:
        validate_meta(params)
        handler = HANDLERS.get(method)
        if handler is None:
            raise McpError(ERR_METHOD_NOT_FOUND, "Method not found: " + str(method))
        result = handler(params)
        reply(req_id, result)
    except McpError as exc:
        reply_error(req_id, exc.code, str(exc))
    except Exception as exc:  # 兜底：任何未预期错误都不能让服务器崩溃
        log("internal error handling %s: %r" % (method, exc))
        reply_error(req_id, ERR_INTERNAL, "Internal error")


def handle_notification(method, params):
    """通知没有 id，不允许回复。规范目前只定义了 notifications/cancelled。"""
    if method == "notifications/cancelled":
        # 取消是“协作式”的：服务器收到后应尽快停止相关工作，且不得再发该请求的消息。
        # 本示例是同步短任务，没有可取消的中间状态，记录日志即可。
        req_id = (params or {}).get("requestId")
        log("received cancellation for request %r (no-op for sync handlers)" % req_id)
    else:
        log("ignoring unknown notification: %s" % method)


def main():
    """主循环：从 stdin 逐行读 JSON-RPC 消息，直到流关闭（EOF）。

    stdin 关闭是规范定义的“优雅关闭信号”：服务器应尽快退出。
    """
    log("note-server started, protocol version %s" % PROTOCOL_VERSION)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            # 解析失败时 id 无法得知，错误响应的 id 允许缺省
            send({"jsonrpc": "2.0",
                  "error": {"code": ERR_PARSE, "message": "Parse error: %s" % exc}})
            continue

        method = message.get("method")
        params = message.get("params")
        if "id" in message and method:
            handle_request(message["id"], method, params)
        elif method:
            handle_notification(method, params)
        else:
            # 客户端发来的响应（本示例服务器不主动发请求，所以不该收到）
            log("ignoring unexpected message: %.200s" % line)
    log("stdin closed, note-server exiting")


if __name__ == "__main__":
    # 语法糖说明：__name__ == "__main__" 表示“本文件被直接运行”；
    # 被 import 时 __name__ 是模块名，主函数不会执行。等价于其他语言的
    # if __name__ == '__main__': main() 惯用法。
    main()
