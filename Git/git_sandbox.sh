#!/usr/bin/env bash
# git_sandbox.sh —— 一键搭建「本地远程」Git 练习沙箱
# =====================================================
#
# 原理：git init --bare 创建一个"裸仓库"——只有仓库数据、没有工作区，
# 这正是 GitHub 服务端存储的本质。把它的路径配成 origin，你就拥有了一个
# 不联网、不注册、随便折腾的"私人 GitHub"。
#
# 用法：
#   bash git_sandbox.sh          # 搭建（已存在则退出并提示）
#   bash git_sandbox.sh --reset  # 删除旧沙箱并重建（沙箱内容会丢失）
#
# 搭建完成后的练习剧本见 README.md 第 12 章（附录）。

set -euo pipefail
# 语法糖说明：set -euo pipefail 是 shell 的"安全模式"组合拳——
#   -e 任何命令失败立即退出；-u 使用未定义变量报错；pipefail 管道中任一环
#   失败就算整体失败。等价于逐条写：
#       set -e
#       set -u
#       set -o pipefail

cd "$(dirname "$0")"
# 语法糖说明：$(dirname "$0") 取本脚本所在目录——让脚本无论从哪里调用，
# 都在自己的目录下工作（沙箱固定落在 Git/ 目录下，而不是调用者的当前目录）。

SANDBOX=sandbox

# ── --reset：先尽力删除旧沙箱 ───────────────────────────────
if [ "${1:-}" = "--reset" ]; then
    # ${1:-} 语法糖：取第一个命令行参数，未传时用空串兜底（避免 set -u 报错）。
    echo "重置：删除旧沙箱..."
    # Windows 上若某终端/编辑器正停在 sandbox 里（目录是它的 CWD），rm 会删不掉
    # 那个目录本身——宽容处理：能删多少删多少，只要目录已空就继续重建。
    rm -rf "$SANDBOX" 2>/dev/null || true
    if [ -d "$SANDBOX/work" ] && [ -n "$(ls -A "$SANDBOX/work" 2>/dev/null)" ]; then
        echo "错误：$SANDBOX/work 仍被其他程序占用且非空，无法重置。"
        echo "请关闭停在 sandbox 目录里的终端/编辑器窗口后重跑本脚本。"
        exit 1
    fi
fi

# ── 已存在检查：只认"完整的沙箱"（裸仓库 + 工作仓库都在）────────
if [ -d "$SANDBOX/remote.git" ] && [ -d "$SANDBOX/work/.git" ]; then
    echo "沙箱已存在（$PWD/$SANDBOX）。"
    echo "  重新搭建：bash git_sandbox.sh --reset"
    echo "  直接练习：cd $SANDBOX/work 后按 README.md 第 12 章剧本操作"
    exit 0
elif [ -d "$SANDBOX" ] && [ -n "$(ls -A "$SANDBOX" 2>/dev/null)" ]; then
    echo "沙箱目录存在但内容不完整（可能是上次搭建/删除中断），用 --reset 重建："
    echo "  bash git_sandbox.sh --reset"
    exit 1
fi
# 目录不存在或为空 → 直接往下搭建

echo "搭建沙箱..."
mkdir -p "$SANDBOX"

# ── 1. 创建裸仓库（扮演远程 GitHub）─────────────────────────
git init --bare -b main "$SANDBOX/remote.git" > /dev/null
# --bare = 裸仓库（无工作区，只有 .git 内容铺在根目录）；-b main 指定默认分支名。

# ── 2. 创建工作仓库（扮演你电脑上的项目）────────────────────
git init -b main "$SANDBOX/work" > /dev/null
cd "$SANDBOX/work"

# 用 local 配置写入演示身份：沙箱 commit 与你的全局身份无关，随便玩。
# （不加 --global 的 config 只作用于当前仓库——这也顺带演示了配置的三个层级：
#   system < global(--global) < local(默认)）
git config user.name "sandbox-demo"
git config user.email "demo@sandbox.local"

# 关闭换行符转换，避免全局 core.autocrlf=true 的用户首跑时刷 CRLF 警告
# （换行符话题见 README.md 9.4）
git config core.autocrlf false

# 初始内容：两个提交，模拟"项目已有历史"
printf '# 沙箱练习仓库\n\nREADME.md 第 12 章剧本从这里开始。\n' > README.md
printf '练习笔记。\n' > notes.md
git add .
git commit -m "feat: 初始提交" > /dev/null
echo "notes.md 第二行（由搭建脚本写入）" >> notes.md
git add .
git commit -m "docs: 补充练习笔记" > /dev/null

# ── 3. 挂上"远程"，但不推送——第一次 push 留给你亲手完成 ──
git remote add origin ../remote.git

# 相对路径 ../remote.git 完全合法：Git 的远程地址可以是本地路径/文件路径，
# 当然也可以是 https://github.com/... 或 git@github.com:...。

echo
echo "=============================================="
echo " 沙箱就绪：$PWD"
echo "   remote.git   → 扮演 GitHub 的裸仓库"
echo "   work/        → 你的工作仓库（origin 已挂好）"
echo
echo " 第一个练习："
echo "   cd $SANDBOX/work"
echo "   git push -u origin main      # 你的第一次推送"
echo
echo " 完整练习剧本：README.md 第 12 章"
echo "=============================================="
