# MCP 学习文档：从原理到上手（重点：本地调用）

> **MCP（Model Context Protocol，模型上下文协议）** 是一个由 Anthropic 于 2024 年 11 月开源的开放协议，用来标准化「AI 应用」与「外部数据源 / 工具」之间的集成方式。
>
> 本文的目标：让你**理解 MCP 为什么存在、协议如何工作、以及如何亲手写出一个 MCP 服务器并在本地跑起来、接进真实客户端**。文档以最新规范 **2026-07-28 版**为准（写于 2026 年 9 月），并附版本演进史帮助你读懂网上基于旧版规范的资料。
>
> **阅读建议**：第 0~3 章讲原理（为什么、是什么），**第 4 章「本地调用完全指南」是重点**——绝大多数人用 MCP 的方式就是「在本地跑一个服务器、接进 Claude Desktop / Cursor 等宿主」，这一章把这条链路从头到尾讲透。第 7 章起是动手实践。
>
> 配套可运行代码（零第三方依赖，纯 Python 标准库手写协议）：
>
> | 文件 | 作用 |
> |------|------|
> | [server.py](#7-动手纯-python-手写-mcp-serverclient) | 手写 stdio MCP 服务器（协议最小实现） |
> | [client.py](#7-动手纯-python-手写-mcp-serverclient) | 手写 MCP 客户端，逐条打印协议报文 |
> | [probe.py](#45-本地调试与排错) | 本地调试探针：不经宿主，直接和服务器对话 |
> | [fastmcp_demo.py](#8-用官方-sdkfastmcp开发) | 用官方 SDK 的 FastMCP 高级 API 重写同一功能 |
>
> 直接运行：`python client.py`（会自动拉起 server.py，无需安装任何包）。

---

## 目录

0. [MCP 是什么：它到底解决什么问题](#0-mcp-是什么它到底解决什么问题)
1. [核心架构：Host / Client / Server](#1-核心架构host--client--server)
2. [三大原语：Tools / Resources / Prompts](#2-三大原语tools--resources--prompts)
3. [协议原理：JSON-RPC 2.0 之上](#3-协议原理json-rpc-20-之上)
4. [**本地调用完全指南（重点）**](#4-本地调用完全指南重点)
5. [远程调用：Streamable HTTP](#5-远程调用streamable-http)
6. [扩展机制：Tasks / Skills / Apps](#6-扩展机制tasks--skills--apps)
7. [动手：纯 Python 手写 MCP Server/Client](#7-动手纯-python-手写-mcp-serverclient)
8. [用官方 SDK（FastMCP）开发](#8-用官方-sdkfastmcp开发)
9. [安全：必须认真对待的部分](#9-安全必须认真对待的部分)
10. [学习路径与资源](#10-学习路径与资源)

---

## 0. MCP 是什么：它到底解决什么问题

### 0.1 N×M 集成困境

在 MCP 之前，如果你有 N 个 AI 应用（Claude Desktop、Cursor、VS Code 插件、自研 Agent……）想连接 M 个外部系统（GitHub、数据库、文件系统、公司内部 API……），你需要写 **N×M 个定制集成**：

```
        应用A   应用B   应用C        N 个 AI 应用
          \      |      /
           \     |     /
            \    |    /
             \   |   /
              \  |  /
               \ | /
                \|/                    M 个外部系统，每个对接一个应用就要重写一遍
               /|\
              / | \
```

每个集成都要各自处理：认证怎么带、错误怎么表达、上下文怎么给模型、工具怎么描述……**没有标准，就没有复用**。

### 0.2 MCP 的答案：把「集成」变成「协议」

MCP 做的事，和 **USB-C** 对硬件生态做的事一样：定义统一接口，让 N 个应用和 M 个系统各自实现一次协议，就能两两互通，N×M 降为 N+M。

```
        应用A   应用B   应用C
          \      |      /
           ======MCP======
                /|\
         系统1  系统2  系统3
```

从架构上讲，MCP 更准确的类比是 **LSP（Language Server Protocol）**：LSP 之前，每个编辑器给每种语言写一遍补全/跳转；LSP 之后，语言服务器实现一次，所有支持 LSP 的编辑器都能用。MCP 就是「AI 应用领域的 LSP」——官方规范原文也明确说了它 take some inspiration from LSP。

### 0.3 MCP 不是什么

| 概念 | 和 MCP 的关系 |
|------|--------------|
| **Function Calling / Tool Use** | 是**单个模型**调用工具的能力，各家 API 私有格式（OpenAI 的格式 ≠ Anthropic 的格式）。MCP 不替代它，而是**在模型之上**定义「工具从哪里发现、如何描述、如何执行、结果如何回传」的标准管道。宿主把 MCP 工具转换成模型各自的 Function Calling 格式。 |
| **REST / GraphQL API** | 是应用间的数据接口。MCP 服务器**内部**当然可以调 REST API，但 MCP 本身解决的是「LLM 应用 ↔ 能力提供方」的协议，消息模型、上下文协商、安全模型都是为 AI 场景设计的。 |
| **Agent 框架（LangChain 等）** | Agent 框架是**应用层**的编排库；MCP 是**协议层**的标准。框架可以作为 MCP 宿主去连接 MCP 服务器。 |
| **插件系统** | 插件通常绑定单一宿主（Chrome 插件只在 Chrome 用）。MCP 服务器是独立进程/服务，任何 MCP 宿主都能连接。 |

---

## 1. 核心架构：Host / Client / Server

### 1.1 三个角色

MCP 采用 **客户端-宿主-服务器**架构，三个角色分工明确：
\> 补充说明：这里提到的“最终一致性”是指…… 

<details> <summary>补充说明</summary> 这里是详细的解释，可以写多段、加代码块。 </details>

```
┌─────────────────────────────────────────────┐
│  Host（宿主）—— 例如 Claude Desktop / Cursor  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │Client 1 │  │Client 2 │  │Client 3 │       │
│  └────┬────┘  └────┬────┘  └────┬────┘       │
└───────┼────────────┼────────────┼────────────┘
        │            │            │
   本地  │       本地 │       远程 │
        ▼            ▼            ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │Server 1 │  │Server 2 │  │Server 3 │
   │文件/Git │  │ 数据库  │  │外部 API │
   └─────────┘  └─────────┘  └─────────┘
```

- **Host（宿主）**：用户直接使用的 AI 应用。负责创建和管理多个 Client 实例、执行安全策略与用户授权、把 LLM 接进来、聚合各服务器的上下文。**完整对话历史只存在于 Host**。
- **Client（客户端）**：Host 内部的协议连接器。每个 Client 与**恰好一个** Server 保持 1:1 连接，负责路由协议消息。Client 由宿主 SDK 提供，业务开发者一般不用自己写（第 7 章为了讲原理会手写一个）。
- **Server（服务器）**：提供具体能力的轻量级程序：暴露工具/资源/提示词，可以访问本地文件、数据库或远程 API。**每个 Server 只做一件专注的事**。

一个直观的例子：你在 Cursor 里同时连了「文件系统 MCP 服务器」和「GitHub MCP 服务器」，Cursor 就是 Host，里面为每个服务器各跑一个 Client。

### 1.2 设计原则

规范明确了四条设计原则，理解它们比记住 API 更重要：

1. **服务器必须极其容易编写**：复杂的编排（多服务器管理、LLM 交互、上下文聚合）全在 Host；Server 只暴露专注的能力。
2. **服务器必须高度可组合**：每个 Server 独立做好一件事，用户按需组合。
3. **服务器不能读到完整对话，也看不到别的服务器**：Server 只收到必要信息，彼此隔离，安全边界由 Host 强制执行。这条是安全模型的根基（见第 9 章）。
4. **能力渐进式扩展**：核心协议最小化，额外能力通过协商逐步开启，前后向兼容。

### 1.3 2026-07-28 的最大变化：无状态化

**旧版 MCP（2024-11-05 ~ 2025-11-25）是有连接会话的**：客户端连上后先发 `initialize` 握手，双方交换协议版本和能力，之后的请求都依赖这个「连接上下文」。

**2026-07-28 版把协议改成了完全无状态（stateless）**：服务器不记住任何连接级状态，每个请求**自包含**——协议版本、客户端身份、客户端能力全部随请求携带（放在 `_meta.io.modelcontextprotocol/*` 字段里）。带来的直接好处：

- HTTP 场景下可以自由地负载均衡、横向扩展（请求落到哪台机器都一样）；
- 断开重连不丢会话，任务可以用显式 ID 跨连接延续（这正是 Tasks 扩展的基础，见第 6 章）；
- 服务器可以同时处理来自多个任务/线程/会话、相互交错的请求。

代价是每个请求都多带几百字节的元数据，并且**能力发现从「一次握手」变成了「随请求携带 + 可选的 `server/discover` 预查询」**。

> 你现在在网上看到的多数教程、SDK 默认行为仍基于旧版握手式协议。读旧资料时，把「initialize 握手」理解为「2026-07-28 之前建立连接上下文的方式」即可，协议消息（tools/list、tools/call 等）本身是连续的。

---

## 2. 三大原语：Tools / Resources / Prompts

MCP 把服务器能提供的东西归为三类**原语（primitives）**，外加客户端侧原语。分类的依据是**控制权在谁手里**——这是 MCP 最核心的设计思想：

| 原语 | 控制方 | 类比 | 典型用途 |
|------|--------|------|----------|
| **Prompts（提示词）** | 用户控制 | 斜杠命令 / 菜单项 | 预置的工作流模板，用户主动选用 |
| **Resources（资源）** | 应用（客户端）控制 | 附件 / 文件 | 文件内容、API 响应、日志等上下文数据 |
| **Tools（工具）** | 模型控制 | 函数调用 | 查数据库、写文件、调外部 API 等动作 |

### 2.1 Tools：模型控制的函数

#### **第 1 组：Tools（暴露「动作」）—— 最常用**

表格

| 方法                               | 方向 | 作用                                                         |
| :--------------------------------- | :--- | :----------------------------------------------------------- |
| `tools/list`                       | C→S  | 「你有什么工具？」返回工具名片数组                           |
| `tools/call`                       | C→S  | 「执行这个工具。」唯一同时具备 `content` / `isError` / `structuredContent` 的方法 |
| `notifications/tools/list_changed` | S→C  | 「我的工具清单变了，你重拉一遍」                             |

- `tools/list`：靠 `cursor` 做游标分页，**不要自己做 offset**；字段重点是 `name`（唯一标识，模型匹配的依据）、`description`（模型唯一的决策依据，务必写清约束和失败时怎么改）、`inputSchema`（Draft-07 JSON Schema 对象，不能外链 `$ref`）、`annotations`（`readOnlyHint`/`destructiveHint`/`idempotentHint`/`openWorldHint`，决定 Host 敢不敢重试、要不要弹安全提示）。
- `tools/call`：`arguments` **必须是对象**，无参时传 `{}` 而非 `null`；长任务用 `_meta.progressToken` 配合进度通知。
- `list_changed`：是**失效通知而非增量同步**，只能喊一声「变了」，Host 会重新完整拉一遍 list，因此你的 list 必须能稳定重放。工具集固定就永远别发，白白浪费 token。

#### **第 2 组：Resources（暴露「数据」）—— 只读、可订阅**

| 方法                                   | 方向 | 作用                                                         |
| :------------------------------------- | :--- | :----------------------------------------------------------- |
| `resources/list`                       | C→S  | 列出可读资源（文件、日志、报表、行数据…）                    |
| `resources/read`                       | C→S  | 按 URI 读一份资源。返回 **`contents[]`（复数）**，不是 content，也没有 isError |
| `resources/templates/list`             | C→S  | 提供 URI 模板（如 `/logs/{date}`）+ 参数 schema              |
| `resources/subscribe` / `unsubscribe`  | C→S  | 订阅某个 URI                                                 |
| `notifications/resources/list_changed` | S→C  | 资源清单变了                                                 |
| `notifications/resources/updated`      | S→C  | 你订阅的那个 URI 内容更新了                                  |

**什么时候选 resources 而不是 tools**：内容**读多写少、有稳定 URI、体积较大、值得被缓存或增量更新**。反之，每次结果依赖参数计算、有副作用，就走 tools。前文提到「base64 大图撑爆 context」，正解就是把文件落盘或上传，改用 `resource` / `resourceLink` 返回 URI。

#### **第 3 组：Prompts（暴露「模板 / 工作流」）**

表格

| 方法                                 | 方向 | 作用                                                         |
| :----------------------------------- | :--- | :----------------------------------------------------------- |
| `prompts/list`                       | C→S  | 列出预置提示模板（可带参数定义）                             |
| `prompts/get`                        | C→S  | 取一个模板，返回 `messages[{role, content}]`，由 Client 拼进上下文 |
| `notifications/prompts/list_changed` | S→C  | 模板清单变了                                                 |

适用场景：给用户提供**可复用的对话入口**（代码审查模板、SQL 生成模板、角色扮演设定），让其在 UI 里一键选择并填参。若只需一段系统提示，写在工具 description 里即可，不必单独开 prompts。

> 上面三组的结构是刻意对称的：**list / call(or read) / list_changed**。记住这个模式，就不会漏掉「变了要通知」那一半。

#### **第 4 组：服务端主动往外发的（非通知类）**

表格

| 方法                     | 方向 | 作用                | 现状                                                         |
| :----------------------- | :--- | :------------------ | :----------------------------------------------------------- |
| `notifications/progress` | S→C  | 长任务进度条        | 请求里带了 `_meta.progressToken` 才能发                      |
| `logging/setLevel`       | C→S  | Client 设定日志级别 | 级别枚举：debug/info/notice/warning/error/critical/alert/emergency/fatal |
| `notifications/message`  | S→C  | 推送日志条目        | **协议级日志已走向弃用**，推荐迁移路径：stdio server 直接写 stderr，remote server 走 OpenTelemetry |

#### **第 5 组：Server 反向调用 Client（方向反过来）**

表格

| 方法                               | 什么时候用                                   | 关键字段                                                     |
| :--------------------------------- | :------------------------------------------- | :----------------------------------------------------------- |
| `sampling/createMessage`           | 你自己需要 LLM 智能，但不想自带模型          | params: `messages`、`systemPrompt?`、`modelPreferences?`、`maxTokens`、`temperature`、`includeContext?`；result 拿模型回复 |
| `elicitation/create`               | 涉及花钱、删数据、授权等**必须用户点头**的事 | params: `message`、`requestedSchema`；result: `action: accept/decline/cancel` + params。**别自作主张，也别指望模型替用户同意** |
| `roots/list`                       | 想知道能访问用户的哪些目录/项目              | result: `roots[{uri, name}]`；拿到合法路径后再读写，别硬编码 |
| `notifications/roots/list_changed` | 根目录变了通知 Server                        | 无 params                                                    |

判断口诀：**要智能 → sampling；要授权 → elicitation；要文件路径 → roots。**

#### **第 6 组：辅助能力**

`completion/complete` —— UI 输入框里的**自动补全**（补全资源 URI、prompt 参数）。params 里 `ref` 指向哪个 resource/prompt 的哪个参数、`argument:{name,value}` 是当前已输入值；result 回 `completion:{values:[], total?, hasMore?}`。纯体验优化，不做也行。

服务器声明 `tools` 能力后，客户端可以 `tools/list` 发现工具、`tools/call` 调用工具。工具定义的要点：

```json
{
  "name": "get_weather",
  "title": "天气查询",
  "description": "查询指定城市的当前天气",
  "inputSchema": {
    "type": "object",
    "properties": {"location": {"type": "string", "description": "城市名或邮编"}},
    "required": ["location"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {"temperature": {"type": "number"}, "conditions": {"type": "string"}}
  },
  "annotations": { "readOnlyHint": true }
}
```

**字段说明**：

| 字段 | 作用与含义 |
|------|-----------|
| `name` | 工具的唯一标识符（1~128 字符，`[A-Za-z0-9_.-]`，服务器内唯一）。模型发起调用时指名要的就是它 |
| `title` | 给**人**看的显示名（工具列表、悬停标题用），模型决策时不依赖它 |
| `description` | 工具功能的自然语言描述。**工具描述即提示词**：模型靠 `name + description + inputSchema` 判断何时调用、怎么传参，写得敷衍模型就会选错 |
| `inputSchema` | 入参的 JSON Schema（默认方言 2020-12）。模型据此知道"该传什么"，宿主据此校验参数合法性 |
| `inputSchema.type` | 根节点固定为 `"object"`：参数以键值对（命名参数）传入 |
| `inputSchema.properties` | 参数清单，键为参数名；每个值是该参数自己的 schema——`type` 约束类型，`description` 告诉模型这个参数填什么（如"城市名或邮编"） |
| `inputSchema.required` | 代表必填参数名单；缺失即校验失败。内容是properties的子集，没有写在里面的properties参数名，说明这个参数可以省略 |
| `outputSchema` | 出参的 JSON Schema。声明后工具结果会附带符合该 schema 的 `structuredContent`，客户端可以机读、可以校验 |
| `outputSchema.properties` | 输出字段定义：`temperature`（number，气温）、`conditions`（string，天气状况） |
| `annotations` | 行为标注集合：`readOnlyHint: true` 提示客户端"只读、无副作用"，可用来免弹确认框；同类还有 `destructiveHint`、`idempotentHint`、`openWorldHint`。注意标注是**不可信输入**，只用于优化交互，不是安全保证 |

| type 值 | 对应 JSON | 对应 Python 标注 | 说明                                       | 常用约束关键字                                               |
| ------- | --------- | ---------------- | ------------------------------------------ | ------------------------------------------------------------ |
| string  | 字符串    | str              | 最常用，地址、名称、路径都是它             | minLength / maxLength、pattern（正则）、format（date-time、uri、email…） |
| number  | 数字      | float            | 任意数值（含小数）                         | minimum / maximum、exclusiveMinimum / exclusiveMaximum、multipleOf |
| integer | 整数      | int              | 没有小数部分的数                           | 同上                                                         |
| boolean | 布尔      | bool             | true / false                               | 无专门约束，常用 enum: [true, false] 或 default              |
| array   | 数组      | list[X]          | 有序列表，元素类型用 items 声明            | items（元素 schema）、minItems / maxItems、uniqueItems       |
| object  | 对象      | dict             | 键值对，子字段用 properties 声明           | properties、required、additionalProperties                   |
| null    | null      | None             | 空值。单独用没意义，一般放进数组表示"可空" | —                                                            |

### **ToolAnnotations：5 个字段**

| 字段              | 类型    | 默认值 | 含义                                                         | 典型填法                                                     |
| ----------------- | ------- | ------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| `title`           | string  | 无     | 给人看的人类可读标题，UI 上显示用（name 是给机器匹配的，可能带下划线或前缀） | `"天气查询"`、`"反编译函数"`                                 |
| `readOnlyHint`    | boolean | false  | 该工具是否不修改环境（只读/查询/搜索）                       | 纯查询标 `true`；只要会写东西就标 `false`                    |
| `destructiveHint` | boolean | true   | 是否会做破坏性变更（删除、覆盖、不可逆）                     | 删除/覆盖标 `true`；只新增、追加标 `false`                   |
| `idempotentHint`  | boolean | false  | 同参数重复调用是否没有额外副作用                             | 幂等（查、upsert、set）标 `true`；累加、追加、发通知标 `false` |
| `openWorldHint`   | boolean | true   | 是否与外部开放世界交互（结果可能被外部改变、不在你掌控中）   | 调公网 API、搜网页标 `true`；操作本地封闭系统标 `false`      |

- **inputSchema / outputSchema**：JSON Schema（默认方言 2020-12），描述入参/出参结构。模型主要靠 `name + description + inputSchema` 决定何时调用、怎么传参——**工具描述就是提示词的一部分**。
- **annotations（行为标注）**：如 `readOnlyHint`、`destructiveHint`、`idempotentHint`、`openWorldHint`。注意规范的态度：标注是**不可信输入**（除非来自可信服务器），客户端可用来决定是否弹确认框，但不能当作安全保证。
- **content（内容块）**：工具返回非结构化内容，支持五种块：`text`、`image`、`audio`、`resource_link`（资源链接）、`resource`（内嵌资源）。

```json
"content": [
  {"type": "text",     "text": "除数不能为 0"},
  {"type": "image",    "data": "iVBOR...", "mimeType": "image/png"},
  {"type": "audio",    "data": "...",     "mimeType": "audio/wav"},
  {"type": "resource", "resource": {...}},
  {"type": "resourceLink", "uri": "file://...", "name": "report.csv"}
]
```



- **structuredContent**：结构化输出，需符合 outputSchema；规范建议同时附一份序列化文本，兼容旧客户端。
- **两类错误**（重要，直接影响模型体验）：
  - **协议级错误**：工具不存在、请求结构非法 → JSON-RPC `error`。模型较难自行恢复。
  - **执行级错误**：入参校验失败、业务异常 → `result` 里 `isError: true` + 可读的错误文本。**模型读到后能自我纠正**（比如「日期必须是未来时间，今天是 08/08/2025」）。写服务器时要善用后者。
- **有状态工具**：协议无会话，服务器要跨调用保持状态（购物车、数据库事务、浏览器会话），必须**显式返回句柄（handle）**，后续调用把句柄当参数传回。句柄要 opaque（不暴露内部结构）、有生命周期说明、过期时返回明确错误。
- 命名规范：1~128 字符，`[A-Za-z0-9_.-]`，服务器内唯一。多个服务器的工具名可能撞车（都叫 `search`），客户端/代理应加前缀消歧。

### 2.2 Resources：应用控制的上下文

资源用 **URI** 标识（`file:///...`、`https://...` 或自定义 scheme 如 `note://welcome`），通过 `resources/list` 列出、`resources/read` 按 URI 读取。返回 `contents` 数组，每项含 `uri`、`mimeType` 和 `text`/`blob`。资源还可以带 annotations（`audience`：给用户还是给模型看；`priority`：重要度）。

与工具的本质区别：**资源由客户端/用户决定何时加载**（比如用户勾选一个文件作为上下文），而不是模型想调就调。工具也可以返回 `resource_link`，引导客户端去读关联资源。

### 2.3 Prompts：用户控制的模板

提示词模板带参数声明（`prompts/list`），用户选用后由 `prompts/get` 渲染成**直接可发给 LLM 的消息列表**（`messages: [{role, content}]`）。它把「怎么用好这个服务器」的经验固化成可复用的模板。

### 2.4 客户端侧原语：服务器向客户端「反向求助」

有些场景服务器干活干到一半，需要客户端提供输入。2026-07-28 规范通过 **MRTR 机制**（见 3.6）统一表达，共有三种求助：

- **Elicitation（请示）**：服务器向**用户**要信息——比如「请提供你的 GitHub 用户名」。客户端弹出表单（`mode: "form"`，带 JSON Schema 描述的表单）或打开 URL（URL 模式）。
- **Sampling（采样）**：服务器请求客户端**代跑一次 LLM 推理**（`sampling/createMessage`）——比如让宿主模型帮忙总结一段文本。LLM 调用权和成本始终在客户端手里。
- **Roots（根目录，已弃用）**：客户端告诉服务器「用户关心哪些目录」。**2026-07-28 起弃用**（规范建议改用工具参数、资源 URI 或服务器配置传目录），但至少还会在规范里保留 12 个月。

---

## 3. 协议原理：JSON-RPC 2.0 之上

### 3.1 消息三态

所有消息都是 **JSON-RPC 2.0**、UTF-8 编码，分三种：

| 类型 | 结构 | 方向 |
|------|------|------|
| **请求 Request** | `{jsonrpc, id, method, params?}` | 客户端 → 服务器 |
| **响应 Response** | `{jsonrpc, id, result}` 或 `{jsonrpc, id, error}` | 服务器 → 客户端 |
| **通知 Notification** | `{jsonrpc, method, params?}`（无 id，不得回复） | 双向 |

MCP 对 JSON-RPC 的约束：id **不允许为 null**；未决请求之间 id 不得重复；结果必须带 `resultType` 字段。

### 3.2 resultType：多态结果

2026-07-28 每个 `result` 都带 `resultType` 字符串，客户端据此决定怎么解析：

- `"complete"`：请求完成，result 里就是最终内容（兼容旧服务器：`resultType` 缺失时按 complete 处理）；
- `"input_required"`：请求没完，服务器需要客户端输入，result 里是 `InputRequiredResult`（见 3.6）；
- 扩展可以增加新值（如 Tasks 扩展的 `"task"`），客户端不认识的 `resultType` 必须视为非法。

### 3.3 _meta：随请求携带的协议元数据

无状态化的落地方式。每个客户端请求的 `params._meta` 里必须带：

| 键 | 必填 | 含义 |
|----|------|------|
| `io.modelcontextprotocol/protocolVersion` | ✅ | 本请求用的协议版本，如 `"2026-07-28"` |
| `io.modelcontextprotocol/clientCapabilities` | ✅ | 客户端能力（如 `{"elicitation": {}}`、扩展支持） |
| `io.modelcontextprotocol/clientInfo` | 建议 | 客户端名和版本 |
| `io.modelcontextprotocol/logLevel` | 可选 | 本请求希望服务器输出的最低日志级别 |
| `progressToken` | 可选 | 订阅进度通知 |
| `traceparent` / `tracestate` / `baggage` | 可选 | OpenTelemetry 追踪上下文透传 |

服务器响应里**建议**带 `_meta.io.modelcontextprotocol/serverInfo`（自报身份）。缺必填字段的请求，服务器必须回 `-32602` 拒绝；需要某能力而客户端没声明，回 `-32021 MissingRequiredClientCapability`。

注意 `_meta` 键名的保留规则：第二段是 `modelcontextprotocol` 或 `mcp` 的前缀（如 `io.modelcontextprotocol/`）保留给官方，第三方用自己的反 DNS 前缀（如 `com.example/`）。

### 3.4 能力协商：server/discover

`server/discover` 是 2026-07-28 新增的、**所有服务器必须实现**的方法。客户端（可选）在发其他请求前调用它，一次性拿到：

```json
{
  "jsonrpc": "2.0", "id": "discover-1", "method": "server/discover",
  "params": { "_meta": { "io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientCapabilities": {} } }
}
```

**字段说明**：

| 字段 | 作用与含义 |
|------|-----------|
| `jsonrpc` | 协议版本标记，固定 `"2.0"`（所有消息都是 JSON-RPC 2.0） |
| `id` | 请求标识，服务器响应时**原样带回**，客户端靠它把响应与请求配对；带 `id` 的消息才需要响应 |
| `method` | 要调用的方法名。`server/discover` 是 2026-07-28 新增的能力预查询，所有服务器必须实现 |
| `params._meta` | 随请求携带的协议元数据——无状态化的载体，每个请求自带版本与身份（详见 3.3） |
| `_meta."io.modelcontextprotocol/protocolVersion"` | 本次请求使用的 MCP 协议版本；服务器不支持时回 `-32022 UnsupportedProtocolVersion` |
| `_meta."io.modelcontextprotocol/clientCapabilities"` | 客户端能力声明（支持 elicitation、启用了哪些扩展等），服务器据此决定能启用哪些特性。缺必填 `_meta` 字段会被 `-32602` 拒绝 |

> 键名前缀 `io.modelcontextprotocol/` 是官方保留前缀；第三方自定义元数据须用反 DNS 前缀（如 `com.example/`），见 3.3。

```json
{
  "jsonrpc": "2.0", "id": "discover-1",
  "result": {
    "resultType": "complete",
    "supportedVersions": ["2026-07-28"],
    "capabilities": { "tools": {}, "resources": {} },
    "instructions": "这是一个教学用服务器：提供加法、回声工具和便签资源。",
    "_meta": { "io.modelcontextprotocol/serverInfo": { "name": "note-server", "version": "1.0.0" } }
  }
}
```

**字段说明**：

| 字段 | 作用与含义 |
|------|-----------|
| `jsonrpc` / `id` | 同请求侧；`id` 原样带回，完成请求-响应配对 |
| `result` | 成功时的结果载荷（失败则是 `error`，二者互斥） |
| `result.resultType` | **多态结果标记**：`complete` = 请求已完成，`result` 里就是最终内容（缺失时按 complete 兼容旧服务器）；`input_required` = 服务器中途需要输入（MRTR 流程，见 3.6）；扩展可定义新值（如 Tasks 的 `"task"`），客户端不认识的必须视为非法 |
| `result.supportedVersions` | 服务器支持的 MCP 协议版本列表，客户端从中选定后续通信使用的版本 |
| `result.capabilities` | 服务器能力清单：出现 `"tools": {}` 表示支持工具原语、`"resources": {}` 表示支持资源原语；不支持的原语整个键不出现。空对象表示"支持，无子选项" |
| `result.instructions` | 服务器写给 LLM 的自然语言使用说明（"怎么正确使用我"），宿主通常把它并入系统提示词 |
| `result._meta."io.modelcontextprotocol/serverInfo"` | 服务器自报身份：`name` 服务器名、`version` 版本号，供客户端展示与日志排查 |

`instructions` 字段很实用：服务器用自然语言告诉 LLM「怎么正确使用我」，宿主通常会把它并进系统提示词。此外 `server/discover` 还兼任 stdio 上的「新旧版本探针」（见 3.5 和 4.2）。

### 3.5 版本演进史

| 版本 | 关键变化 |
|------|----------|
| **2024-11-05** | 首个公开版本。stdio + HTTP+SSE 两种传输；`initialize` 握手建立连接会话；服务器可以主动向客户端发请求 |
| **2025-03-26** | Streamable HTTP 取代 HTTP+SSE；OAuth 授权框架；工具 annotations；音频内容 |
| **2025-06-18** | elicitation（表单请示）；结构化工具输出（outputSchema/structuredContent）；工具结果里的 resource_link；`MCP-Protocol-Version` 头 |
| **2025-11-25** | 增量修订（URL 模式 elicitation 等，细节见官方 changelog） |
| **2026-07-28** | **无状态化**：每请求携带 `_meta` 元数据；新增 `server/discover`；MRTR 取代服务器主动请求；订阅流 `subscriptions/listen`；Tasks/Skills/Apps 扩展框架；Roots 弃用；HTTP+SSE 正式弃用 |

**向后兼容**：支持新旧的客户端会先探测（stdio 上发 `server/discover`，HTTP 上先发一个带现代头的 POST）：得到现代响应/错误 → 按现代协议继续；得到无法识别的错误或超时 → 回退到 `initialize` 握手。规范要求回退判断不能绑定单一错误码。

### 3.6 MRTR：多轮请求（服务器反向求助的标准姿势）

旧协议里服务器想向客户端要输入，得**主动发一个 JSON-RPC 请求**。2026-07-28 废除了这个模式，改为 **MRTR（Multi Round-Trip Requests）**：服务器返回 `resultType: "input_required"` 的结果，里面挂 `inputRequests`（elicitation/create、sampling/createMessage、roots/list 等）和一个不透明的 `requestState`；客户端收集输入后，**用新的 id 重发原请求**，参数里带上 `inputResponses` 和 `requestState`：

```
Client                          Server
  │  tools/call (id=1)            │
  │──────────────────────────────>│
  │                               │  （干到一半，需要用户输入）
  │  result: input_required       │
  │  inputRequests: {…}           │
  │  requestState: "eyJs…"        │
  │<──────────────────────────────│
  │  （弹表单/调 LLM/取 roots）    │
  │  tools/call (id=2)            │
  │  + inputResponses + requestState
  │──────────────────────────────>│
  │  result: complete             │
  │<──────────────────────────────│
```

好处：服务器永远不发请求，传输层简单了；输入收集与重试完全在请求生命周期内，天然兼容无状态和 HTTP。

### 3.7 订阅与通知

需要持续接收服务器状态变化（工具列表变更、资源更新、任务进度）的客户端，发一个 `subscriptions/listen` 请求，**它的响应本身就是一条长活的流**，按订阅过滤推送通知（`notifications/tools/list_changed`、`notifications/resources/updated` 等），流里每条通知带 `_meta.io.modelcontextprotocol/subscriptionId` 供关联。stdio 上是单信道，客户端靠这个字段区分通知属于哪个订阅。

### 3.8 错误码体系

- 标准 JSON-RPC 码：`-32700`（解析失败）、`-32600`、`-32601`（方法不存在）、`-32602`（参数非法）、`-32603`（内部错误）。
- MCP 规范专用（保留子区间 `-32020`~`-32099`）：
  - `-32020` HeaderMismatch：HTTP 头与请求体不一致；
  - `-32021` MissingRequiredClientCapability：客户端没声明必需能力；
  - `-32022` UnsupportedProtocolVersion：协议版本不支持。
- `-32000`~`-32019` 是历史遗留区，新代码不应再用；新用途的私有错误码应分配在 `-32768`~`-32000` 之外。

### 3.9 横切关注点

- **进度（progress）**：请求参数里带 `progressToken`，服务器可中途发 `notifications/progress`（`{progress, total}`）。
- **取消（cancelled）**：stdio 上客户端发 `notifications/cancelled`；HTTP 上直接关闭该请求的 SSE 流即为取消。取消是协作式的：服务器尽快停，且不得再发该请求的后续消息。
- **分页（pagination）**：`*/list` 支持 `cursor` 参数与 `nextCursor` 返回。
- **缓存（caching）**：`*/list` 响应可带 `ttlMs`、`cacheScope`，客户端可缓存；工具列表**确定性排序**能提升 LLM 提示词缓存命中率。
- **日志（logging）**：服务器通过 `notifications/message` 按级别（debug/info/warning/error）发日志，客户端可用 `_meta` 的 `logLevel` 控制。

---

## 4. 本地调用完全指南（重点）

**本地调用**是 MCP 最常见的用法：**Host 把 MCP 服务器作为本地子进程拉起，双方走 stdio 通信**。本章把这条链路完整讲透：调用过程 → 传输规范 → 工程实践 → 接入各宿主 → 调试排错 → 代码级调用。

### 4.1 本地调用的完整链路

以「用户在 Claude Desktop 里让 AI 算 2+3，背后是本地 note-server 的 add 工具」为例：

```
用户              Host(宿主)            Client           Server(本地子进程)
 │ "帮我算 2+3"     │                     │                  │
 │─────────────────>│                    │                  │
 │                  │ 1. 首次使用时按配置 spawn 子进程        │
 │                  │   python server.py │                  │
 │                  │───────────────────────────────────────>│ 启动，等待 stdin
 │                  │                     │ 2.（可选）server/discover 探测能力
 │                  │                     │─────────────────>│
 │                  │                     │<─────────────────│ 支持版本+能力清单
 │                  │ 3. tools/list 拿工具，随系统提示词给 LLM│
 │                  │                     │─────────────────>│
 │                  │                     │<─────────────────│ add/echo 工具定义
 │                  │                     │                  │
 │                  │ 4. LLM 决定调用 add(2,3)               │
 │                  │                     │ tools/call       │
 │                  │                     │─────────────────>│ 执行，返回 sum=5
 │                  │                     │<─────────────────│
 │                  │ 5. 结果回喂 LLM，生成回答               │
 │<─────────────────│                    │                  │
 │ "2+3=5"          │                    │                  │
 │                  │ 6. 用户禁用/退出宿主：关闭服务器 stdin ─>│ 读到 EOF，退出
```

四个关键认知：

1. **进程由客户端管理**：启动、重启、关闭都是客户端（宿主）的职责。服务器只负责「stdin 有数据就干活、stdin 关闭就退出」。
2. **进程 ≠ 会话**：无状态协议下，一个服务器进程可以同时服务多个对话/任务，请求可以交错。别在服务器里把「连接」当「会话」用；要跨调用的状态，用工具有状态 handle 模式（见 2.1）。
3. **进程崩溃可自愈**：服务器意外退出，客户端应重启它；无状态协议下进行中的请求直接重试即可，会话不丢。
4. **工具调用有人工把关**：宿主通常会先弹确认框（尤其对 `destructiveHint` 工具），用户同意才真正发 `tools/call`。

### 4.2 stdio 传输：服务器自查清单

stdio 的规范细节（第 3 章的协议在此之上的传输绑定）：

- 服务器从 **stdin** 逐行读 JSON-RPC 消息，向 **stdout** 逐行写；
- 每条消息是**不含换行符的单行 JSON**（`json.dumps` 默认不换行，天然满足）；
- **stderr** 专用于日志——服务器不得往 stdout 写任何非协议内容（混入一行 `print` 就能让客户端解析崩溃）；
- UTF-8 编码；
- 优雅关闭 = 客户端关闭服务器 stdin，服务器应尽快退出；
- 客户端关闭流后若进程不退，客户端会升级到 SIGTERM/SIGKILL（Windows 上 TerminateProcess）。

**写完一个本地服务器，按这份清单自查**：

- [ ] `for line in sys.stdin` 逐行读；写完 `sys.stdout.flush()`（管道是块缓冲，不 flush 客户端收不到）
- [ ] 所有日志走 `print(..., file=sys.stderr)`；检查第三方库启动时不会往 stdout 打 banner
- [ ] JSON 输出 `ensure_ascii=False` 且管道按 UTF-8 读写（Windows 默认 GBK，必须显式指定）
- [ ] stdin 读到 EOF（for 循环结束）时正常退出，不留僵尸进程
- [ ] 每个请求带齐 `_meta`（新版）或先 `initialize`（旧版）；`server/discover` 必须实现
- [ ] 手动 `python server.py` 空跑不报错（关闭窗口/Ctrl+D 能退出）

### 4.3 本地服务器工程实践

1. **解释器用绝对路径，别赌 PATH**。配置文件里写 `"command": "python"` 时，实际用的是宿主环境里的 PATH——可能是另一个 Python、根本没装依赖。更稳的写法：
   ```json
   "command": "E:\\Demo\\ZCode\\MD5\\MCP\\.venv\\Scripts\\python.exe"
   ```
   字段 `command`：宿主拉起服务器子进程所用的可执行程序路径——指向 venv 里的解释器，保证用对 Python 及其装好的依赖。
   （Windows 上 JSON 的反斜杠要双写转义，也可以统一用正斜杠。）
2. **uv 项目可以用 `uv run`**：`"command": "uv", "args": ["run", "python", "server.py"]`，uv 会自动准备虚拟环境，省心。
3. **密钥走 `env`，不进代码**：
   ```json
   "env": { "GITHUB_TOKEN": "ghp_xxx" }
   ```
   字段 `env`：以键值对形式**追加**给子进程的环境变量；`GITHUB_TOKEN` 是示例键名——服务器代码里用 `os.environ` 读取，密钥因此不写进代码。
   带密钥的配置文件不要提交到 git。
4. **相对路径要设 `cwd`**：服务器里用相对路径读写文件时，它的工作目录取决于宿主怎么拉起它。显式设置最稳：
   ```json
   "cwd": "E:\\Demo\\ZCode\\MD5\\MCP"
   ```
   字段 `cwd`：子进程的当前工作目录，服务器内所有相对路径的解析基准；不设则由宿主决定，显式设置最稳。
5. **Windows 三个经典坑**：
   - JSON 路径反斜杠转义（`\\`）；
   - Node 系服务器（npx/node）在部分宿主里要写 `npx.cmd` 而不是 `npx`；
   - 管道默认 GBK 编码导致中文乱码——代码里显式 UTF-8（本目录 server.py/client.py 已处理）。
6. **启动要快**：import 重型库（torch、pandas）会拖慢首次工具调用；用到再 import（函数内延迟导入）。
7. **一个进程服务多个会话**：无状态协议下不要用进程级全局变量存「当前用户」这类会话状态。

### 4.4 接入本地宿主

#### Claude Desktop（最典型）

配置文件位置：

| 系统 | 路径 |
|------|------|
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |

完整配置示例（把本目录的服务器接进去）：

```json
{
  "mcpServers": {
    "note-demo": {
      "command": "python",
      "args": ["E:\\Demo\\ZCode\\MD5\\MCP\\fastmcp_demo.py"],
      "env": {},
      "cwd": "E:\\Demo\\ZCode\\MD5\\MCP"
    },
    "raw-server": {
      "command": "python",
      "args": ["E:\\Demo\\ZCode\\MD5\\MCP\\server.py"]
    }
  }
}
```

**字段说明**：

| 字段 | 作用与含义 |
|------|-----------|
| `mcpServers` | Claude 系宿主的固定顶层键；其下每个键是一台要连接的 MCP 服务器（VS Code 的变体叫 `servers`，见下） |
| `"note-demo"` / `"raw-server"` | 服务器在本宿主内的**别名**，自己起，仅用于界面展示与日志，与服务器自报的 serverInfo 无关；连几台就写几个键 |
| `command` | 启动服务器的可执行程序。stdio 方式下宿主把它作为**子进程**拉起，经 stdin/stdout 交换 JSON-RPC（见 4.1/4.2）；建议写绝对路径（见 4.3 第 1 条） |
| `args` | 传给 `command` 的参数数组，这里是要运行的服务器脚本路径 |
| `env` | 追加给子进程的环境变量，密钥放这里不放代码（见 4.3 第 3 条）；`{}` 表示不追加 |
| `cwd` | 子进程的工作目录，服务器内相对路径的解析基准（见 4.3 第 4 条）；省略则由宿主决定 |

- **保存后必须完全退出 Claude Desktop 再重启**（包括托盘/后台），只关窗口不生效；
- 生效后对话里会出现工具图标（锤子/插头），点击可查看该服务器暴露的工具；首次调用高危工具会弹批准框；
- 排错日志在 `%APPDATA%\Claude\logs\` 下的 `mcp*.log`。

#### Cursor

- 全局配置 `~/.cursor/mcp.json`，或项目级 `.cursor/mcp.json`，格式同样是 `{"mcpServers": {...}}`；
- 也可以在 Settings → MCP 面板里直接添加、查看各服务器的连接状态和工具列表。

#### VS Code（GitHub Copilot Agent 模式）

- 在工作区建 `.vscode/mcp.json`：
  ```json
  {
    "servers": {
      "note-demo": {
        "type": "stdio",
        "command": "python",
        "args": ["E:\\Demo\\ZCode\\MD5\\MCP\\fastmcp_demo.py"]
      }
    }
  }
  ```

  **字段说明**：

  | 字段 | 作用与含义 |
  |------|-----------|
  | `servers` | VS Code 的顶层键（对应 Claude 系的 `mcpServers`） |
  | `"note-demo"` | 服务器在本宿主内的别名，同上例 |
  | `type` | 传输类型，`stdio` = 本地子进程。VS Code 要求显式声明；Claude 系配置没有此字段，默认即 stdio |
  | `command` / `args` | 同 Claude 配置：拉起子进程的程序与参数；`env` / `cwd` 在 VS Code 配置里同样可用 |

#### Cline / Zed 等

- Cline（VS Code 扩展）：MCP Servers 面板里配置，存储在 `cline_mcp_settings.json`，格式同为 `mcpServers`；
- Zed：在 settings.json 的 `context_servers` 里配置。

> 各宿主的配置格式演进很快，字段以各自当前文档为准；`{"mcpServers": {"name": {"command", "args", "env", "cwd"}}}` 是事实标准，VS Code 的 `servers` 是主要变体。

### 4.5 本地调试与排错

排查「宿主里看不到工具/调用失败」的正确顺序：**先证明服务器是好的，再查宿主配置**。

**第一步：绕过宿主，直接和服务器对话。**

用本目录的探针脚本（自动拉服务器、发 discover/list/call、打印原始响应和服务器 stderr）：

```bash
python probe.py                    # 探测 server.py
python probe.py fastmcp_demo.py    # 探测其他服务器（需先 pip install mcp）
```

或者裸管道一行流（适合 Git Bash / Linux/macOS）：

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}' | python server.py
```

**第二步：用 MCP Inspector 图形化调试。** 官方工具，能列工具、填参数调用、看每一条报文：

```bash
npx @modelcontextprotocol/inspector python server.py
```

**第三步：看日志。** 服务器的 stderr 是第一现场；Claude Desktop 的日志在 `%APPDATA%\Claude\logs\mcp*.log`；开发时可以 `python server.py 2>server.log` 把日志落到文件。

**常见症状速查表**：

| 症状 | 可能原因 | 修复 |
|------|----------|------|
| 宿主报 spawn ENOENT / command not found | python/node 不在 PATH 或名字不对 | 用绝对路径；Windows 下 npx 写 `npx.cmd` |
| 进程起来就退，一个工具都没有 | import 阶段抛异常；或有库往 stdout 打了 banner | 手动 `python server.py` 看 stderr；重定向污染 stdout 的库 |
| 改了配置毫无变化 | 没完全重启宿主 | 完全退出（含托盘）再启动 |
| 工具出现了，一调用就 `isError` | 这是**正常的业务错误**返回 | 读错误文本——它本来就是写给模型自我纠正的 |
| 中文乱码 | Windows GBK 管道 | 代码显式 UTF-8 + `ensure_ascii=False` |
| 时好时坏，偶发失败 | 服务器进程崩溃后被客户端重启 | 查服务器 stderr 日志找崩溃原因 |
| Inspector 打不开/连不上 | 端口被占或代理干扰 | 看 CLI 输出，换端口重试 |

### 4.6 用代码本地调用

除了宿主，你也可以在自己的程序里调本地 MCP 服务器。两种姿势：

**姿势一：手写客户端（本目录 client.py）**——`subprocess.Popen` 拉起服务器，逐行读写 JSON-RPC。零依赖、完全可控，适合学习和嵌入无第三方包约束的环境。

**姿势二：官方 SDK**（需 `pip install mcp`）：

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # StdioServerParameters 描述“怎么把服务器拉起来”
    params = StdioServerParameters(command="python", args=["server.py"])

    # stdio_client 负责子进程生命周期和管道读写
    async with stdio_client(params) as (read, write):
        # ClientSession 负责协议层（新旧版本握手由 SDK 处理）
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("工具:", [t.name for t in tools.tools])
            result = await session.call_tool("add", {"a": 2, "b": 3})
            print("结果:", result.content)


# asyncio.run(main()) 是语法糖：等价于
#   loop = asyncio.get_event_loop(); loop.run_until_complete(main())
asyncio.run(main())
```

> SDK 的具体 API 随版本变化较快（尤其 2026-07-28 无状态化后握手行为有调整），以 SDK 文档为准；上面这段表达的使用模式（描述启动参数 → 拿读写通道 → 开会话 → list/call）是稳定的。

---

## 5. 远程调用：Streamable HTTP

当服务器需要**多人共享、跨网络访问、或本身就在远程机器上**时，用 Streamable HTTP 传输：服务器作为独立服务，暴露**单一 MCP 端点**（如 `https://example.com/mcp`）。

- 每条客户端消息 = 一次 HTTP **POST**，`Accept` 头必须同时列出 `application/json` 和 `text/event-stream`；
- 服务器对请求的回复二选一：单个 JSON 对象，或一条**该请求独享的 SSE 流**（先推 `notifications/progress` 等相关通知，最终响应收尾）；
- 通知类 POST：接受则回 `202 Accepted` 空体；
- 长活通知流通过 `subscriptions/listen` 请求获得；SSE 建议加 `X-Accel-Buffering: no` 防止反代缓冲；
- **取消 = 关闭该请求的 SSE 流**（不再发 `notifications/cancelled`）；
- 必须的安全措施：校验 `Origin` 头（防 DNS rebinding）、本地服务只绑 `127.0.0.1`、实现 OAuth 认证。

HTTP 传输特有的一组镜像头（让负载均衡器等中间件不解析 body 就能路由/审计，body 仍是唯一事实来源）：

| 头 | 来源 | 说明 |
|----|------|------|
| `MCP-Protocol-Version` | `_meta.protocolVersion` | 必填；与 body 不一致 → `400` + `-32020` |
| `Mcp-Method` | `method` | 必填 |
| `Mcp-Name` | `params.name` / `params.uri` | `tools/call` 等必填；非 ASCII 值用 `=?base64?…?=` 哨兵编码 |
| `Mcp-Param-{Name}` | 工具参数 | 服务器可在 inputSchema 里给参数标 `x-mcp-header`，客户端把该参数值镜像成头 |

> 2026-07-28 起 HTTP 传输**移除了** GET 流端点和 `Mcp-Session-Id` 会话机制，流也不可恢复（`Last-Event-ID` 失效）——这正是无状态化在 HTTP 侧的体现。读到 2025 年的资料时这些差异会反复出现。

**本地 vs 远程怎么选**：

| | stdio（本地） | Streamable HTTP（远程） |
|------|-------|------|
| 部署 | 宿主拉起的本地子进程 | 独立远程服务 |
| 认证 | 环境变量 | OAuth 授权框架 |
| 适合 | 本地文件/数据库/CLI 工具 | 团队共享服务、SaaS、跨网络 |
| 延迟 | 最低（无网络） | 取决于网络 |

个人开发和本机工具用 stdio 就够；要把能力分享给团队或多个宿主，再考虑 HTTP。

---

## 6. 扩展机制：Tasks / Skills / Apps

核心协议之外，MCP 用**扩展（extensions）**承载可选的高级功能，全部 opt-in，双方在初始化时通过能力协商开启：

- **Tasks（任务）**：解决长耗时操作。服务器不阻塞等待，而是返回 `resultType: "task"` 的 `CreateTaskResult`（含 `taskId`、初始状态、TTL、建议轮询间隔）；客户端用 `tasks/get` 轮询，任务中途需要输入时进入 `input_required` 状态并用 `tasks/update` 回复，`tasks/cancel` 协作式取消。状态机：`working → input_required? → completed/failed/cancelled`。适用：CI 流水线、批处理、人工审批、外部作业系统、易断开的移动网络。**taskId 是持久句柄，客户端崩溃重连后凭它继续**——这是无状态协议的直接红利。
- **Skills over MCP**：通过 MCP 发现和消费面向 Agent 工作流的富结构化指令（相当于把「技能包」标准化分发）。
- **MCP Apps**：让服务器在对话里内联渲染交互式 UI（图表、表单、视频播放器）。

---

## 7. 动手：纯 Python 手写 MCP Server/Client

> **目标**：不装任何包，只用标准库，按 2026-07-28 规范实现一个能跑的 MCP 服务器和客户端。跑通之后，你对协议的理解会超过绝大多数「只会用 SDK」的开发者。

### 7.1 运行

```bash
cd MCP
python client.py
```

客户端会自动以子进程方式拉起 `server.py`，依次执行：`server/discover` → `tools/list` → `tools/call`（成功 + 业务失败 + 协议错误各一次）→ `resources/list`/`read` → `prompts/list`/`get` → 畸形请求 → 取消通知，**并把每一条线上收发的原始 JSON 打印出来**。

### 7.2 服务器代码走读（server.py）

结构很薄，四部分：

1. **输出工具**：`send()`（stdout 写单行 JSON + flush）、`log()`（stderr 日志）、`reply()`/`reply_error()`。注意 `reply()` 会自动给 result 补上 `resultType: "complete"`。
2. **数据定义**：`TOOLS` / `RESOURCES` / `PROMPTS` 三个纯数据列表——协议里工具就是「带 JSON Schema 的字典」，没有任何魔法。
3. **处理器**：每个 MCP 方法一个函数（`handle_tools_call` 等），通过 `HANDLERS` 分发表注册。`tools/call` 里特意演示了两种错误：业务错误返回 `isError: true`（模型可自我纠正），工具不存在抛 `McpError` 走 JSON-RPC error。
4. **主循环**：`for line in sys.stdin` 逐行解析；`validate_meta()` 落实无状态校验（每个请求必须自带 `protocolVersion` + `clientCapabilities`，否则 `-32602`）；EOF（stdin 关闭）即优雅退出。

几个容易踩的坑，代码里都处理了：**flush**（管道块缓冲，写完必须 flush）、**编码**（Windows 管道默认 GBK，JSON 一律 `ensure_ascii=False` + UTF-8）、**stdout 纯净**（日志只能去 stderr）、**通知不能回**（`handle_notification` 只记录）。

### 7.3 客户端代码走读（client.py）

`McpStdioClient` 类封装三件事：`subprocess.Popen` 拉起服务器、`request()` 发请求并读匹配 id 的响应（无关消息跳过）、`_meta()` 构造每请求元数据。stderr 用守护线程实时转发，让你看到服务器的日志与协议流量分离。

### 7.4 练习

1. 给服务器加一个 `multiply` 工具，然后不改客户端、只改 `client.py` 里的一处调用验证它；
2. 把一个工具改成需要 elicitation 的 MRTR 流程（返回 `input_required`，客户端重发带 `inputResponses`）；
3. 把 `TOOLS` 里的 `description` 改写得极其敷衍，思考：模型还能选对这个工具吗？（体会「工具描述即提示词」）；
4. 按 4.4 的配置把 server.py 接进 Claude Desktop 或 Cursor，实际对话里调用一次 `add`。

---

## 8. 用官方 SDK（FastMCP）开发

手写协议是为了理解原理；生产开发请用 SDK。官方 Python SDK 的 `mcp` 包提供 **FastMCP** 高级 API，本目录的 fastmcp_demo.py 用十几行复刻了 server.py 的全部功能：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("note-demo")

@mcp.tool()
def add(a: float, b: float) -> float:
    """计算两个数字的和。"""
    return a + b

@mcp.resource("note://welcome")
def welcome() -> str:
    return "欢迎来到 MCP 世界！"

@mcp.prompt()
def greet(name: str) -> str:
    return f"请用热情友好的中文向 {name} 打招呼。"

if __name__ == "__main__":
    mcp.run()   # 默认 stdio 传输
```

SDK 自动完成：docstring → `description`、类型标注 → `inputSchema`、协议分发、传输层。安装（需联网，请手动执行）：

```bash
pip install mcp        # 或：uv add mcp
```

其他语言 SDK：TypeScript（`@modelcontextprotocol/sdk`）、C#、Java/Kotlin、Swift、Rust、Go——协议一致，API 风格各异。注意各 SDK 对 2026-07-28 无状态模型的支持进度不同，升级前看 release notes。

---

## 9. 安全：必须认真对待的部分

MCP 服务器 = **任意代码执行 + 数据访问**，规范把安全列为实现者义务，核心原则：

1. **用户同意与控制**：数据访问、工具调用都必须获得用户明确授权，界面要清楚展示服务器在干什么。
2. **数据隐私**：Host 未经同意不得把用户数据发给服务器，服务器也拿不到完整对话和其他服务器的数据（隔离由 Host 强制执行）。
3. **工具安全**：工具即代码执行；`description`、annotations 等元数据**视为不可信输入**（除非服务器可信）；调用前给用户确认机会，展示工具入参（防数据外泄）。
4. **传输安全**：HTTP 服务器必须校验 `Origin`（防 DNS rebinding）、本地只绑回环、实现 OAuth；图标等远程资源按不可信输入处理（禁 `javascript:`/`file:` 等 scheme、禁携带凭据获取、限制大小）。

本地场景的额外提醒：**往配置里加一个本地服务器 = 授予它你的用户权限执行代码**。只添加可信来源的服务器；优先官方/知名实现；`env` 里的密钥按敏感信息管理；对能写文件、执行命令的工具保持警惕。

开发者侧的最佳实践：最小权限（只给必要的目录/scope）、校验所有工具入参、限流、输出净化、超时、审计日志；客户端侧：对高危工具（`destructiveHint`）弹确认、校验工具结果再喂给模型、注意 prompt injection（工具返回的文本可能挟带指令）。

---

## 10. 学习路径与资源

建议顺序：

1. 跑通本目录 `python client.py`，对照第 3 章读懂每一条报文；
2. 完成 7.4 的四个练习（尤其是第 4 个：接进真实宿主）；
3. 用 FastMCP 把自己的一个小需求（读某个 API、查自己的数据库）写成服务器，按第 4 章接进 Claude Desktop 或 Cursor；
4. 读一遍官方规范（重点：architecture、basic、server/tools 三章）+ 安全最佳实践文档；
5. 深入：Tasks 扩展（ext-tasks 仓库）、MCP 授权框架、各语言 SDK 源码。

权威资源：

- 规范与文档：<https://modelcontextprotocol.io>（specification 按版本归档，schema.ts 是唯一事实来源）
- 规范仓库与 SEP（协议增强提案）：<https://github.com/modelcontextprotocol/specification>
- SDK 与参考服务器：<https://github.com/modelcontextprotocol>
- 社区服务器合集：awesome-mcp-servers

---

## 附录：本目录文件清单

| 文件 | 说明 |
|------|------|
| `README.md` | 本文档 |
| `server.py` | 纯标准库手写的 stdio MCP 服务器（2026-07-28 规范最小实现） |
| `client.py` | 纯标准库手写的 MCP 客户端，打印全部协议报文 |
| `probe.py` | 本地调试探针：绕过宿主直连服务器，快速定位问题 |
| `fastmcp_demo.py` | 官方 SDK FastMCP 版同功能服务器（需 `pip install mcp`） |

> 协议细节以官方规范为准。本文基于 2026-07-28 版撰写；该版本变化很大，阅读 2025 年的教程时请注意「握手式连接 vs 无状态请求」「服务器主动请求 vs MRTR」「GET 流/会话 vs 单一端点」三处时代差异。







### 术语 

<details>
<summary>实现方式</summary> if redis.exists(request_id):
        return cached_response
</details>

<details>
<summary>幂等性</summary>
<p>指同一个操作执行一次和执行多次，产生的结果一致。</p>
<pre><code class="language-python">if redis.exists(request_id):
    return cached_response</code></pre>
</details>

<details>
<summary><strong>前端相关术语</strong></summary>

<details>
<summary><strong>SSR</strong></summary>
<p>服务端渲染，页面在服务器上生成 HTML 后返回。</p>
</details>

<details>
<summary><strong>CSR</strong></summary>
<p>客户端渲染，浏览器下载 JS 后再渲染页面。</p>
</details>

</details>