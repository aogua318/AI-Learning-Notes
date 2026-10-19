# 从零手搓：Windows 上的 Rust 环境搭建（rustup + rustlings）

> 目标：从一台裸机 Windows，到能跑第一课的课后任务——rustlings 装好、`move_semantics` 六个练习开练。全程约 30 分钟，大部分时间是下载和编译的等待。
>
> 适用对象：有 C 基础、Python 应用层经验、第一次装 Rust 工具链的人。每一步都带**预期输出**，对不上就是出错，直接查第 9 节排错表。

---

## 目录

1. [要装的三样东西](#1-要装的三样东西)
2. [第一步：安装 rustup](#2-第一步安装-rustup)
3. [第二步：验收 rustc 与 cargo](#3-第二步验收-rustc-与-cargo)
4. [第三步：第一次编译验收（第一堵墙在这）](#4-第三步第一次编译验收第一堵墙在这)
5. [第四步：安装 rustlings](#5-第四步安装-rustlings)
6. [第五步：开练 move_semantics](#6-第五步开练-move_semantics)
7. [rustlings 目录放哪](#7-rustlings-目录放哪)
8. [顺手一步：固件编译目标（可选）](#8-顺手一步固件编译目标可选)
9. [排错表](#9-排错表)
10. [验收清单](#10-验收清单)

---

## 1. 要装的三样东西

| 装什么 | 是什么 | 干什么用 |
|---|---|---|
| rustup | Rust 官方工具链管理器 | 以后所有 Rust 组件（编译器、交叉编译目标）都通过它装，自己不带编译器 |
| Rust 工具链（stable） | rustup 下载的 rustc + cargo | rustc 是编译器；cargo 是包管理器和构建工具 |
| rustlings | rust-lang 官方练习集 | 第一课到第四课的课后练习都在里面跑，编译错误即反馈 |

注意分工：**rustup 是管家，rustc 才是编译器**。装 rustup 时它会顺手把 stable 工具链装好，你不用单独找编译器下载。

## 2. 第一步：安装 rustup

1. 打开 <https://rustup.rs>，下载 **rustup-init.exe**（选 x86_64 版本，2026 年的电脑都是 64 位）。
2. 双击运行，屏幕会问安装选项。**全部选默认**——出现 `1) Proceed with installation (default)` 就按回车；`Modify PATH variable? (y/N)` 输 `y`。
3. 等它下载安装（几分钟）。看到 `Rust is installed now. Great!` 字样即成功。
4. **关键动作：关掉当前终端，重新开一个**。PATH 环境变量只在**新开的**终端里生效——这是新手第一课，不关窗口后面全部命令都报"不是内部或外部命令"。

备用路径：如果你用 winget，`winget install Rustlang.Rustup` 是等价的，装完同样要开新终端。

## 3. 第二步：验收 rustc 与 cargo

新终端里依次执行：

```bash
rustc --version
cargo --version
```

预期输出长这样（**版本号和时间戳会变，看格式别看数字**）：

```
rustc 1.xx.0 (xxxxxx 2026-xx-xx)
cargo 1.xx.0 (xxxxxx 2026-xx-xx)
```

两条都打印出版本号 = 编译器就位。版本号不用纠结：1 开头、两位数主版本，都是正常的 stable Rust，我们的项目不锁特定版本。

## 4. 第三步：第一次编译验收（第一堵墙在这）

光看版本号不能证明能编译，跑一个" hello world "试试——这一步会在你第一次真正编译时暴露 Windows 特有的坑：

```bash
cargo new hello_rust
cd hello_rust
cargo run
```

预期输出：

```
   Compiling hello_rust v0.1.0 (C:\...\hello_rust)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.5s
     Running `target\debug\hello_rust.exe`
Hello, world!
```

看到 `Hello, world!` = 工具链完整可用，直接跳第五步。

**如果报这个错**：

```
error: linker `link.exe` not found
  = note: program not found
```

原因：rustup 在 Windows 上默认安装 MSVC 版本的工具链，它需要一个微软的链接器 `link.exe`，而你的系统没装 Visual Studio Build Tools。两条解法，选一条：

**解法 A（快，推荐给本项目）**——换用自带链接器的 GNU 工具链，两条命令，不下载几个 GB 的 VS：

```bash
rustup toolchain install stable-x86_64-pc-windows-gnu
rustup default stable-x86_64-pc-windows-gnu
```

然后重跑 `cargo run`。我们的项目（rustlings、WoL 工具、Pico 固件）全是纯 Rust 或嵌入式目标，GNU 工具链完全够用，且不依赖 VS。

**解法 B（标准路）**——安装 VS Build Tools： winget 搜 `Microsoft.VisualStudio.2022.BuildTools`，安装时勾选"使用 C++ 的桌面开发"工作负载。要下载几个 GB，但这是大多数 Windows Rust 开发者的默认环境。以后如果遇到某个 crate 只支持 MSVC，再走这条路。

## 5. 第四步：安装 rustlings

```bash
cargo install --locked rustlings
```

这条命令会**从源码编译 rustlings 再安装**，等两三分钟正常，不是卡死。看到 `Installed package \`rustlings v0.x.0\`` 即完成（版本号以实际为准）。

> 备用路径：嫌编译慢，可以去 rustlings 的 GitHub Releases 页面下载 Windows 二进制，解压后把 `rustlings.exe` 所在目录加进 PATH。效果等价。

然后初始化练习目录（在任意你想放的位置执行，放哪见第 7 节）：

```bash
rustlings init
cd rustlings
rustlings
```

`rustlings init` 会拉取全部练习文件到当前目录的 `rustlings\` 文件夹；最后一条 `rustlings` 启动练习环境（新版 rustlings 的启动命令就是 `rustlings` 本身，旧版教程里的 `rustlings watch` 已废弃）。

## 6. 第五步：开练 move_semantics

启动后按提示操作，核心循环是三步：

1. **看当前练习**：启动界面会列出练习清单，`move_semantics` 系列共 6 个练习，是第一课的指定作业；
2. **改代码**：练习文件在 `rustlings\exercises\move_semantics\` 下，用任何文本编辑器打开，把 `// TODO` 处补成正确代码；
3. **保存即验收**：保存文件，rustlings 自动重新编译，通过就显示成功并自动进入下一题；编译错误会把错误信息打出来——**这些错误信息就是你的老师，逐条读**。

卡住了：练习文件顶部通常有提示注释，也可以先猜再看错误信息。界面内可用的命令（提示、重跑当前题等）以启动后按 `h` 或执行 `rustlings --help` 显示的为准——细节版本间有调整，我不在文档里锁死按键，以你看到的帮助为准。

**六个练习的名字规律**：`move_semantics1` 到 `move_semantics6`，难度递进，分别练习：移动一个值、移动后填坑、函数传参的移动、返回值的移动等。全部通过后，第一课的课后任务就完成了，回来找我。

## 7. rustlings 目录放哪

**建议放在仓库外**，比如 `C:\Users\admin\rustlings`。原因：练习目录里有 `target\` 构建缓存（动辄几百 MB），还有上百个练习文件，全都不适合进 git。

两个选择：

- **放仓库外**（推荐）：`cd C:\Users\admin`，然后 `rustlings init`。干净，仓库零污染。
- **放仓库内**：放在 `Rust-Driver\rustlings\`，并且必须把 `Rust-Driver/rustlings/` 加进根 `.gitignore`，否则 `git add .` 会把构建缓存一起提交。

## 8. 顺手一步：固件编译目标（可选）

执行下面这一条，提前装好摇杆固件的交叉编译目标：

```bash
rustup target add thumbv6m-none-eabi
```

`thumbv6m-none-eabi` 是 Pico 的 RP2040 芯片（Cortex-M0+ 核心）对应的编译目标。现在装不装都不影响前四周的 Rust 语言学习，但装好它，等固件课开始时能少一个排错环节。预期输出 `info: downloading component 'rust-std' for 'thumbv6m-none-eabi'`。

## 9. 排错表

| 症状 | 原因 | 解法 |
|---|---|---|
| `rustc` 不是内部或外部命令 | 装完没开新终端，PATH 未更新 | 关掉终端重开；还不行就重启资源管理器或注销重登 |
| `link.exe` not found | MSVC 工具链缺链接器 | 第 4 节解法 A 或 B |
| `cargo install rustlings` 卡在编译 | 正常，在从源码编译 | 等两三分钟；或走 Releases 二进制 |
| `rustlings` 启动后找不到练习 | 不在 rustlings 目录里执行 | 先 `cd rustlings` |
| `rustlings init` 拉取练习失败 | 网络问题 | 重试；或去 GitHub Releases 下载练习包 |
| 终端中文乱码 | 老版本 Windows 控制台编码问题 | 用 Windows Terminal，或执行 `chcp 65001` 切 UTF-8 |

## 10. 验收清单

全部打勾 = 环境就绪，第一课的课后任务可以正式开跑：

- [ ] `rustc --version` 和 `cargo --version` 都输出版本号
- [ ] `cargo run` 在 hello_rust 项目里打印出 `Hello, world!`
- [ ] `cargo install --locked rustlings` 安装成功
- [ ] `rustlings init` + `cd rustlings` + `rustlings` 能启动练习环境
- [ ] （可选）`rustup target add thumbv6m-none-eabi` 完成

---

> 环境是学习的跑道，不是学习本身——但它铺不平，后面每一步都会崴脚。按清单逐项打勾，任何一项卡住，把**报错原文**贴给我，我帮你定位。
