#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
client.py —— 纯 Python 手写的 MCP Client（零第三方依赖）
========================================================

演示一个 MCP 客户端如何与 server.py 通信：

  1. 把 MCP 服务器作为子进程启动（stdio 传输：客户端负责拉起服务器进程）；
  2. 先发 server/discover 探测服务器能力；
  3. tools/list 发现工具，tools/call 调用工具（含一次失败调用，演示 isError）；
  4. resources/list + resources/read 读取资源；
  5. prompts/get 获取渲染后的提示词；
  6. 故意发一个缺少 _meta 的畸形请求，演示服务器的无状态校验。

同时把每一次收发的原始报文打印出来，让你直观看到“协议在线上到底长什么样”。

运行：python client.py        （无需任何第三方包）
"""

import json
import subprocess
import sys
import threading

PROTOCOL_VERSION = "2026-07-28"


class McpStdioClient:
    """一个最小化的 MCP stdio 客户端。"""

    def __init__(self, command):
        # subprocess.Popen 启动子进程；text=True 表示用文本模式（str）读写管道，
        # 此时必须显式指定 encoding="utf-8"——Windows 上管道默认编码是本地代码页
        # （中文系统为 GBK），不指定会导致中文乱码。bufsize=1 = 行缓冲，写一行
        # 立即发给子进程。
        self.proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._next_id = 0
        # 语法糖说明：threading.Thread(target=..., daemon=True) 创建守护线程——
        # daemon=True 表示主程序退出时该线程被强制结束，不会拖住进程。
        # 这里用它把服务器的 stderr 日志实时转发到我们终端。
        threading.Thread(target=self._pump_stderr, daemon=True).start()

    def _pump_stderr(self):
        for line in self.proc.stderr:
            print("[server-stderr] " + line.rstrip())

    # ------------------------------------------------------------------
    # 协议层
    # ------------------------------------------------------------------

    def _meta(self):
        """2026-07-28 规范：每个请求都必须自带协议元数据（无状态化的核心），
        服务器不依赖任何连接级记忆。protocolVersion 与 clientCapabilities
        是必填，clientInfo 是 SHOULD。"""
        return {
            "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
            "io.modelcontextprotocol/clientInfo": {
                "name": "raw-client",
                "version": "1.0.0",
            },
            "io.modelcontextprotocol/clientCapabilities": {},
        }

    def _write_line(self, message):
        self.proc.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def request(self, method, params=None, show=True):
        """发一条请求，读到对应 id 的响应后返回 result 或 error 字典。"""
        self._next_id += 1
        req_id = self._next_id
        body = {"jsonrpc": "2.0", "id": req_id, "method": method}
        # 规范结构：params._meta 里才放 io.modelcontextprotocol/* 元数据键。
        # 即 {"method": ..., "params": {"_meta": {"io.modelcontextprotocol/...": ...}}}
        body["params"] = {**(params or {}), "_meta": self._meta()}
        if show:
            self._show("--> 客户端发出", body)
        self._write_line(body)

        # 逐行读响应，直到拿到匹配 id 的（通知没有 id，直接忽略）
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("服务器关闭了 stdout（进程可能已退出）")
            line = line.strip()
            if not line:
                continue
            message = json.loads(line)
            if message.get("id") != req_id:
                # 理论上 2026-07-28 下服务器不会主动发请求/无关通知
                self._show("<-- 服务器推送（无关消息，忽略）", message)
                continue
            self._show("<-- 服务器响应", message)
            if "error" in message:
                return message["error"]
            return message.get("result", {})

    def notify(self, method, params=None):
        """发一条通知（无 id，服务器不得回复）。"""
        body = {"jsonrpc": "2.0", "method": method}
        if params:
            body["params"] = params
        self._write_line(body)
        self._show("--> 客户端发出（通知，无 id）", body)

    # ------------------------------------------------------------------
    # 展示层：让协议报文对人类可读
    # ------------------------------------------------------------------

    @staticmethod
    def _show(title, message):
        print("\n" + title)
        print(json.dumps(message, ensure_ascii=False, indent=2))

    def close(self):
        """规范定义的优雅关闭：关闭服务器 stdin → 等待退出 → 超时则强杀。"""
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


# ---------------------------------------------------------------------------
# 演示流程
# ---------------------------------------------------------------------------

def main():
    print("=" * 62)
    print("MCP 原始协议演示：客户端启动 server.py 并逐条收发 JSON-RPC")
    print("=" * 62)

    # sys.executable 是当前 Python 解释器的绝对路径，保证子进程用同一个 Python
    client = McpStdioClient([sys.executable, "server.py"])
    try:
        # 1) 能力发现：服务器 MUST 实现 server/discover
        print("\n\n########## 第 1 步：server/discover 能力发现 ##########")
        result = client.request("server/discover")
        print("\n=> 解析：服务器支持版本 %s，能力 %s"
              % (result.get("supportedVersions"), list(result.get("capabilities", {}))))

        # 2) 发现工具
        print("\n\n########## 第 2 步：tools/list 发现工具 ##########")
        result = client.request("tools/list")
        tools = result.get("tools", [])
        print("\n=> 解析：发现 %d 个工具：%s"
              % (len(tools), ", ".join(t["name"] for t in tools)))

        # 3) 调用工具（成功）
        print("\n\n########## 第 3 步：tools/call 调用 add(2, 3) ##########")
        result = client.request("tools/call",
                                {"name": "add", "arguments": {"a": 2, "b": 3}})
        print("\n=> 解析：结构化输出 structuredContent = %s"
              % result.get("structuredContent"))

        # 4) 调用工具（业务失败）：演示 isError=true 的“模型可自我纠正”错误
        print("\n\n########## 第 4 步：tools/call 故意传错参数（a='x'） ##########")
        result = client.request("tools/call",
                                {"name": "add", "arguments": {"a": "x", "b": 3}})
        print("\n=> 解析：isError = %s，错误文本 = %r"
              % (result.get("isError"),
                 result.get("content", [{}])[0].get("text")))

        # 5) 调用不存在的工具：演示 JSON-RPC 协议级错误
        print("\n\n########## 第 5 步：tools/call 调用不存在的工具 ##########")
        err = client.request("tools/call", {"name": "nope", "arguments": {}})
        print("\n=> 解析：协议级错误 code = %s，message = %r"
              % (err.get("code"), err.get("message")))

        # 6) 资源
        print("\n\n########## 第 6 步：resources/list + resources/read ##########")
        result = client.request("resources/list")
        uris = [r["uri"] for r in result.get("resources", [])]
        print("\n=> 解析：资源 URI = %s" % uris)
        result = client.request("resources/read", {"uri": uris[0]})
        text = result.get("contents", [{}])[0].get("text", "")
        print("\n=> 解析：读到的内容前 40 字：%r" % text[:40])

        # 7) 提示词
        print("\n\n########## 第 7 步：prompts/list + prompts/get ##########")
        result = client.request("prompts/list")
        print("\n=> 解析：提示词 = %s"
              % [p["name"] for p in result.get("prompts", [])])
        result = client.request("prompts/get",
                                {"name": "greet", "arguments": {"name": "MCP 学习者"}})
        msg = result.get("messages", [{}])[0]
        print("\n=> 解析：渲染出的消息 role=%s，text=%r"
              % (msg.get("role"), msg.get("content", {}).get("text")))

        # 8) 畸形请求：不发 _meta，看服务器如何拒绝（无状态强制校验）
        print("\n\n########## 第 8 步：故意发送缺少 _meta 的畸形请求 ##########")
        self_next = client._next_id + 1
        bad = {"jsonrpc": "2.0", "id": self_next, "method": "tools/list",
               "params": {}}
        client._show("--> 客户端发出（畸形请求）", bad)
        client._write_line(bad)
        while True:
            message = json.loads(client.proc.stdout.readline())
            if message.get("id") == self_next:
                client._show("<-- 服务器响应", message)
                err = message.get("error", {})
                print("\n=> 解析：被拒绝，code = %s（-32602 Invalid params）"
                      % err.get("code"))
                break

        # 9) 通知演示
        print("\n\n########## 第 9 步：发送 notifications/cancelled 通知 ##########")
        client.notify("notifications/cancelled", {"requestId": 1})
        print("\n（通知没有 id，服务器不会回复；其 stderr 会打印一行日志）")

        print("\n\n演示结束。服务器 stdin 关闭后应自行退出。")
    finally:
        client.close()


if __name__ == "__main__":
    main()
