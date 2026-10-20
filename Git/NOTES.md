# NOTES.md — Git 教学工作区

## 用户偏好与背景

- 中文授课；Git 术语保留英文原文并附中文对照（remote-tracking branch / 远程跟踪分支、fast-forward / 快进合并等）。
- 偏好机制级解释：先讲「为什么」，再看命令；重视可复现的跨机器配置。
- 2026-10-20 选定课程形态：HTML 互动课（teach 工作区），四组图全要——快照与提交链、三区与远程地图、推送被拒急救、分支与 merge/rebase。
- 现有 `Git/README.md` 是 630 行的速查长文，保留为参考，不整体改写成 HTML；课程与 README 互相链接，避免内容漂移。

## 课程设计

- 0001 快照与引用：commit = 快照 + 父指针；branch / HEAD 是指针。互动：四步 SVG 切换（初始 → 建 feature → 在 feature 提交 → 切回 main）。
- 0002 三区与远程地图：工作区 / 暂存区 / 本地仓库 / 远程；`origin/main` 是本地缓存的远程地图。图：archify architecture。
- 0003 推送被拒急救：non-fast-forward 的原因与 `pull --rebase` 自救；`--force-with-lease` 边界。图：archify lifecycle。
- 0004 merge vs rebase：fast-forward、merge commit、rebase 重放的拓扑差异与黄金法则。图：手写 SVG 四面板。
- 每节课后练习统一使用 `Git/sandbox/`，不碰真实 GitHub；沙箱玩坏可 `bash git_sandbox.sh --reset` 重建。

## 组件库状态

- `assets/lesson.css`：从 `Rust-Driver/assets/lesson.css` 复制，改为 Git 课程配色；新增 tab 切换、提交图、术语表样式。
- `assets/zoomable-figure.js`：从 `Rust-Driver/assets/` 复制（滚轮以光标为中心缩放、拖拽平移）。
- `assets/quiz.js`：从 `Japanese-Travel/assets/quiz.js` 复制，计分文案改为 Git 课程通用文案。
- `assets/diagram-tabs.js`：新增；按钮切换预绘 SVG 面板，并在状态栏显示该步发生了什么。
- 图约定：`figure` 同时带 `figure-zoom` 与 `data-zoomable`，内置 `.zoom-badge`，页面底部引入 `../assets/zoomable-figure.js`。

## 沙箱现状（2026-10-20）

- `Git/sandbox/work/` 目前只有两个默认文件，**没有 `.git`**；`sandbox/remote.git/` 是空裸仓库。说明历史沙箱是中断或旧版本留下的不完整状态。
- 课程中已写明：先 `bash git_sandbox.sh --reset` 重建（会清空沙箱内容，目前内容为脚本默认值）。
- 不要在未确认时替用户执行 `--reset`；这是删除操作。

## 交付与验证（2026-10-20）

- 已交付 4 节课 + 2 个速查页（`reference/glossary.html`、`reference/push-rescue.html`）；`README.md` 顶部已加入口。
- 已用 Edge CDP 在 1200×900 与 390×844 下实际渲染检查；四节课的 tab、quiz、放大/收起（含 Esc 与滚动锁）均通过，控制台无报错。
- 四节课答案键：0001 b/b/c/b；0002 b/c/c/a；0003 b/b/a/b；0004 b/b/b/b。
- 宽幅 archify 图（0002 architecture、0003 lifecycle）改为「全幅出血」：在桌面突破 44rem 正文栏，按视口宽度铺开；窄屏回到 100% 并保留横向滚动。此前 960px 最小宽度会把右侧远程区/终点裁掉。
- archify 图注增加右侧留白，避免右下角「点击放大」按钮压住文字。
- 本地引用检查：7 个页面共 55 条本地链接/资源引用，无缺失。

## 待办

- 用户完成课程后：按课号写 `learning-records/`（首次学习记录时才建目录），并把术语表晋升情况补进本文件。
- 沙箱仍是不完整状态；用户第一次做练习前需确认是否执行 `bash git_sandbox.sh --reset`。
- `.archify/` 下的渲染产物、截图与临时脚本只用于本次验证，不进入 git；如需要可加入根 `.gitignore`。
