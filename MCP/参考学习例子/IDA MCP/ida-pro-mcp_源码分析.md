# ida-pro-mcp 源码分析：MCP 工具调用全链路

> **源码 GitHub 地址：<https://github.com/mrexodia/ida-pro-mcp>**
>
> 本目录下的 `ida-pro-mcp/` 文件夹是它的本地克隆，**不入库**（已被 `.gitignore` 排除）。
> 以后想看源码 / 更新版本，直接：
>
> ```bash
> git clone https://github.com/mrexodia/ida-pro-mcp.git
> cd ida-pro-mcp && git pull
> ```
>
> | 项目信息 | 值 |
> |------|------|
> | GitHub | https://github.com/mrexodia/ida-pro-mcp |
> | 作者 | Duncan Ogilvie（mrexodia，x64dbg 作者） |
> | 协议 | MIT License（Copyright 2025） |
> | 语言 | 纯 Python（零第三方运行时依赖） |
> | 分析时版本 | commit `cae2fa8`（2026-09-20） |
> | 规模 | 98 个工具（12 个 `api_*.py` 模块）+ 资源/提示词；自研 MCP 协议实现 `zeromcp` |
> | 要求 | Python 3.11+，IDA Pro 8.3+（不支持 IDA Free） |

> 本文是 [MCP/README.md](../../README.md) 的配套实战案例，协议概念以 README 第 2~4 章为准。姊妹篇：[cheatengine-mcp-bridge 源码分析](../Cheat%20engine%20MCP/cheatengine-mcp-bridge_源码分析.md)。

---

## 一句话总评

**「手写 MCP 协议 + 进程内 HTTP 服务器 + 主线程封送」的全栈范本**。它不依赖官方 SDK，用 ~1400 行的 `zeromcp` 把 JSON-RPC 分发、工具 schema 反射生成、三种传输（stdio / Streamable HTTP / SSE）全部自己实现，并且把「宿主进程有 GUI 主线程」这个 IDA 特有的约束解决得非常彻底。想深入 MCP 协议细节、或者要给**任何单线程 GUI 应用**写 MCP 桥，这个仓库就是最佳参考。

---

## 1. 总体架构：两个进程，两种角色

```
 MCP 宿主（Claude / Cursor / ZCode…）
      │ stdio
      ▼
┌─────────────────────────────────────────────┐
│ server.py —— 独立 stdio 代理进程              │
│  McpServer("ida-pro-mcp")（zeromcp）          │
│  registry.dispatch 被换成 dispatch_proxy：    │
│   · initialize / 通知 → 本地应答              │
│   · 其余全部 POST 转发到 IDA                  │
└───────┬─────────────────────────────────────┘
        │ HTTP POST /mcp（JSON-RPC）127.0.0.1:13337
        ▼
┌─────────────────────────────────────────────┐
│ IDA Pro 进程（ida_mcp 插件包）                │
│  McpHttpRequestHandler（ThreadingHTTPServer） │
│   → JsonRpcRegistry.dispatch                 │
│   → _mcp_tools_call → @tool 函数             │
│   → @idasync → idaapi.execute_sync(MFF_WRITE)│
│   → IDA 主线程执行 → IDA SDK / Hex-Rays      │
└─────────────────────────────────────────────┘
```

为什么拆两个进程？

- IDA 插件**只能活在 IDA 进程里**（要用 `idaapi`），所以 HTTP 服务器必须内嵌在 IDA 中；
- 但 MCP 宿主最通用、最不容易坏的传输是 **stdio 子进程**，于是 `server.py` 作为一个几乎零逻辑的「协议翻译器」跑在外面；
- `initialize` 在代理本地应答（客户端拿到 serverInfo 与能力），工具调用才转发——客户端完全感知不到后面还有一跳 HTTP。
- `--transport http://...` 可以跳过 stdio 直连 IDA 的 HTTP 端点（配合 `npx @modelcontextprotocol/inspector` 调试）。

**自动发现**：IDA 插件启动时把 `(host, port, pid, binary, idb_path)` 写进发现文件（`discovery.py`），`server.py` 启动时 `discover_instances()` 扫描，多个 IDA 开着时自动选第一个并提示可用 `--ida-rpc` 指定。

## 2. 工具调用全链路（核心）

以宿主调用 `lookup_funcs` 为例。

### 第 0 步：工具注册 —— `@tool` 只做一件事

`rpc.py:179`：

```python
def tool(func):
    return MCP_SERVER.tool(func)     # = self.tools.method(func)
```

`JsonRpcRegistry.method`（`zeromcp/jsonrpc.py:113`）：

```python
def method(self, func, name=None):
    self.methods[name or func.__name__] = func
    return func
```

**函数名 = 工具名**，没有任何包装。12 个 `api_*.py` 模块被 `ida_mcp/__init__.py` import 的瞬间，98 个工具就全部注册进 `MCP_SERVER.tools.methods` 了。

### 第 1 步：`tools/list` —— 反射生成 schema

`McpServer._generate_tool_schema`（`zeromcp/mcp.py:1352`）用 `inspect.signature + get_type_hints(include_extras=True)` 从函数定义推导出完整 schema：

```python
@tool
@idasync
def lookup_funcs(
    queries: Annotated[list[str] | str, "Address(es) or name(s)"],
) -> list[LookupFuncResult]:
    """Get functions by address or name (auto-detects)"""
```

推导规则（全部值得学）：

| 函数元素 | 生成的 schema 部分 |
|----------|--------------------|
| 函数名 | `"name"` |
| docstring | `"description"`（工具描述即提示词） |
| 参数类型标注（含 `Annotated` 的说明文字、`TypedDict`、`Union`） | `inputSchema.properties[...]` |
| 无默认值的参数 | `inputSchema.required` |
| 有默认值的参数 | 写进 properties 的 `"default"`（不可 JSON 序列化的默认值静默丢弃） |
| 返回类型标注 | `outputSchema`；非 object 的返回值包成 `{"result": ...}` 保证根节点是 object（MCP 规范要求） |

结果类型用的是 `TypedDict`（如 `LookupFuncResult`），所以 `structuredContent` 输出有**可机读的强 schema**，MCP Inspector 会真的拿它做校验。

### 第 2 步：`tools/call` —— 套娃式分发

`McpServer._mcp_tools_call`（`zeromcp/mcp.py:1039`）做了一个很妙的复用：**把工具调用再包成一个内部 JSON-RPC 请求**，丢回给 tools registry 自己的 `dispatch`：

```python
tool_response = self.tools.dispatch({
    "jsonrpc": "2.0", "method": name,      # method 就是工具名！
    "params": arguments, "id": None,
})
```

于是协议方法（tools/call）和工具函数走**同一条**参数校验代码 `_call()`，一套逻辑两处受益：

- `_call()`（`jsonrpc.py:201`）缓存 `inspect.signature` 与类型标注，逐参数校验：
  - 必填缺失 / 多余参数 → `-32602`；
  - `Union` 类型逐个分支试匹配；`int → float` 自动提升；`list[X]`/`dict[K,V]` 泛型检查；`TypedDict` 检查为 dict；
  - 一个针对性 hack：schema 说是 object 但某些客户端（Claude Code）发来「字符串化的 JSON」，就先 `json.loads` 再匹配；
- 校验通过 → `func(**validated_params)` 真正调用工具函数。

错误分级（README 2.1 说的两类错误的活例子）：

- **业务错误**：`_call` 抛异常 → `_mcp_tools_call` 返回 `{"content":[text],"isError":true}`，错误文本写给模型自我纠正；
- **协议错误**：方法不存在 → JSON-RPC `error -32601`。

### 第 3 步：`@idasync` —— 封送回 IDA 主线程（本项目的灵魂）

IDA SDK **不是线程安全的**，而 HTTP 请求跑在 `ThreadingHTTPServer` 的 worker 线程上。`sync.py:257` 的 `@idasync` 负责把函数体搬回主线程：

```python
idaapi.execute_sync(runned, idaapi.MFF_WRITE)   # 排队到 IDA 主线程，MFF_WRITE=写权限
res = res_container.get()                        # 阻塞等结果经 Queue 送回
```

`_sync_wrapper`（`sync.py:96`）细节：

- **batch 模式**：执行期间 `idc.batch(1)`，抑制 IDA 弹窗（完成后恢复原值，`@keep_batch` 可豁免）；
- **重入保护**：`call_stack`（LifoQueue）非空说明正在重入 → 通过 Queue 回传 `IDASyncError` 而不是 raise（`execute_sync` 会吞掉回调里的异常，raise 会让请求线程**永久卡死**——issue #217 的教训）。

超时与取消（`sync_wrapper`，`sync.py:173`）是三层兜底：

1. **deadline**：默认 60s（环境变量 `IDA_MCP_TOOL_TIMEOUT_SEC`，`@tool_timeout(n)` 按工具覆盖）；
2. **原生取消**：`threading.Timer` 到点调 `ida_kernwin.set_cancelled()`——IDA SDK 的搜索/反编译等函数会轮询 `user_cancelled()` 并自己退出，比 Python 层强杀优雅得多；
3. **Python 层检查点**：`sys.setprofile(profilefunc)` 逐函数调用检查 cancel 事件（`notifications/cancelled` → `cancel_request(id)` → `threading.Event.set()`）与 deadline，超时抛 `IDASyncError`，请求级取消抛 `CancelledError`（JSON-RPC `-32800`）。

工具函数还可以调 `get_tool_deadline()` 自查剩余时间，主动返回部分结果。

### 第 4 步：idalib 无头模式 —— mainthread.py

`idalib`（无 GUI 的 IDA 库模式）**没有 UI 事件循环**，`execute_sync` 永远不会被派发。`mainthread.py` 的 `MainThreadPump` 换了思路：**让主线程自己停在一个队列上**——

```python
# idalib_server.py 在主线程调用：
pump.run()      # 死循环 drain 队列
# HTTP 线程提交任务：
pump.submit(fn, label=..., timeout=...)   # → PumpBusyError 若主线程忙
```

`@idasync` 里先探测 `pump.active`：有 pump 走 `submit`，没有（GUI 模式）走 `execute_sync`。同一个装饰器兼容两种宿主形态。

### 全链路一图流

```
tools/call(lookup_funcs)
  → MCP_SERVER.registry.dispatch（jsonrpc.py 解析 JSON-RPC）
  → _mcp_tools_call → tools.dispatch（内部 JSON-RPC，同名分发）
  → _call：签名+类型反射校验 → lookup_funcs(**args)
  → @idasync → execute_sync(MFF_WRITE) 排队
  → IDA 主线程：batch(1) → deadline/取消布防 → 函数体调 idaapi/idautils/idc
  → 结果经 Queue 回 HTTP 线程 → _limit_output_response
  → structuredContent + content → HTTP 200 JSON → stdio 代理回传宿主
```

## 3. zeromcp：零依赖手写 MCP 的精读地图

`zeromcp/` 是理解 MCP 协议最直观的一手材料（对照官方 SDK 的黑盒）：

| 文件 | 内容 | 关键点 |
|------|------|--------|
| `jsonrpc.py` (387 行) | JSON-RPC 2.0 注册表 | `dispatch()`：解析→查表→`_call` 反射校验→结果/错误包封；thread-local 保存当前请求 id 与取消事件 |
| `mcp.py` (1408 行) | MCP 协议 + 传输 | 方法表：`ping/initialize/tools/* /resources/* /prompts/* /notifications/*`；`stdio()` 逐行循环；`serve()` ThreadingHTTPServer |
| — `_handle_mcp_post` | Streamable HTTP | 校验/签发 `Mcp-Session-Id`；响应 200 JSON 或通知 202 空体；协议版本 2025-06-18 |
| — `_handle_sse_*` | 旧版 SSE | `GET /sse` 长流 + `POST /sse?session=` 回传，协议版本 2024-11-05 |
| — 安全 | | CORS 仅回环、Host 头校验防 DNS rebinding、body ≤ 10MB、gzip/deflate 解压、Windows 用 `SO_EXCLUSIVEADDRUSE` 防端口劫持 |

会话与状态：HTTP 会话是「带 TTL 的 id 集合」（默认 24h，上限 4096），不是有状态连接——与 README 第 3.1 节讲的无状态化方向一致，只是该实现仍基于 2025-06-18 版协议（读源码时注意这处时代差异）。

## 4. 值得抄的工程细节

| # | 细节 | 位置 | 为什么重要 |
|---|------|------|-----------|
| 1 | **输出限流 + 下载兜底** | `rpc.py:20-171` | 工具结果 > 50000 字符时：缓存全文（`/output/{uuid}.json` 端点）+ 返回分层截断的预览 + `_meta.ida_mcp.download_url` + `curl` 提示。**保护 LLM 上下文**的正确姿势（CE 桥用分页达到同一目的） |
| 2 | `tools/call` 结果 patch | `rpc.py:158-171` | 不改 `zeromcp`，直接替换 `registry.methods["tools/call"]` 加后处理——对第三方库做增强的最小侵入手法（项目里 dispatch 换成 proxy 同理） |
| 3 | 端口冲突自动 +1 | `ida_mcp.py:290-306` | `serve` 失败（errno 48/98/10048）就试下一个端口，最多 +100；配合发现文件，多开 IDA 互不干扰 |
| 4 | 插件热重载 | `unload_package()` | 从 `sys.modules` 删掉整包再 import，IDA 插件开发不用重启 IDA |
| 5 | SIGPIPE 忽略 | `ida_mcp/__init__.py:17` | 客户端断连时 HTTP 写回会触发 SIGPIPE 杀掉整个 IDA——嵌入 Python 里 CPython 的默认 SIG_IGN 不可靠，必须自己再设一遍 |
| 6 | 双通道取消 | `sync.py` + `jsonrpc.py` | SDK 级 `set_cancelled()`（IDA 原生协作退出）+ profile 检查点（Python 级硬超时），长跑工具不会卡死宿主 |
| 7 | `@ext("dbg")` 扩展分组 | `rpc.py:192` + `mcp.py:1020` | 调试器类工具默认隐藏，`?ext=dbg` 才出现在 `tools/list`——给「高危/可选能力」做渐进披露的轻量方案 |
| 8 | 返回 TypedDict | 各 `api_*.py` | 输出即文档即校验：outputSchema 自动生成，`structuredContent` 结构稳定，测试框架可直接断言形状 |

## 5. 与 cheatengine-mcp-bridge 的对照（两篇合读）

| 维度 | cheatengine-mcp-bridge | ida-pro-mcp |
|------|------------------------|-------------|
| MCP 协议实现 | 官方 SDK（FastMCP） | 手写 zeromcp，零依赖 |
| 服务器位置 | 独立 Python 进程 | IDA 进程内（+ 外部 stdio 代理） |
| 到宿主 app 的传输 | 命名管道 / TCP + 长度帧 JSON-RPC | HTTP POST /mcp（JSON-RPC 原生） |
| 跨语言 | Python ↔ Lua | 纯 Python |
| 主线程封送 | `thread.synchronize`（CE GUI 线程） | `execute_sync`（GUI）/ `MainThreadPump`（idalib） |
| 输出控制 | 分页参数（offset/limit） | 50k 字符截断 + 下载 URL |
| 工具规模 | 175 个，一层薄封装 | 98 个，带 TypedDict 输出 schema |
| 共同点 | 工具描述即提示词；错误文本写给模型自我纠正；stdout/协议流纯净；帧边界/参数校验严谨 | |

两份源码合起来正好覆盖 README 第 7 章手写实现的全部知识点，且各自给出了「宿主应用不是 Python 服务」时的两种主流桥接形态：**外挂 RPC 进程**（CE）与**进程内嵌服务器**（IDA）。

## 6. 接入宿主的配置（配合 README 4.4）

推荐先用项目自带的安装器（会写好 stdio 配置并自动装 IDA 插件）：

```bash
pip install ida-pro-mcp
ida-pro-mcp --install claude    # 或 cursor / vscode / cline …；--list-clients 查看全部
```

手写等价配置（stdio 代理模式）：

```json
{
  "mcpServers": {
    "ida-pro-mcp": {
      "command": "E:\\path\\to\\python.exe",
      "args": ["-m", "ida_pro_mcp", "server"],
      "env": {}
    }
  }
}
```

或直连 HTTP（适合 Inspector 调试）：先在 IDA 里 `Edit → Plugins → MCP (Ctrl-Alt-M)` 启动服务，再 `ida-pro-mcp --transport http://127.0.0.1:13374`。

## 7. 源码文件清单（本地克隆内）

| 文件 | 说明 |
|------|------|
| `src/ida_pro_mcp/server.py` | stdio 代理入口：dispatch 拦截转发、IDA 实例自动发现、安装器 CLI |
| `src/ida_pro_mcp/ida_mcp.py` | IDA 插件加载器（PLUGIN_ENTRY）：配置持久化、端口探测、启停 |
| `src/ida_pro_mcp/ida_mcp/__init__.py` | 插件包聚合：import 12 个 api 模块完成工具注册 |
| `src/ida_pro_mcp/ida_mcp/rpc.py` | `MCP_SERVER` 单例、`@tool/@resource/@unsafe/@ext` 装饰器、输出限流 |
| `src/ida_pro_mcp/ida_mcp/sync.py` | `@idasync`：主线程封送、batch、超时、双通道取消 |
| `src/ida_pro_mcp/ida_mcp/mainthread.py` | idalib 无头模式的主线程任务泵 |
| `src/ida_pro_mcp/ida_mcp/api_*.py` | 12 个模块 98 个工具（core/analysis/memory/types/modify/stack/debug/python/survey/composite/sigmaker/resources） |
| `src/ida_pro_mcp/ida_mcp/zeromcp/` | 手写 MCP：`jsonrpc.py`（分发/校验）+ `mcp.py`（协议方法/三种传输/安全） |
| `src/ida_pro_mcp/ida_mcp/discovery.py` | 多实例发现（文件系统注册表） |
| `src/ida_pro_mcp/ida_mcp/trace.py` | 每次 tools/call 记录进 IDB netnode（审计） |
| `tests/`、`skills/`、`devdocs/` | 规范级测试（MCP spec 合规）、idapython 技能文档、开发笔记 |

## 8. 学习检验清单

读完本文应能回答：

1. 为什么 `tools/call` 要把工具调用再包成内部 JSON-RPC？好处是什么？
2. `inputSchema` 是从函数的哪些元素推导出来的？`Annotated` 的第二项去哪了？
3. `execute_sync` 回调里直接 raise 会发生什么？项目怎么绕开这个坑（issue #217）？
4. 请求取消有哪两层机制？`sys.setprofile` 为什么能做到逐函数检查？
5. idalib 模式下 `execute_sync` 为什么失效？`MainThreadPump` 怎么解决？
6. 一次返回 10MB 的工具结果，最终到模型手里的是什么？
