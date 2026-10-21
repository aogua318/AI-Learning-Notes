# Git 学习文档（重点：推送到 GitHub）

> **Git** 是分布式版本控制系统：给项目记「存档点」（commit），让你随时回溯、并行开发（分支）、和他人协作（远程同步）。**GitHub** 是托管 Git 仓库的云平台——「推送到 GitHub」就是把本地存档同步到云端，实现备份、协作与展示。
>
> 本文重点放在**从本地仓库到 GitHub 远程仓库的完整链路**：远程模型 → 认证配置（HTTPS/PAT 与 SSH）→ 三种典型推送场景 → Pull Request 协作 → 推送错误急救。前面的本地基础（commit/分支）压成两章速成，保证零基础也能一路读下来。
>
> 环境基准：Git 2.55（Windows / Git Bash），2026-09 的 GitHub 规则（密码登录已于 2021 年移除，必须 PAT 或 SSH）。
>
> 配套文件：[git_sandbox.sh](#12-附录目录文件与沙箱使用说明) —— 一键搭建「本地远程」沙箱，不碰 GitHub 就能完整练习 push/pull/fetch/冲突解决。

---

## 目录

0. [Git 是什么：版本控制的原理](#0-git-是什么版本控制的原理)
1. [安装与首次配置](#1-安装与首次配置)
2. [本地基础：add → commit → log](#2-本地基础add--commit--log)
3. [分支：merge / rebase / stash](#3-分支merge--rebase--stash)
4. [远程仓库模型：origin / fetch / push（重点）](#4-远程仓库模型origin--fetch--push重点)
5. [GitHub 认证：HTTPS+PAT 与 SSH（重点）](#5-github-认证httpspat-与-ssh重点)
6. [推送到 GitHub：三种实战场景（重点）](#6-推送到-github三种实战场景重点)
7. [.gitignore 与仓库卫生](#7-gitignore-与仓库卫生)
8. [团队协作：Pull Request 工作流（重点）](#8-团队协作pull-request-工作流重点)
9. [推送急救与常见错误速查表](#9-推送急救与常见错误速查表)
10. [安全：绝对不要提交的东西](#10-安全绝对不要提交的东西)
11. [学习路径与资源](#11-学习路径与资源)
12. [附录：目录文件与沙箱使用说明](#12-附录目录文件与沙箱使用说明)

---

## 0. Git 是什么：版本控制的原理

### 0.1 快照，不是差异

很多人以为 Git 存的是「每次改动的差异」，其实 Git 存的是**快照**：每次 commit 记录当时**整个项目所有文件的指针**。没变的文件直接引用上一个快照里的同一份内容，变了才存新版本。这个设计让分支、回溯、对比都变成指针操作，快而可靠。

### 0.2 三个区域

理解 Git 的关键心智模型——文件在三个区域之间流动：

```
 工作区                暂存区               本地仓库              远程仓库
(Working Dir)        (Staging/Index)      (.git 目录)          (GitHub)
    │   git add          │   git commit       │   git push        │
    │ ────────────────>  │ ────────────────>  │ ───────────────>  │
    │                    │                    │                   │
    │ <──────────────── git restore        │ <───────────────── git pull/fetch
    │                    (从暂存区恢复)      │  (git clone 全量复制)
```

- **工作区**：你正在编辑的文件；
- **暂存区**：下次 commit 要包含哪些改动——Git 强迫你「选好再存档」，所以能精确控制每个 commit 的内容；
- **本地仓库**：`.git` 目录里的完整历史（**含全部版本**，所以离线也能看日志、切分支）；
- **远程仓库**：GitHub 上的那份副本，本地仓库与它是**对等的独立仓库**，靠 push/fetch 同步。

> 可交互版本（四区状态 + fetch/pull 到底动了哪一层）：[Git 状态与引用图](reference/git-state-and-refs.html)。

### 0.3 提交历史是一条链

每个 commit 包含：**完整的树（快照）+ 作者/时间 + 说明 + 上一个 commit 的哈希**。哈希（SHA-1，如 `a1b2c3d`）由内容算出——改了内容哈希必变，所以历史链不可篡改，哈希就是每个存档点的「身份证」。

分支的本质也极其简单：**指向某个 commit 的可移动指针**（一个 41 字节的文件而已）。`main`、`dev` 都只是指针名；`HEAD` 是「你当前站在哪个分支/提交上」的指针。切分支 = 移动 HEAD，瞬间完成，没有复制。

```
              ┌─────┐      ┌─────┐      ┌─────┐
 (main) ───>  │ c3  │ <──  │ c2  │ <──  │ c1  │
              └─────┘      └─────┘      └─────┘
                 ▲ HEAD
```

### 0.4 本地仓库 vs 远程仓库

这是本文的主线：**clone 下来的仓库和 GitHub 上的仓库是两个对等仓库**，GitHub 不比你「高级」，它只是大家约定同步的那一份。本地仓库里有两个「信箱」负责和远程对账：

- `origin/main`（远程跟踪分支）：**上次与远程同步时**远程 main 的位置——本地缓存的「远程地图」；
- `git fetch` 刷新这张地图；`git push` 把你的提交搬过去；`git pull` 把对方的搬过来。

「推送被拒绝」的全部故事，都发生在「你地图过期了」这一件事上（详见第 4.4 与第 9 章）。

---

## 1. 安装与首次配置

### 1.1 安装

- Windows：[git-scm.com](https://git-scm.com) 下载 Git for Windows（自带 Git Bash 和 Git Credential Manager——后者是第 5 章 HTTPS 认证的关键）；或 `winget install Git.Git`；
- macOS：`brew install git` 或装 Xcode Command Line Tools；
- Linux：`sudo apt install git`。

### 1.2 必做的首次配置

```bash
git config --global user.name "你的名字"          # 会写进每个 commit
git config --global user.email "you@example.com" # 建议用 GitHub 账号邮箱（隐私见下方提示）
git config --global init.defaultBranch main      # 新仓库默认分支叫 main（与 GitHub 一致）
git config --global core.autocrlf input          # Windows 换行符设置，见 9.4
```

> 隐私提示：GitHub 用邮箱关联 commit 与你的头像/贡献图。不想公开真实邮箱？在 GitHub 设置里获取 `12345+username@users.noreply.github.com` 形式的替代邮箱并配置在这里，同时保持两个邮箱一致（commit 用的邮箱 = GitHub 绑定的邮箱，贡献才算到你头上）。

验证与常用配置操作：

```bash
git config --list --global      # 看全部全局配置
git config --global alias.st status      # 别名：以后敲 git st
git config --global alias.lg "log --oneline --graph --all --decorate"
git config --global --unset xxx.yyy      # 删某项配置
```

---

## 2. 本地基础：add → commit → log

```bash
git init                       # 把当前目录变成 Git 仓库（生成 .git/）
git status                     # 最常用的命令：哪里改了、哪些已暂存
git add 文件名                  # 单个文件进暂存区
git add .                      # 全部改动进暂存区
git add -p                     # 交互式选择部分改动（分块提交利器）
git commit -m "说明这次为什么改"  # 存档；-m 直接写说明
git commit -am "说明"           # 已跟踪文件的改动 add+commit 一步走（新文件仍要 add）
git log --oneline --graph --all --decorate   # 一图看全部历史与分支
git diff                       # 工作区 vs 暂存区
git diff --staged              # 暂存区 vs 上次 commit
git diff HEAD~1                # 和上一个 commit 比
```

**commit message 写法**：一行 50 字以内说明「为什么改」，祈使句，如 `fix: 空列表分页崩溃`；团队常用 Conventional Commits 前缀（`feat:` 新功能 / `fix:` 修复 / `docs:` 文档 / `refactor:` 重构 / `chore:` 杂务）。**别写 "update"**——三个月后的你会感谢现在写清楚的你。

### 撤销操作（本地，按「改动走到哪一步」对症下药）

```bash
git restore 文件名               # 丢弃工作区改动（未 add）——不可恢复，慎用
git restore --staged 文件名      # 从暂存区撤回（已 add，未 commit）
git commit --amend              # 补充/修改上一次 commit（还没 push 时）
git restore --source=HEAD~1 文件 # 把某文件恢复到上个版本
git revert <hash>               # 生成一个"反向 commit"抵消某次提交——唯一安全的"撤销已推送提交"方式
git reset --soft HEAD~1         # 撤销 commit，改动退回暂存区
git reset --mixed HEAD~1        # 撤销 commit+add，改动留在工作区（默认）
git reset --hard HEAD~1         # 彻底丢弃最近一次 commit 及改动——不可恢复，慎用
```

> `reset` 改写历史（commit 没了），`revert` 追加历史（错误保留、用新提交抵消）。**已 push 的提交一律用 revert**，原因见第 9 章。

---

## 3. 分支：merge / rebase / stash

### 3.1 日常分支操作

```bash
git switch -c feature/login    # 创建并切换到新分支（现代写法）
git switch main                # 切回 main
git branch                     # 列出本地分支
git branch -a                  # 含远程分支
git branch -d feature/login    # 删除已合并分支（-D 强删）
git merge feature/login        # 在 main 上合入 feature 分支
git log --graph --oneline --all   # 随时看分支拓扑
```

### 3.2 合并的三种结局

1. **快进（fast-forward）**：main 自分叉后没新提交 → 指针直接前移，历史成一条线；
2. **正常合并**：两边都有新提交 → Git 自动生成一个合并 commit（`--no-ff` 强制生成，保留"这里发生过合并"的痕迹）；
3. **冲突**：两边改了同一处 → 自动合并失败，进入冲突解决。

### 3.3 冲突解决（必会）

冲突时 `git status` 列出冲突文件，文件里长这样：

```
<<<<<<< HEAD
main 分支上的内容
=======
feature 分支上的内容
>>>>>>> feature/login
```

解决三步：**手工编辑文件**（留下想要的版本，删掉 `<<<<<<<` 等标记）→ `git add 文件` → `git commit`（merge 冲突时）或 `git rebase --continue`（rebase 冲突时）。中途想放弃：`git merge --abort` / `git rebase --abort`。

### 3.4 rebase 与它的黄金法则

```bash
git switch feature && git rebase main   # 把 feature 的提交"搬"到 main 最新提交之后
```

rebase 相当于把你的提交**逐个重放**到新基点上，历史变成一条直线——干净，但**重放产生的 commit 哈希全部变了**。所以：

> **黄金法则：已经 push 到共享分支的提交，不要 rebase**（他人基于旧哈希的工作会全部错乱）。rebase 只用于：未推送的本地提交；或你确认只有自己在用的分支（此时推送需 `--force-with-lease`，见 9.1）。

个人开发推荐主线用 rebase 拉平、协作分支用 merge——团队约定优先。

### 3.5 stash 与 cherry-pick

```bash
git stash        # 手头改到一半，又必须切分支？把改动暂存进"口袋"
git stash pop    # 切回来后取出（stash list / stash apply stash@{1}）
git cherry-pick <hash>  # 把别的分支上的某一个 commit 单独"摘"过来
```

---

## 4. 远程仓库模型：origin / fetch / push（重点）

### 4.1 remote：给远程仓库起名字

remote 就是「远程仓库的地址 + 名字」。名字只是本地代号，惯例 `origin` 指**你自己的远程仓库**，`upstream` 指**原项目仓库**（fork 场景）。

```bash
git remote -v                        # 查看所有远程（fetch/push 两条地址）
git remote add origin https://github.com/you/repo.git    # 添加
git remote rename origin github                          # 改名
git remote remove origin                                 # 删除
git remote set-url origin git@github.com:you/repo.git    # 改地址（换认证方式时常用）
```

`git clone <url>` 做了三件事：完整复制远程仓库 → 本地分支与远程分支对应 → 自动把来源命名为 `origin`。所以**从 GitHub 开始做项目**时不需要 remote add。

### 4.2 远程跟踪分支与 -u

第一次 `git push -u origin main` 时发生了两件事：① 上传并让远程建好 `main`；② 记录「本地 main ↔ origin/main」的对应关系（upstream）。之后这条分支上就可以偷懒：

```bash
git push            # 知道推到 origin main
git pull            # 知道从 origin main 拉
git status          # 还能显示"领先/落后远程几个提交"
```

没配 -u 的分支每次都要写全 `git push origin 分支名`。`git branch -vv` 可以看每条分支的跟踪关系。

### 4.3 fetch vs pull vs push

```
             fetch(只取不合)         push(推你的提交)
  GitHub  <──────────────────  本地仓库  ─────────────────>  GitHub
             pull(取+合并=fetch+merge)
```

- **fetch**：把远程的新提交下载到本地，**更新 origin/main 这张地图**，但不碰你的工作区。安全，先看看别人改了什么再决定。
- **pull** = fetch + merge（或 `git pull --rebase` = fetch + rebase）。日常单人开发直接 pull 没问题；多人开发建议 `pull --rebase` 或先 fetch 看一眼。
- **push**：把你本地领先远程的提交上传。**Git 的铁律：push 只允许快进**——你的提交必须建立在远程最新提交之上，否则拒绝（见 4.4）。

```bash
git fetch --all --prune     # 取回全部远程更新，并清掉已在远程删除的分支引用
git push origin feature     # 推送本地分支（远程自动创建同名分支）
git push origin :old-branch # 删除远程分支（推送"空"过去）；或 git push -d origin old-branch
git push --tags             # 推送标签（git tag v1.0 打标签；push 默认不带 tag）
```

### 4.4 为什么会被拒绝：non-fast-forward

「推送被拒」的机制图解：

```
远程:   A ── B ── C          （别人推了 C，或你在网页上改了 README）
                 \
你本地:  A ── B ── D          （你基于 B 提交了 D，但不知道 C 的存在）

git push  → 远程发现"你的历史里没有 C"，如果接受 D 就会丢掉 C
          → 拒绝: ! [rejected] ... (fetch first / non-fast-forward)
```

正解是**先把自己的历史补全再推**：

```bash
git pull --rebase origin main   # 把你的 D 搬到 C 后面（推荐，历史线性）
git push
```

> 千万不要条件反射地 `--force`。强推会**抹掉远程上你不知道的提交**（比如同事刚推的 C）。确需强推（rebase 过自己的分支）也用 `git push --force-with-lease`——它会检查远程没有你未见过的新提交，是安全阀。

> 把 fetch → pull --rebase → push 三步连起来看：[参考页第 ③ 页「推送被拒」](reference/git-state-and-refs.html)。

### 4.5 本地远程：不出门就能练

没有 GitHub 也能拥有远程——`git init --bare` 创建一个**裸仓库**（只有仓库数据、没有工作区，专业远程仓库的本质），路径当 remote 用。配套的 `git_sandbox.sh` 就是这么搭的练习场，详见附录。

---

## 5. GitHub 认证：HTTPS+PAT 与 SSH（重点）

推送时 GitHub 要确认「你是你」。**2021 年 8 月起 GitHub 移除了密码推送**，只有两条路：HTTPS + Personal Access Token，或 SSH 密钥。

### 5.1 方式一：HTTPS + Personal Access Token（推荐新手）

**PAT（个人访问令牌）= 密码替代品**，用法：克隆/推送时用户名填 GitHub 用户名，密码栏粘贴 PAT。

创建 PAT：GitHub → Settings → Developer settings → Personal access tokens：

- **Fine-grained tokens（推荐）**：可限定到具体仓库、具体权限（只勾 `Contents: Read and write` 即可推送）；
- **Classic tokens**：勾 `repo` 作用域即覆盖私有/公共仓库读写。

认证一次后不想每次粘贴？Git for Windows 自带 **Git Credential Manager**：首次推送弹出浏览器 GitHub 授权页，点一下即完成 OAuth 认证，令牌存入 Windows 凭据管理器，之后全自动。所以 Windows 上最顺的路径其实是：**HTTPS + GCM，一路点浏览器**。

```bash
# HTTPS 地址形态：
git clone https://github.com/you/repo.git
git remote add origin https://github.com/you/repo.git
```

排查认证问题：`git credential-manager github list`（GCM）、控制面板 → 凭据管理器 → Windows 凭据，删掉 `git:https://github.com` 条目可强制重新认证。

### 5.2 方式二：SSH 密钥（推荐长期开发）

SSH 用「私钥在你电脑、公钥在 GitHub」的非对称加密证明身份，配好后永不再输任何东西。

```bash
# ① 生成密钥对（一路回车即可；-C 只是备注）
ssh-keygen -t ed25519 -C "you@example.com"
#    生成 ~/.ssh/id_ed25519（私钥，绝不外传）和 id_ed25519.pub（公钥）

# ② 把公钥内容贴到 GitHub：Settings → SSH and GPG keys → New SSH key
cat ~/.ssh/id_ed25519.pub     # 复制整行输出

# ③ 测试连接
ssh -T git@github.com         # 首次问是否信任，yes；成功回显 "Hi 用户名! You've successfully authenticated"
```

使用 SSH 地址（注意形态不同：`git@github.com:用户/仓库.git`，冒号无斜杠）：

```bash
git clone git@github.com:you/repo.git
git remote set-url origin git@github.com:you/repo.git   # 已有仓库从 HTTPS 切到 SSH
```

**多账号配置**（公司号+个人号共存）：`~/.ssh/config` 用 Host 别名区分：

```
# 个人号
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
# 工作号：地址要写成 git@github-work.com:company/repo.git
Host github-work.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_work
```

### 5.3 怎么选

| | HTTPS + PAT/GCM | SSH |
|------|-----------------|-----|
| 首次配置 | 最简单（浏览器点一下） | 生成密钥 + 贴公钥 |
| 日常体验 | 配好 GCM 后无感 | 配好后无感 |
| 多账号 | 麻烦 | `~/.ssh/config` 优雅支持 |
| 严格内网/代理 | 需要代理配置 | 22 端口可能被封（可改 443：`ssh.github.com`） |

结论：**个人开发 HTTPS 起步；长期/多账号切 SSH**。两者可以随时用 `git remote set-url` 互切，仓库数据不受影响。

---

## 6. 推送到 GitHub：三种实战场景（重点）

### 6.1 场景 A：已有本地项目，推上 GitHub（最高频）

第 1 步，在 GitHub 网页上：**New repository** → 起名 → **不要**勾选任何初始化选项（README/.gitignore/license 都不勾）→ Create。空仓库最省事，因为你本地已有历史。

第 2 步，在本地项目目录里：

```bash
git init                          # 还不是仓库的话
git add .
git commit -m "feat: 初始提交"
git remote add origin https://github.com/you/repo.git   # 挂上远程
git branch -M main                # 确保主分支叫 main（老仓库可能是 master）
git push -u origin main           # 首推 + 建立跟踪
```

四个易错点：

1. **远程仓库必须为空**（或至少没有会冲突的提交）。如果建仓库时勾了 README，首推会被拒——先 `git pull --rebase origin main` 把那个提交合进来再推；
2. `git remote add origin ...` 报 **already exists** → 说明之前挂过，用 `git remote set-url origin 新地址` 改地址即可（9.3）；
3. 报 **authentication failed** → 认证问题，回第 5 章（HTTPS 用户填 PAT / GCM / 切 SSH）；
4. 推完刷新 GitHub 网页验证；commit 列表里头像没亮 = commit 邮箱和 GitHub 绑定邮箱不一致（1.2 节）。

### 6.2 场景 B：从 GitHub 开始（新项目）

在 GitHub 上建好带 README 的仓库后：

```bash
git clone https://github.com/you/repo.git   # 完整拉下来，origin 已自动配好
cd repo
# ...写代码...
git add . && git commit -m "feat: xxx"
git push                                    # 以后就这两个动作循环
```

日常循环就三句：`git pull`（开工前对齐）→ 改代码 `git add` + `git commit` → `git push`。

### 6.3 场景 C：参与开源项目（fork + PR）

你**没有**别人仓库的写权限，标准流程是「fork 出自己的副本 → 改自己的副本 → 发 PR 请求合入原仓库」：

```bash
# ① 网页上点 Fork，得到 you/other-project
git clone https://github.com/you/other-project.git
cd other-project
git remote add upstream https://github.com/author/other-project.git  # ② 挂上原项目

# ③ 开功能分支干活
git switch -c fix-typo
git commit -am "docs: 修正拼写"

# ④ 推到【自己的 fork】（你只对自己的仓库有写权限）
git push -u origin fix-typo

# ⑤ 网页上你的 fork 会出现 "Compare & pull request" 按钮 → 发 PR 到原项目
```

PR 被评审期间，同步上游最新代码：

```bash
git fetch upstream && git rebase upstream/main
git push --force-with-lease        # rebase 过自己的 PR 分支，安全强推
```

PR 合并后，删功能分支、同步自己 fork 的 main。

---

## 7. .gitignore 与仓库卫生

`.gitignore` 放在仓库根目录，声明哪些文件**不进入版本管理**（构建产物、日志、依赖目录、IDE 配置、密钥）：

```gitignore
# 注释：一行一个模式
node_modules/      # 斜杠结尾 = 目录
*.log              # 通配所有 .log
/dist              # 只忽略根目录下的 dist
!important.css     # 感叹号 = 例外，不忽略
**/temp/           # ** = 任意层级
.env               # 密钥文件，必忽略（见第 10 章）
```

三个常见坑：

1. **已被跟踪的文件不受 .gitignore 影响**（它只管"未跟踪"文件）。加规则前已经 commit 过的文件要主动移出跟踪但保留本地：
   ```bash
   git rm -r --cached .    # 把所有文件移出暂存（--cached = 不删本地文件）
   git add .
   git commit -m "chore: 应用 .gitignore"
   ```
2. **全局忽略**自己编辑器的杂物（如 `.idea/`、`Thumbs.db`）放全局配置，不污染项目文件：`git config --global core.excludesFile ~/.gitignore_global`；
3. 拿现成模板：[github.com/github/gitignore](https://github.com/github/gitignore) 收录了各语言模板。

---

## 8. 团队协作：Pull Request 工作流（重点）

PR（Pull Request）不是 Git 命令，是 GitHub 的协作机制：**「我请求把我分支上的提交合进目标分支」**，附带走代码评审、CI 检查、讨论记录。

### 8.1 标准流程（feature branch workflow）

```bash
git switch main && git pull                 # ① 开工前同步最新
git switch -c feature/xxx                   # ② 开功能分支
# ...开发、若干次 commit...
git push -u origin feature/xxx              # ③ 推分支（会自动给出创建 PR 的链接）
# ④ 网页上发起 PR：base 选目标分支，compare 选你的功能分支
# ⑤ 评审通过 → Merge（或 Squash and merge）
git switch main && git pull                 # ⑥ 合并后同步，删除功能分支
git branch -d feature/xxx && git push -d origin feature/xxx
```

### 8.2 三种合并按钮的取舍

| 方式 | 效果 | 适用 |
|------|------|------|
| Merge commit | 保留全部提交 + 一个合并节点 | 想保留完整开发过程 |
| **Squash and merge** | 整个 PR 压成 main 上**一个** commit | main 历史洁癖，最常用 |
| Rebase and merge | 提交线性接到 main 上，无合并节点 | 同上，但保留多个提交 |

### 8.3 用 gh CLI 把流程搬进终端（可选）

安装 [gh CLI](https://cli.github.com) 后，开仓库、发 PR 不用碰浏览器：

```bash
gh auth login                        # 浏览器授权（也解决 git 的 HTTPS 认证）
gh repo create my-repo --public --source=. --push   # 建远程仓库并直接推当前项目
gh pr create --fill                  # 基于 commit 信息发 PR
gh pr status / gh pr checks          # 查 PR 状态/CI 结果
gh pr merge --squash --delete-branch # 终端里合并
```

> 本机环境检测：git 已装（2.55），gh 未安装——需要时 `winget install GitHub.cli` 后 `gh auth login`。

---

## 9. 推送急救与常见错误速查表

### 9.1 push 相关

| 报错 | 原因 | 处理 |
|------|------|------|
| `! [rejected] main -> main (fetch first)` / `(non-fast-forward)` | 远程有你没有的提交（4.4 图解） | `git pull --rebase` 再 push。**别 --force** |
| `remote: Support for password authentication was removed` | 还在用账号密码 | 改 PAT（5.1）或 SSH（5.2） |
| `Authentication failed for 'https://github.com/...'` | 令牌过期/无权限/凭据缓存旧密码 | PAT 重新生成；删 Windows 凭据管理器里的 git 条目重登；或 `remote set-url` 切 SSH |
| `ERROR: Repository not found` / `Permission to ... denied` | 地址错、仓库是私有且你没权限、SSH key 绑的是别的账号 | 核对 URL；`ssh -T git@github.com` 看认证成了谁 |
| `fatal: The current branch has no upstream branch` | 新分支第一次推没带 -u | `git push -u origin 分支名` |
| `remote contains work you do not have`（建仓库勾了 README） | 远程初始化提交 vs 你的首推 | `git pull --rebase origin main` 后再推 |
| `file exceeds ... 100.00 MB` | GitHub 单文件上限 100MB（>50MB 警告） | 移出版本管理；真要存大文件用 [Git LFS](https://git-lfs.com)：`git lfs install && git lfs track "*.psd"` |
| `push protection` 拒绝 | 提交内容里检测到 GitHub 已知泄露的密钥格式 | **正确做法是作废该密钥**，而不是绕过；误报才可绕过一次 |

> 其中 non-fast-forward 的三步自救（fetch → pull --rebase → push）有一张分步图：[参考页第 ③ 页](reference/git-state-and-refs.html)。

### 9.2 通用排障

| 报错 | 原因 | 处理 |
|------|------|------|
| `fatal: not a git repository` | 当前目录（及上级）没有 .git | 先 `git init`，或 cd 到仓库根 |
| `remote origin already exists` | 重复 remote add | `git remote set-url origin 新地址` |
| `Please tell me who you are` | 没配 user.name/email | 第 1.2 节 |
| `nothing to commit, working tree clean` | 改动其实没保存/不在仓库范围 | `git status` 逐区检查；文件是否被 .gitignore 忽略：`git check-ignore -v 文件名` |
| `detached HEAD` 警告 | 直接 checkout 了某个 commit | 只是看历史没问题；要在其上开发就 `git switch -c 新分支` |
| 不小心 commit 了不该提交的文件 | —— | 还没 push：`git reset --soft HEAD~1`，处理完重新 commit；已 push：删文件新提交 + 轮换泄露的密钥（第 10 章） |
| `LF will be replaced by CRLF` 刷屏 | Windows 换行符转换提示 | 无害；`core.autocrlf` 见 9.4 |

### 9.3 HTTPS ↔ SSH 互切

```bash
git remote -v                                            # 先看现在的地址
git remote set-url origin git@github.com:you/repo.git    # HTTPS → SSH
git remote set-url origin https://github.com/you/repo.git # SSH → HTTPS
```

### 9.4 Windows 换行符（autocrlf）

Windows 的 CRLF（`\r\n`）与 Linux 的 LF（`\n`）差异是跨平台仓库的头号噪音源。`core.autocrlf` 三种取值：

- `true`：检出时 LF→CRLF，提交时 CRLF→LF（Windows 传统默认，仓库内永远 LF）；
- `input`：检出不动，提交时 CRLF→LF（**推荐**，Git Bash 用户）；
- `false`：完全不转换（纯 Windows 团队可用）。

团队统一方案：仓库里放一个 `.gitattributes` 文件（`* text=auto`），让规则跟仓库走，与每人本机配置解耦。

---

## 10. 安全：绝对不要提交的东西

1. **密钥与凭据**（`.env`、API key、私钥、数据库密码）——**提交即公开**（私有仓库也有员工/协作者可见，且 GitHub 会扫描已知密钥格式）。一旦推出去：
   - **第一步永远是作废轮换该密钥**（改密码、吊销 token），因为历史里已经拿不干净了；
   - 清理历史用 `git filter-repo` 或 [BFG Repo-Cleaner](https://github.com/rtyley/bfg-repo-cleaner)（改写历史后需 force push，协作仓库要先全员知会）；
   - 预防：`.env` 进 .gitignore，`.env.example` 提交模板；CI 里加 secret 扫描。
2. **大文件/二进制**（视频、数据集、模型权重）——撑爆仓库且 Git 对二进制增量存储效率极差，用 LFS 或对象存储。
3. **他人隐私**：真实姓名、身份证、内网地址——commit 是永久的、可被 fork 的。
4. **明确边界**：`--force` 只允许强推自己的分支；`git push --mirror` 会把本地所有引用（含你不知道的分支覆盖）推上去，对共享仓库是灾难，永远别对 GitHub 仓库用。

---

## 11. 学习路径与资源

建议练习顺序（配合沙箱，见附录）：

1. 第 2~3 章：本地沙箱里把 add/commit/分支/冲突解决各做一遍（不碰网络，零风险）；
2. 第 5 章：配好一种认证（推荐先 HTTPS+GCM 跑通，再补 SSH）；
3. 第 6.1 场景 A：把本工作区的 `Agent.md` 所在项目或任意小项目推上 GitHub，完整走一遍；
4. 第 4 章：回到沙箱用第二个 clone 模拟同事，体验 non-fast-forward 与 pull --rebase 急救；
5. 第 8 章：在 GitHub 上给自己的仓库开 PR、自评、squash 合并，走完整闭环；
6. 进阶：`git reflog`（所有操作后悔药）、bisect（二分定位 bug 提交）、Git LFS、submodule。

权威资源：

- **Pro Git 中文版**（官方书，免费）：<https://git-scm.com/book/zh/v2>
- 官方速查：<https://education.github.com/git-cheat-sheet-education.pdf>
- 交互式练习：<https://learngitbranching.js.org/?locale=zh_CN>（分支可视化练手神器）
- GitHub 官方 Skills 实战课：<https://skills.github.com>
- 救火手册：<https://ohshitgit.com/zh>（「完蛋了怎么办」系列）

---

## 12. 附录：目录文件与沙箱使用说明

| 文件 | 说明 |
|------|------|
| `README.md` | 本文档 |
| `git_sandbox.sh` | 一键搭建「本地远程」练习沙箱（见下） |
| `reference/git-state-and-refs.html` | 五组交互图：四区状态、引用指针、推送被拒、merge/rebase、reset/revert |
| `assets/` | 参考页共享样式、图表切换与放大组件 |

### 沙箱是什么

`git_sandbox.sh` 在本目录下创建 `sandbox/`：

```
sandbox/
├── remote.git     # 裸仓库：扮演"GitHub"（只有仓库数据，无工作区——真实远程的本质）
└── work/          # 你的工作仓库：已初始化 user/2 个提交/挂好 origin
```

它让你**不注册不联网**就能练习推拉的全套动作（push/pull/fetch/跟踪分支/non-fast-forward/冲突解决），仓库互相独立，玩坏了 `--reset` 一键重置。

> 提示：`--reset` 时如果报"目录被占用"，说明某个终端/编辑器的工作目录还停在 `sandbox/` 里（Windows 不允许删除进程的当前目录）——关掉对应窗口再重跑即可。练习时在沙箱里开着的终端，练完顺手 `cd` 出去是个好习惯。

### 练习剧本（按顺序敲）

```bash
bash git_sandbox.sh            # 搭建（已存在则提示；--reset 强制重建）
cd sandbox/work
git push -u origin main        # ① 第一次推送
git switch -c feature/demo && echo change >> notes.md && git add . && git commit -m "wip"
git push -u origin feature/demo && git switch main   # ② 推分支再切回

# ③ 模拟"同事"：另开一个 clone（同事的仓库）。同事新建自己的文件，避免与你稍后的改动撞在同一处
cd .. && git clone remote.git alice && cd alice
echo "同事的修改" > colleague.md && git add colleague.md && git commit -m "feat: 同事加了 colleague.md"
git push
# 注：如果两边改了【同一文件的同一处】，pull --rebase 会停下来等你解决冲突——
# 按第 3.3 节三步走（编辑文件 → git add → git rebase --continue），这正是练习冲突的机会。

# ④ 回到 work 拉：你会亲身撞上 non-fast-forward，然后自救
cd ../work && echo "我的修改" >> notes.md && git add . && git commit -m "feat: 我也改了 notes"
git push                       # → ! [rejected] ... (fetch first)
git pull --rebase              # → 自救成功
git push                       # → OK
```

### 一页速查（最常用的 15 条）

```bash
git status                         # 现状
git add . && git commit -m "msg"   # 存档
git log --oneline --graph --all    # 历史
git switch -c 分支名                # 新建并切换分支
git merge 分支名                    # 合并
git remote -v                      # 看远程
git remote add origin <url>        # 挂远程
git clone <url>                    # 克隆
git pull --rebase                  # 拉取并对齐
git push                           # 推送
git push -u origin main            # 首推并建立跟踪
git push --force-with-lease        # 安全强推
git restore --staged 文件           # 取消暂存
git revert <hash>                  # 撤销已推送提交
git stash / git stash pop          # 口袋暂存
```
