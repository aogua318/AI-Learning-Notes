# Skill 使用说明

本仓库的技能分两个来源：**项目级**（`.zcode/skills/`，仅在本仓库生效）和 **ZCode 内置插件**（全局可用；用户级默认不装技能，保持干净）。本文说明什么时候该调用哪个。

## 场景速查

| 场景 | 调用 |
|---|---|
| 想学一个新东西、准备开新学习项目 | `brainstorming`（明确目标与范围）→ `writing-plans`（写实施计划） |
| 计划已写好，开始执行 | `executing-plans` |
| 写有实际功能的代码（如 Rust-Driver） | `test-driven-development` |
| 遇到 bug、报错、行为和预期不符 | `systematic-debugging` |
| 多个互不依赖的任务想并行推进 | `dispatching-parallel-agents` |
| 宣称"做完了 / 修好了"之前 | `verification-before-completion` |
| 想让 AI 审查刚写的代码 | `requesting-code-review` |
| 收到审查意见要处理 | `receiving-code-review` |
| 写教程、说明文档、提案 | `doc-coauthoring` |
| 画架构图 / 流程图 / 时序图 | `archify`（独立 HTML，可交互） |
| 在 markdown 教程里内嵌图表 | `design-doc-mermaid`（Mermaid） |
| 记笔记想用 Obsidian 双链 / callout 语法 | `obsidian-markdown` |
| 把学习笔记做成 Anki 记忆卡片 | `anki-connect` |
| 学新技术前做资料调研 | `research` |
| 建虚拟环境 / 管理 Python 依赖 | `uv-package-manager` |
| 提交代码，想要规范提交信息 | `conventional-commit` |
| 想被循序渐进地教一个概念 | `teach`（输入 `/teach <主题>`） |
| 开课前预检 HTML 互动课（答案键、反馈极性、计分） | `lesson-quiz-preflight` |
| 想法 / 计划想被压力测试 | `grilling`（或 `/grill-me`） |
| 想找新 skill | `find-skills` |
| 用浏览器查资料 / 测试网页 | `agent-browser` 或 `browser-use:control-browser` |
| 开发 MCP 服务器 | `mcp-server-spec-driven-development` |
| 交互式可视化讲解某个原理 | `visualize` |

## 调用方式

- 大多数 skill 由 AI 按场景自动触发，直接用自然语说明要做的事即可；
- `teach` 为仅手动调用，需输入 `/teach <想学的东西>`；
- 本仓库已安装技能见 `.zcode/skills/` 目录（30 个）。

## 典型学习工作流

```
brainstorming → writing-plans → executing-plans
  → test-driven-development / systematic-debugging（开发中循环）
  → verification-before-completion → conventional-commit 提交
```

写教程阶段：`doc-coauthoring` 打磨文档 → `archify` / `design-doc-mermaid` 配图；长期学习用 `teach` 工作区 + `anki-connect` 做记忆卡片。

**teach × archify 搭配**：teach 工作区（如 `Rust-Driver/`、`Japanese-Travel/`）的课程与 reference 文档配图用 `archify`——生成的 SVG 内联进单文件课程，保持课程自包含；markdown 教程（如 `From-Scratch/`）则用 `design-doc-mermaid` 的 Mermaid 代码块（GitHub 原生渲染）。

**课程图表默认可放大（通用约定）**：teach 工作区课程里的图表默认带放大能力——`<figure>` 加 `class="figure-zoom"`（与 `archify-figure` 并存）和 `data-zoomable` 属性，内置 `<button class="zoom-badge">⤢ 点击放大</button>`，并在 `</body>` 前引入 `../assets/zoomable-figure.js`。点徽章或图表变身为近全屏浮层，浮层内**滚轮以当前光标位置为中心缩放**（1~8 倍）、拖拽平移，再点徽章、按 Esc 或点浮层任意处（图注链接除外）收起；实现上不搬移 DOM 节点（iframe 场景追加一个透明事件捕获层），只切 class 加宽高/位移（布局式缩放，SVG 文字放大不糊），SVG 内部引用和页面状态都不会丢。组件与配套 CSS 以 `Rust-Driver/assets/zoomable-figure.js` 及其 lesson.css 中的“可放大图表组件”段为准，新工作区复制这两处即用。注意：课程图保留内联 SVG 而不换成 iframe——内联 SVG 已接好 archify 主题样式（暗色模式都适配了），想要带动画的完整版才走图注里的交互版链接。

## 技能库（E:\Skills库）

2026-10 从网络下载的 6 个技能——`uv-package-manager`、`research`、`obsidian-markdown`、`anki-connect`、`design-doc-mermaid`、`conventional-commit`——已装入本仓库项目级，并同时归档进 `E:\Skills库`（共 222 个技能）。

需要启用技能库中的其他技能时，从 `E:\Skills库` 复制到 `.zcode/skills/` 即可；技能库总清单见 `E:\Skills库\skill.md`。
