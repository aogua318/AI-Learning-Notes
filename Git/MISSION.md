# Mission: Git 与 GitHub 推送 / 协作

## Why

把学习项目可靠地备份、展示到 GitHub，并能在日常开发中安全地管理历史与分支。目标不是背命令，而是理解 Git 的快照、引用和远程跟踪模型——遇到 non-fast-forward、认证失败、分支分叉时，能自己判断原因并救火。

## Success looks like

- 能把任意本地项目推到 GitHub（HTTPS + PAT/GCM 或 SSH），并说出每一步让文件在哪个区域之间移动。
- 看到 `! [rejected] ... non-fast-forward` 能解释原因，按「fetch → 看清分叉 → pull --rebase → push」自救；知道 `--force-with-lease` 的适用边界。
- 能画出 commit、分支、HEAD、`origin/main` 的关系，解释 merge 与 rebase 对历史和哈希的影响。
- 用本地裸仓库沙箱独立完成 push / pull / fetch / 冲突 / PR 前置流程，不依赖网络。
- 不把密钥、大文件、构建产物提交进仓库。

## Constraints

- Windows 10/11 + Git Bash，Git 2.55；GitHub 规则以 2026-09 为准（密码推送已移除）。
- 英语水平有限：术语保留英文原文并附中文对照（如 remote-tracking branch / 远程跟踪分支）。
- 偏好机制级解释与可复现的跨机器配置；课程要能离线打开。
- 课程形态：HTML 互动课，每节 15–20 分钟，一个知识点 + 一个图或互动 + 沙箱练习；图默认可放大。
- 不在公司仓库/设备上做实验；不执行未经确认的破坏性远程操作。

## Out of scope

- Git 对象存储格式（loose object / packfile）与源码级实现。
- Git LFS、submodule、`git filter-repo`、`bisect` 的深入用法（只作索引了解）。
- GitHub Actions、企业权限模型、复杂 monorepo 工作流。
- 多人实时协作的冲突策略细化（先掌握个人 + 小团队 PR 流程）。
