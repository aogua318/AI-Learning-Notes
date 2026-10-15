#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe.py —— 本地调试探针：不经宿主，直接和本地 MCP 服务器对话
================================================================

用途：排查「宿主里工具不出现」类问题时，先确认服务器本身是好的。
把 server.py 当子进程拉起，连发三条请求（server/discover、tools/list、
tools/call），打印原始响应。全程不依赖任何第三方包。

用法：
    python probe.py                # 探测同目录的 server.py
    python probe.py path/to/其他服务器.py
"""

import json
import subprocess
import sys

PROTOCOL_VERSION = "2026-07-28"


def meta():
    """每个请求必带的 _meta（2026-07-28 无状态协议）。"""
    return {
        "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
        "io.modelcontextprotocol/clientInfo": {"name": "probe", "version": "1.0.0"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }


def main():
    server_script = sys.argv[1] if len(sys.argv) > 1 else "server.py"
    print("探测目标: %s\n" % server_script)

    proc = subprocess.Popen(
        [sys.executable, server_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )

    # 依次发送三条请求，读三条响应
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": meta()}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {"_meta": meta()}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "add", "arguments": {"a": 2, "b": 3}, "_meta": meta()}},
    ]

    ok = True
    try:
        for req in requests:
            print("--> %s" % json.dumps(req, ensure_ascii=False))
            proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            if not line:
                print("<-- （无响应：服务器可能已退出，往下看 stderr）")
                ok = False
                break
            print("<-- %s\n" % line.strip())
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    # 把服务器的 stderr 原样展示——日志里通常藏着真正的原因
    stderr_text = proc.stderr.read()
    if stderr_text:
        print("---- 服务器 stderr ----")
        print(stderr_text)

    print("结论: %s" % ("服务器响应正常，问题大概率在宿主配置/重启上"
                        if ok else "服务器无响应，先按上面的 stderr 修服务器"))


if __name__ == "__main__":
    main()
