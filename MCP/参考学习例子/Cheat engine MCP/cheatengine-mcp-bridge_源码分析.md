# cheatengine-mcp-bridge 源码分析：MCP 工具调用全链路

> **源码 GitHub 地址：<https://github.com/miscusi-peek/cheatengine-mcp-bridge>**
>
> 本目录下的 `cheatengine-mcp-bridge/` 文件夹是它的本地克隆，**不入库**（已被 `.gitignore` 排除）。
> 以后想看源码 / 更新版本，直接：
>
> ```bash
> git clone https://github.com/miscusi-peek/cheatengine-mcp-bridge.git
> cd cheatengine-mcp-bridge && git pull
> ```
>
> | 项目信息 | 值 |
> |------|------|
> | GitHub | https://github.com/miscusi-peek/cheatengine-mcp-bridge |
> | 协议 | MIT License（Copyright 2025 miscusi-peek） |
> | 语言 | Python（MCP 服务器）+ Lua（CE 内脚本） |
> | 分析时版本 | commit `6bd7ce9`（2026-08-14），CE 版本徽标 12.0.0，协议版本 v12/v99 |
> | 规模 | 175 个 MCP 工具（`@mcp.tool()`），Lua 桥约 6100 行 |
> | 依赖 | `mcp`（官方 SDK，FastMCP）、`pywin32`（管道模式才需要） |

> 本文是 [MCP/README.md](../../README.md) 的配套实战案例，协议概念（tools/list、tools/call、stdio 等）以 README 第 2~4 章为准。

---

## 一句话总评

**「官方 FastMCP SDK + 自定义二进制帧管道 + CE 内 Lua RPC」的三层桥**。它演示了一个典型问题怎么拆：MCP 工具的执行环境（Cheat Engine）不能直接跑 Python MCP 服务器，于是中间加了一段「MCP 服务器进程 ↔ 命名管道/TCP ↔ CE 内嵌 Lua」的 RPC 链路，MCP 工具全部退化成**薄封装的远程调用**。学会了这套拆法，任何「能力在别的进程/别的语言里」的场景都能套用。

---

## 1. 总体架构

```
 LLM / MCP 宿主（Claude Desktop、Cursor、ZCode……）
        │  stdio（逐行 JSON-RPC 2.0，UTF-8）
        ▼
┌────────────────────────────────────────────────┐
│ mcp_cheatengine.py   ← FastMCP 服务器进程        │
│  ① 175 个 @mcp.tool() 薄封装函数                 │
│  ② CEBridgeClient：send_command(method,params)  │
└───────┬────────────────────────────────────────┘
        │  自定义帧协议：4 字节小端长度头 + JSON-RPC 体
        │  传输 A：Windows 命名管道 \\.\pipe\CE_MCP_Bridge_v99（默认）
        │  传输 B：TCP 127.0.0.1:9876 ──► ce_tcp_relay.py ──► 同一根管道
        ▼
┌────────────────────────────────────────────────┐
│ ce_mcp_bridge.lua   ← 运行在 Cheat Engine 内    │
│  ① createPipe 建管道服务端（worker 线程）        │
│  ② thread.synchronize 切回 GUI 主线程执行        │
│  ③ commandHandlers[method] → cmd_* 函数          │
│  ④ 调 CE Lua API → 读/写/扫描目标进程内存         │
└────────────────────────────────────────────────┘
```

三个角色各管一段协议，互不渗透：

| 层 | 文件 | 职责 | 协议 |
|----|------|------|------|
| MCP 层 | `MCP_Server/mcp_cheatengine.py` | 对宿主暴露 175 个工具 | MCP over stdio |
| 传输层 | 同上（客户端）+ `ce_tcp_relay.py`（可选中继） | 把「方法名+参数」送进 CE | 4 字节长度帧 + JSON-RPC |
| 执行层 | `MCP_Server/ce_mcp_bridge.lua` | 真正操作内存/调试器 | 收 JSON-RPC，调 CE Lua API |

## 2. 工具调用全链路（核心）

以宿主调用 `read_integer("0x1234", "dword")` 为例，从 LLM 决策到 CE 读出内存，共 7 步：

### 第 0 步：宿主发现工具 —— `tools/list`

FastMCP 在 `@mcp.tool()` 装饰时就把函数注册进了工具表（`mcp_cheatengine.py:455` 起）：

```python
mcp = FastMCP(MCP_SERVER_NAME)          # 服务器名 "cheatengine"

@mcp.tool()
def read_integer(address: str, type: str = "dword") -> str:
    """Read a number from memory. Types: byte, word, dword, qword, float, double."""
    return format_result(ce_client.send_command("read_integer", {"address": address, "type": type}))
```

宿主发 `tools/list` 时，FastMCP 自动完成：

- 函数名 → 工具名 `read_integer`；
- **docstring → `description`**（工具描述即提示词，LLM 靠它选工具）；
- **类型标注 → `inputSchema`**（`address: str` → `{"type":"string"}`，有默认值的参数变可选）；
- 返回类型 `str` → 按「文本内容块」返回。

对照我们手写的 `server.py`（README 第 7 章）：`TOOLS` 纯数据列表里那一坨 JSON Schema，FastMCP 全部从函数签名**推导**出来了——这就是 SDK 的价值。

### 第 1 步：宿主发 `tools/call`

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call",
 "params":{"name":"read_integer","arguments":{"address":"0x1234","type":"dword"}}}
```

FastMCP 校验参数（缺必填、类型不符都会拦下）后，调用对应的 Python 函数。

### 第 2 步：工具函数 → `send_command`（MCP 层退化成 RPC 客户端）

每个工具函数体都只有一行：把 MCP 参数翻译成 CE 方法名 + 参数字典：

```python
ce_client.send_command("read_integer", {"address": address, "type": type})
```

`send_command`（`mcp_cheatengine.py:259`）内做了四件事，全部是**通用可靠性工程**，值得整段抄走：

1. **自动重连**：`if not self.connected: self.connect()`，失败重试 2 次；
2. **构造 JSON-RPC**：`{"jsonrpc":"2.0","method":...,"params":...,"id":毫秒时间戳}`；
3. **超时控制**：交换动作放进 daemon 线程，`worker.join(timeout)` 等不到就 `close()` 并抛
   `TimeoutError`。超时秒数来自环境变量 `CE_MCP_TIMEOUT`（默认 30s，`<=0` 禁用）；
4. **错误归一**：CE 返回的 JSON-RPC `error` 被转成 `{"success": false, "error": ...}`，
   让 MCP 层永远走正常返回（模型读到错误文本能自我纠正，而不是拿到协议级报错）。

### 第 3 步：帧协议（长度前缀）

管道/TCP 上不是裸 JSON，而是 **4 字节小端长度头 + JSON 体**：

```python
header = struct.pack('<I', len(req_json))      # 发送
# 响应侧：先 _read_exact(4) 拿长度，再 _read_exact(resp_len) 拿 body
```

这是 TCP 粘包问题的教科书解法，两端（Python / Lua）都按同一规则封帧/拆帧。还有防护：
响应超过 `MAX_RESPONSE_SIZE_BYTES = 32MB` 直接 `ConnectionError`，防止恶意/异常响应把内存吃爆。

### 第 4 步：传输层双实现

`CEBridgeClient` 基类定义了 `_exchange_once` 抽象，两个子类只换「怎么读写字节」：

| 实现 | 场景 | 关键点 |
|------|------|--------|
| `CENamedPipeBridgeClient` | Windows 本机，默认 | `win32file.CreateFile` 打开 `\\.\pipe\CE_MCP_Bridge_v99` |
| `CETcpBridgeClient` | WSL / 容器 / 跨机器 | 连 `CE_MCP_HOST:CE_MCP_PORT`（默认 9876） |

环境变量 `CE_MCP_TRANSPORT=pipe|tcp` 切换（`_create_bridge_client()`，`mcp_cheatengine.py:441`）。

TCP 模式下，`ce_tcp_relay.py`（181 行，短小精悍）负责 **TCP ↔ 命名管道** 的双向中继：

- `socketserver.TCPServer` 每个连接建一条独立管道，收到帧就原样转发、收到回包就原样写回；
- 非回环地址绑定会打警告——**根命名管道等价于给外部机器开了一个「任意代码执行」后门**（README 第 9 章安全的活例子）。

### 第 5 步：Lua 管道服务（CE 内部）

`ce_mcp_bridge.lua` 末段（5975 行起）：

- **worker 线程** 里 `createPipe(PIPE_NAME, 262144, 262144)` 建管道并阻塞式 `acceptConnection()`——放线程里是为了**不卡 CE 的 GUI**（注释写明：v10 用 Timer 架构导致 GUI 冻结，v12 改成线程）；
- 读 4 字节头（Lua 里手工 `b1 + b2*256 + b3*65536 + b4*16777216` 解小端）、读 payload；
- **`thread.synchronize(function() response = executeCommand(payload) end)`**——这是整个 Lua 桥最关键的一行：CE 的 Lua API 不是线程安全的，必须切回 GUI 主线程执行。worker 线程在这里**暂停等待**，主线程跑完拿到 response 后再由 worker 写回管道。

### 第 6 步：Lua 命令分发

```lua
local function executeCommand(jsonRequest)
    local ok, request = pcall(json.decode, jsonRequest)
    if not ok then return json.encode({jsonrpc="2.0", error={code=-32700, ...}}) end

    local handler = commandHandlers[method]           -- 方法名 → cmd_* 函数分发表
    if not handler then return json.encode({jsonrpc="2.0", error={code=-32601, ...}}) end

    local ok2, result = pcall(handler, params)        -- 业务异常不炸连接
    if not ok2 then return json.encode({jsonrpc="2.0", error={code=-32603, ...}}) end

    return json.encode({jsonrpc="2.0", result=result, id=id})
end
```

`commandHandlers` 表（5836 行附近起）注册了 175 个 `cmd_*` 函数（与 Python 端 175 个工具一一对应），每个函数用 CE Lua API
（`readInteger`、`AOBScan`、`debug_setBreakpoint`、`executeCodeEx`……）干活。因为 **Lua 没有内置 JSON**，文件前段还手写了一份 JSON encode/decode（417~527 行）。

### 第 7 步：回包

Lua 的 JSON-RPC 响应 → worker 线程封帧写回 → Python `_decode_response` 解帧 → `send_command`
剥出 `result` → 工具函数 `format_result()` 序列化成 JSON 字符串 → FastMCP 包成 MCP `content` 文本块 → 宿主回喂 LLM。

### 调用链一图流

```
LLM 决策 → tools/call → FastMCP 校验 → read_integer()
  → send_command: 连接检查→JSON-RPC→超时线程→重试
  → struct.pack('<I', len) + body → 命名管道(或 TCP→relay→管道)
  → Lua worker 读帧 → thread.synchronize 切主线程
  → executeCommand → commandHandlers["read_integer"] → cmd_read_integer
  → CE Lua API 读内存 → json.encode 回包 → 原路逐层返回
```

## 3. 值得抄的工程细节

| # | 细节 | 位置 | 为什么重要 |
|---|------|------|-----------|
| 1 | **Windows CRLF 猴子补丁** | `mcp_cheatengine.py:1-105` | MCP SDK 的 `stdio_server` 在 Windows 输出 `\r\n`，宿主报 "invalid trailing data"。项目在 import FastMCP **之前**重写了 `stdio_server`（`TextIOWrapper(..., newline='\n')`），并且连 `fastmcp_server` 模块内已绑定的引用也一并替换。我们 README 4.2「Windows 编码坑」的完整解法范本 |
| 2 | **stdout 纯净保护** | `mcp_cheatengine.py:82-118` | import 阶段先把 `sys.stdout` 整个重定向到 stderr，等「可能乱 print 的库」全部导入完再恢复。第三方库一个 banner 就能毁掉 stdio 协议流，这是最稳的防法 |
| 3 | 每个工具都是**一行薄封装** | 全文件 | MCP 参数 → CE 方法名的翻译层只有一层，没有业务逻辑堆积，175 个工具依然可读 |
| 4 | 超时用**独立线程 + join** | `_exchange_with_timeout` | 管道阻塞读无法设超时，就用 daemon 线程硬等；超时后必须 `close()` 连接，否则下一次调用会读到上一条的残包 |
| 5 | 错误两级分离 | `send_command` | 协议错误（JSON-RPC error）在桥内转成 `{"success":false,...}` 业务返回，模型永远拿到可读文本 |
| 6 | Lua 侧 `thread.synchronize` | `ce_mcp_bridge.lua:6029` | 跨线程调用 GUI 库的标准姿势（对照 IDA 的 `execute_sync`，见姊妹篇） |
| 7 | 分页参数贯穿始终 | `enum_modules`/`get_scan_results` 等 | `offset/limit` 上限 10000，避免一次扫描几十万结果撑爆 LLM 上下文（对照 ida-pro-mcp 的输出截断，两家想到一起去了） |

## 4. 接入宿主的配置（配合 README 4.4）

```json
{
  "mcpServers": {
    "cheatengine": {
      "command": "E:\\path\\to\\python.exe",
      "args": ["E:\\path\\to\\MCP_Server\\mcp_cheatengine.py"],
      "env": {
        "CE_MCP_TRANSPORT": "pipe",
        "CE_MCP_TIMEOUT": "30"
      }
    }
  }
}
```

前置步骤：Cheat Engine 里加载并运行 `ce_mcp_bridge.lua`（或 Table 自带脚本），它会建好管道服务端。跨 WSL/容器时把 `CE_MCP_TRANSPORT` 改 `tcp`，并在 Windows 侧跑 `python ce_tcp_relay.py`。

## 5. 源码文件清单（本地克隆内）

| 文件 | 行数 | 说明 |
|------|------|------|
| `MCP_Server/mcp_cheatengine.py` | ~2350 | FastMCP 服务器：175 个工具 + 桥客户端（管道/TCP）+ Windows 补丁 |
| `MCP_Server/ce_mcp_bridge.lua` | ~6100 | CE 内脚本：管道服务、JSON 实现、175 个 cmd_* 处理器 |
| `MCP_Server/ce_tcp_relay.py` | 181 | TCP↔命名管道中继（WSL/容器/远程场景） |
| `MCP_Server/test_mcp.py` | - | 直连桥的冒烟测试（不经 MCP） |
| `AI_Context/*.md` | - | 给 AI 看的上下文文档：CE Lua API 文档、命令参考、指针工具设计 |
| `README.md` / `CLAUDE.md` / `AGENTS.md` | - | 使用文档与 Agent 约定 |

## 6. 学习检验清单

读完本文应能回答：

1. `tools/list` 返回的 schema 是谁生成的？生成时机？
2. 为什么 `send_command` 超时后必须先 `close()` 再抛异常？
3. 帧协议为什么需要长度头？Lua 端怎么解 4 字节小端？
4. 为什么 Lua 里读管道放 worker 线程、执行命令却要 `thread.synchronize`？
5. 如果 CE 卡死（主线程忙），这条链路哪一层先超时？超时后连接状态如何？
