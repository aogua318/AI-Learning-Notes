# SETUP：新机器恢复指南

本仓库已包含全部学习内容：文档、示例代码、参考例子源码、5 张图解、29 个项目级 skill。克隆到新电脑后，只需要按本清单补齐"仓库之外"的工具与依赖，即可无缝衔接学习。

## 1. 基础工具链

| 工具 | 用途 | 安装方式 |
|---|---|---|
| Python 3.12+ | 各学习项目的示例代码 | python.org，或 `winget install Python.Python.3.12` |
| uv | 虚拟环境与依赖管理（AGENTS.md 规定每个学习子目录自建 `.venv`，根目录不建共享 venv） | `winget install astral-sh.uv`，或 <https://docs.astral.sh/uv/> |
| Git for Windows | 版本控制；自带 Git Bash，教程中的 shell 示例均可直接运行 | `winget install Git.Git` |
| Node.js | archify 技能图表渲染器（`node bin/archify.mjs render ...`）及 npx skills CLI | `winget install OpenJS.NodeJS.LTS` |
| ZCode | AI 教学工作流（本仓库的 AGENTS.md / SKILLS.md 为其配置） | 按你的 ZCode 安装方式 |

## 2. 各学习目录的依赖

大部分目录零依赖，直接运行：

| 目录 | 需要什么 | 恢复方式 |
|---|---|---|
| ADB | Android platform-tools（`adb` 命令） | `winget install Google.PlatformTools`（或 brew / apt，见 ADB/README.md 第 1 章） |
| Git | 仅 Git 本身；练习沙箱用脚本重建 | 见第 3 节 |
| MCP | `client.py` / `server.py` / `probe.py` 纯标准库，直接 `python client.py` 即可；`fastmcp_demo.py` 需要官方 SDK 的 `mcp` 包 | `cd MCP && uv venv && uv pip install mcp`（或 `uv add mcp`） |
| Rust-Driver | Rust 工具链 + 嵌入式目标（rustup，UF2 拖拽烧录，不用 WSL） | 装好 rustup 后执行 `rustup target add thumbv6m-none-eabi`；细节见 Rust-Driver/RESOURCES.md |
| From-Scratch | Python 部分全程纯标准库；md5 篇打包 exe 的环节需要 Cython 和 C 编译器 | `uv pip install cython`；编译器安装见 md5-tutorial.md 第 7 节 |
| Japanese-Travel | 无依赖（纯 HTML/CSS/JS，浏览器直接打开） | —— |

虚拟环境一律建在对应子目录内（`cd <Topic> && uv venv`），根 `.gitignore` 已排除 `.venv/` 和 `__pycache__/`，不会误提交。

## 3. 被 git 排除内容的再生

- **Git/sandbox/**（练习沙箱，由脚本生成，不入库）：在 Git 目录执行 `bash git_sandbox.sh --reset` 一键重建，练习剧本见 Git/README.md 第 12 章。
- MCP 参考例子源码（ida-pro-mcp、cheatengine-mcp-bridge）已完整入库，无需恢复。

## 4. teach 学习工作区如何续接

`Rust-Driver/` 与 `Japanese-Travel/` 是 teach 工作区，学习状态全部存在仓库里：MISSION.md（学习动机）、NOTES.md（进度、偏好、待核实事项）、RESOURCES.md（高信任资料）、learning-records/（学习记录）。克隆后在对应目录运行 `/teach <主题>`，AI 会依据这些文件推知你的最近发展区，从中断处继续。

## 5. 技能（skill）

- **29 个项目级 skill 已随仓库分发**（`.zcode/skills/`，仅在本仓库生效），克隆即得，无需安装；清单与使用时机见根目录 SKILLS.md。
- 个人的 `E:\Skills库`（222 个技能）是仓库外的独立收藏，不随本仓库走，需要时另行恢复。

## 6. 推送到 GitHub 的认证

新机器首次推送需要凭据：GitHub 已移除密码登录，必须用 PAT 或 SSH（Git Credential Manager 会引导你配置）。详见 Git/README.md 第 5 章。
