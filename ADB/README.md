# ADB 常用命令学习文档

> **ADB（Android Debug Bridge，Android 调试桥）** 是 Android 官方提供的通用命令行工具，让你通过 USB 或网络与 Android 设备（手机、平板、电视、车机、模拟器）通信：安装调试应用、传输文件、执行 shell 命令、查看日志、模拟输入……它是 Android 开发、自动化测试、逆向分析和玩机折腾的基础设施。
>
> 本文以 **platform-tools 37.x**（2026 年）为基准，覆盖：架构原理 → 连接管理 → 全部常用命令族（install/pm/push/shell/am/input/logcat/dumpsys/settings/fastboot…）→ 场景组合实战 → 常见错误速查。
>
> 配套文件：[adb_demo.py](#18-附录目录文件与快速参考) —— 用 Python 子进程封装 ADB 的最小自动化示例。

---

## 目录

0. [ADB 是什么：架构与原理](#0-adb-是什么架构与原理)
1. [环境准备与首次连接](#1-环境准备与首次连接)
2. [设备与连接管理](#2-设备与连接管理)
3. [应用管理：安装、卸载与包控制](#3-应用管理安装卸载与包控制)
4. [文件传输与设备文件系统](#4-文件传输与设备文件系统)
5. [adb shell 与系统信息](#5-adb-shell-与系统信息)
6. [应用操控：am 命令](#6-应用操控am-命令)
7. [输入模拟：input 与按键事件](#7-输入模拟input-与按键事件)
8. [截屏、录屏与显示设置](#8-截屏录屏与显示设置)
9. [日志：logcat 详解](#9-日志logcat-详解)
10. [端口转发与网络](#10-端口转发与网络)
11. [系统设置：settings 命令](#11-系统设置settings-命令)
12. [刷机与底层：fastboot 与 sideload](#12-刷机与底层fastboot-与-sideload)
13. [性能调试与整机诊断](#13-性能调试与整机诊断)
14. [场景 Cookbook：组合命令实战](#14-场景-cookbook组合命令实战)
15. [安全与注意事项](#15-安全与注意事项)
16. [常见错误速查表](#16-常见错误速查表)
17. [学习路径与资源](#17-学习路径与资源)
18. [附录：目录文件与快速参考](#18-附录目录文件与快速参考)

---

## 0. ADB 是什么：架构与原理

### 0.1 三段式架构

ADB 不是「一根线直连设备」那么简单，它是典型的 **客户端-服务端-守护进程** 三段结构：

```
┌──────────────┐  adb 命令   ┌────────────────┐  USB / TCP  ┌─────────────────────┐
│  adb 客户端   │ ─────────> │   adb server    │ ──────────> │  设备端 adbd 守护进程 │
│ （你敲的命令） │ <───────── │ （本机 5037 端口）│ <────────── │ （设备上 root/shell） │
└──────────────┘   本机回环   └────────────────┘   真实链路   └─────────────────────┘
```

| 组件 | 位置 | 职责 |
|------|------|------|
| **adb client** | 每次敲命令临时启动 | 解析你的命令，转发给 server；找不到 server 就先拉起一个 |
| **adb server** | 本机后台进程，监听 `localhost:5037` | 管理所有设备连接、多路复用：N 个客户端命令 ↔ M 台设备都经它中转 |
| **adbd** | 每台设备/模拟器上的守护进程 | 在设备端执行命令、传文件，权限是 shell 用户（部分操作需 root） |

三个由此产生的关键认知：

1. **`adb kill-server` 为什么万能**：连接状态错乱、server 版本不匹配（装了新版 platform-tools 但旧 server 还活着）时，杀掉 server 重启就能重置一大半问题。
2. **server 只监听本机回环**：本机任何进程都能和它通信（这是本机自动化的便利，也是多用户系统上的安全隐患，见第 15 章）。
3. **设备端 adbd 的权限是「shell 用户」**：比普通应用高（能读写很多系统设置、访问 `/data/local/tmp`），比 root 低（动不了别的应用私有数据和系统分区）。`adb root` 只在工程版系统/模拟器上有效。

### 0.2 传输通道：USB 与无线

- **USB**：插线即用，走 USB bulk 传输，速度最快（push/pull 大文件必选）。
- **无线（经典法）**：先用 USB 执行 `adb tcpip 5555` 让 adbd 改听 TCP 5555 端口，之后拔线 `adb connect 设备IP:5555`。`adb usb` 切回 USB 模式。
- **无线（Android 11+ 配对法）**：开发者选项 → 无线调试 → 使用配对码配对，得到 `IP:配对端口` + 6 位配对码，然后 `adb pair IP:配对端口 配对码`，再 `adb connect IP:调试端口`。全程不需要 USB 线，底层用 mDNS 发现 + 一次性配对码建立 TLS。

### 0.3 ADB 与 fastboot 的区别

| | adb | fastboot |
|------|-----|----------|
| 工作状态 | Android 正常运行（也可在 recovery/sideload） | Bootloader（引导加载程序）模式 |
| 能力 | 完整系统内操作：shell、装应用、日志…… | 刷分区镜像、解锁、擦除——系统还没启动，只有分区级操作 |
| 进入方式 | 开机即可 | `adb reboot bootloader`，或开机时按住特定按键组合 |
| 工具来源 | 同属 platform-tools，但 fastboot 是独立二进制 | |

两者的衔接：`adb reboot bootloader` 进 fastboot → 刷完 `fastboot reboot` 回系统。

### 0.4 获取方式

ADB 包含在 **Android platform-tools** 里，随版本独立更新（与 Android Studio 版本无关）：

- Android Studio / SDK Manager：SDK Platforms → SDK Tools → Android SDK Platform-Tools；
- 独立下载：<https://developer.android.com/tools/releases/platform-tools>（解压后把目录加入 PATH）；
- 包管理器：`winget install Google.PlatformTools` / `brew install --cask android-platform-tools` / `apt install adb`。

验证：`adb version`。本文示例假定 adb 已在 PATH 中。

---

## 1. 环境准备与首次连接

### 1.1 设备端开启调试

1. 设置 → 关于手机 → 连续点击「版本号」7 次，解锁开发者选项；
2. 开发者选项 → 打开 **USB 调试**；
3. （可选但推荐）同时打开「USB 调试（安全设置）」——模拟点击/截屏类操作在部分品牌（小米等）需要它。

### 1.2 首次连接的授权机制

第一次插线执行 `adb devices` 时，**手机上会弹出 RSA 指纹确认框**（勾选「一律允许」可免重复确认）。这是 ADB 的安全设计：防止别人拿根线就操作你手机。

- 点「允许」后，指纹存进设备的 `/data/misc/adb/adb_keys`，你电脑的公钥在 `~/.android/adbkey(.pub)`;
- 误点了拒绝 / 想重来：开发者选项 → **撤销 USB 调试授权**，拔插重来；
- 部分电脑生成的 RSA 密钥算法太老（如 1024 位）会导致新设备拒绝授权，删除 `~/.android/adbkey*` 让 adb 重新生成即可。

### 1.3 验证连接

```bash
adb version          # 确认工具版本
adb devices          # 必须先敲一次：它负责拉起 server、发现设备
adb devices -l       # 长格式：能看到型号、设备名、transport_id
```

`adb devices` 输出的四种状态：

| 状态 | 含义 | 处理 |
|------|------|------|
| `device` | 已授权、可正常使用 | —— |
| `unauthorized` | 已连接但**手机上还没点允许**（或授权被撤销） | 看手机屏幕弹窗 |
| `offline` | 连接异常（线/驱动/server 状态错乱） | 拔插、换线换口、`adb kill-server` |
| （无输出行） | 没检测到设备 | 检查 USB 模式选「文件传输」而非「仅充电」、装 OEM 驱动、开 USB 调试 |

模拟器同理（`emulator-5554` 是它的 serial）。特殊状态：设备处于 recovery 时显示 `recovery`，bootloader 下 adb 看不见它，要用 `fastboot devices`；OTA 界面下显示 `sideload`。

---

## 2. 设备与连接管理

### 2.1 多设备选择：-s / -d / -e / -t

接了多台设备（或一手机一模拟器）时，绝大多数命令都必须指定目标，否则报 `more than one device/emulator`：

```bash
adb devices -l                  # 先看 serial 和 transport_id
adb -s R3CN123ABC shell ...     # 按序列号指定（最常用）
adb -d shell ...                # 唯一的 USB 真机（multiple 时报错）
adb -e shell ...                # 唯一的模拟器
adb -t 2 shell ...              # 按 transport_id 指定（devices -l 输出里有）
```

环境变量 `ANDROID_SERIAL` 可以设默认目标，免去每条命令敲 `-s`。

### 2.2 server 管理

```bash
adb kill-server     # 杀掉本机 adb server（5037 端口的进程）
adb start-server    # 显式启动
adb mdns check      # 检查 mDNS 发现服务是否可用（无线调试配对用）
adb mdns services   # 列出 mDNS 发现的可连接设备
```

### 2.3 无线连接

```bash
# ── 经典法（Android 11 以下，或你有 USB 线时最方便）──
adb tcpip 5555                  # ① 插线执行：adbd 重启为 TCP 模式
adb connect 192.168.1.20:5555   # ② 拔线，连接（5555 可省略）
adb disconnect 192.168.1.20     # 断开（不带参数 = 全部）

# ── 配对法（Android 11+，无需 USB 线）──
# 手机：开发者选项 → 无线调试 → 配对码 → 显示 IP:配对端口 和 6 位码
adb pair 192.168.1.20:43210 873214   # ① 配对（一次性）
adb connect 192.168.1.20:34567       # ② 连接（端口是"无线调试"主页面上的那个，≠ 配对端口）

adb usb                          # 切回 USB 模式
```

注意：无线模式下adb 流量在局域网内明文/加密取决于机制（配对法是 TLS），**公共 Wi-Fi 下别开无线调试**；手机重启后 TCP 模式失效，要重新 `tcpip 5555`。

### 2.4 重启与特殊模式

```bash
adb reboot                # 普通重启
adb reboot bootloader     # 进 bootloader（fastboot 模式）
adb reboot recovery       # 进 recovery（工程模式）
adb reboot sideload       # 进 recovery 并自动进入 sideload 等待
adb root                  # 让 adbd 以 root 重启（仅工程版/模拟器，量产机会报 adbd cannot run as root）
adb unroot                # 切回非 root
adb remount               # 把 /system 等分区改为可写（需 root 或 userdebug，系统目录改动的入口）
```

---

## 3. 应用管理：安装、卸载与包控制

### 3.1 安装：install

```bash
adb install app.apk
adb install -r app.apk            # 保留数据覆盖安装（reinstall）
adb install -r -t app.apk         # -t 允许 test-only 包（IDE 直接 Run 出来的常是这种）
adb install -g app.apk            # 安装时授予全部 runtime 权限
adb install -d app.apk            # 允许"降级"安装（新版本号 < 已装的）
adb install --abi arm64-v8a app.apk  # 多 ABI 包指定架构
adb install-multiple base.apk split_config.arm64_v8a.apk split_config.zh.apk
                                  # App Bundle 拆分 APK 场景：必须一起装
```

常用 flag 速查：`-r` 覆盖重装 / `-t` 测试包 / `-g` 授权 / `-d` 降级 / `-l` 加锁安装 / `--user N` 指定用户。

安装失败的 `Failure [INSTALL_FAILED_XXX]` 见第 16 章速查表。

### 3.2 卸载：uninstall 与 bloatware 清理

```bash
adb uninstall com.example.app          # 完整卸载（数据一起删）
adb uninstall -k com.example.app       # 保留数据和缓存目录（少用，残留会导致重装异常）

# ── 预装应用清理（无需 root，但只对当前用户生效、系统分区文件还在）──
adb shell pm uninstall -k --user 0 com.xxx.bloatware   # 对 user 0 卸载，保留数据
adb shell pm disable-user --user 0 com.xxx.bloatware   # 更保守：仅停用（可随时 enable）
adb shell pm enable com.xxx.bloatware                  # 恢复停用的应用
adb shell cmd package install-existing com.xxx.bloatware  # 恢复 --user 0 卸载的应用
```

> 动手删预装前先搜一下包名——**删错系统组件可能导致系统异常甚至无法开机**（比如 Play 服务、系统输入法）。`disable-user` 是最安全的试错方式。

### 3.3 包查询与控制：pm 命令族

`pm`（package manager）在 shell 里执行，现代版本它就是 `cmd package` 的别名：

```bash
adb shell pm list packages                 # 全部包名
adb shell pm list packages -3              # 仅第三方应用
adb shell pm list packages -s              # 仅系统应用
adb shell pm list packages -d              # 已停用的
adb shell pm list packages -e              # 已启用的
adb shell pm list packages | grep camera   # 过滤（配合本机或设备端 grep）
adb shell pm path com.example.app          # 查 APK 安装路径（取出 APK：见 4.3）
adb shell pm clear com.example.app         # 清除应用全部数据（等于「清除存储」，重置测试环境利器）
adb shell pm grant com.example.app android.permission.CAMERA   # 授予运行时权限
adb shell pm revoke com.example.app android.permission.CAMERA  # 撤销
adb shell dumpsys package com.example.app  # 完整包信息（版本、权限、签名、Activity 等全在里面）
```

---

## 4. 文件传输与设备文件系统

### 4.1 push / pull

```bash
adb push 本地文件 /sdcard/DCIM/            # 本机 → 设备（目录要已存在）
adb push 本地目录 /sdcard/                  # 目录递归传输
adb pull /sdcard/DCIM/IMG_001.jpg ./       # 设备 → 本机（./ 可省略，默认当前目录）
adb pull /sdcard/Download ./backup         # 拉整个目录
```

路径约定：`/sdcard` 是 `/storage/emulated/0` 的符号链接（共享存储，无 root 也能读写）；`/data/local/tmp` 是 shell 用户的「自家目录」，各种临时文件、待装 APK 的标准中转站；应用私有目录 `/data/data/包名/` 普通 shell **读不了**，见 4.3 的 run-as。

`push --sync` 只传内容有变化的文件，适合反复同步代码/资源。

### 4.2 二进制安全的输出：exec-out vs shell

一个经典大坑：`adb shell` 输出经过设备端 pty，**`\n` 会被改写成 `\r\n`**。文本无所谓，二进制直接损坏。所以：

```bash
adb exec-out screencap -p > screen.png   # ✅ exec-out：不经 pty，字节流原样返回
adb shell screencap -p > screen.png      # ⚠️ 老版本 adb 会得到损坏的 PNG（\n→\r\n）
```

**任何「拉二进制内容」的场景（截图、数据库、图片）一律用 `adb exec-out`。** 现代 adb 对 `shell` 做了兼容处理，但养成习惯更稳。

### 4.3 run-as：以应用身份访问私有数据

只对 **debuggable（debug 签名）的应用**有效，release 包不行：

```bash
adb shell run-as com.example.app ls databases/                    # 看应用私有目录
adb shell run-as com.example.app cat databases/app.db > app.db    # 文本/小文件
adb exec-out run-as com.example.app cat databases/app.db > app.db # ✅ 二进制安全拉库
adb shell run-as com.example.app cp databases/app.db /data/local/tmp/   # 中转再 pull
```

### 4.4 常用 shell 文件操作

设备端 shell 是 toybox 工具箱，常用命令都有：`ls -l`、`cd`、`cat`、`cp`、`mv`、`rm`、`mkdir`、`chmod`、`df -h`（看各分区容量）、`du -sh *`（看目录大小）。

```bash
adb shell df -h /data              # 存储空间排查
adb shell du -sh /sdcard/Android/* # 谁占了空间
```

> ⚠️ `rm -rf` 在设备上没有回收站。路径写错（尤其是变量为空时 `rm -rf /$EMPTY/...`）后果自负，删除系统分区内容前先 `ls` 确认。

---

## 5. adb shell 与系统信息

### 5.1 两种用法

```bash
adb shell                      # ① 交互式：进入设备端 shell，exit 退出
adb shell getprop ro.product.model   # ② 单次执行：执行完直接回结果
```

### 5.2 引号与管道的两层解析（必懂）

`adb shell 后面的整串` 会经历**两次解析**：本机 shell 一次（引号、管道、变量），剩下部分拼成字符串发给设备端 shell 再解析一次。理解这一点，90% 的「命令怎么写引号」问题都能推导出来：

```bash
adb shell dumpsys window | grep focus        # 管道在【本机】执行：grep 过滤 adb 的输出（效果通常一样，但语义不同）
adb shell "dumpsys window | grep focus"      # 管道在【设备】执行：引号让整串成为一条设备端命令
adb shell input text 'hello%sworld'          # 本机单引号保住 %s；设备端 input 把 %s 渲染成空格
adb shell am start -a android.intent.action.VIEW -d "https://x.com/?a=1&b=2"
                                             # bash/cmd 里 & 是特殊字符，URL 必须整体加引号
adb shell "dumpsys package com.example | grep versionName"   # 设备端过滤，省流量
```

### 5.3 系统属性：getprop / setprop

```bash
adb shell getprop ro.product.model       # 设备型号
adb shell getprop ro.build.version.release   # Android 版本（如 15）
adb shell getprop ro.build.version.sdk       # API Level（如 35）
adb shell getprop | grep -i android      # 全量属性过滤
adb shell setprop debug.x.y 1            # 写属性（仅 debug.* 等可写项，多数 ro.* 只读）
```

常用属性速查：

| 属性 | 含义 |
|------|------|
| `ro.product.model` / `ro.product.brand` | 型号 / 品牌 |
| `ro.build.version.release` / `.sdk` | Android 版本 / API Level |
| `ro.build.version.incremental` | 精确构建号（比对刷机包用） |
| `ro.build.type` | user / userdebug / eng（决定能否 adb root） |
| `ro.serialno` | 序列号 |
| `ro.hardware` / `ro.board.platform` | 芯片平台 |

### 5.4 dumpsys：系统服务的全家桶

`dumpsys 服务名 [参数]` 打印某系统服务的内部状态，是排障第一利器。常用：

```bash
adb shell dumpsys battery                # 电量、充电状态（细到电压温度、充电方式 USB/AC/Wireless）
adb shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'   # 当前前台窗口/应用
adb shell dumpsys activity activities | grep -i resumed  # 当前栈顶 Activity
adb shell dumpsys activity services com.example.app      # 该应用在跑哪些 Service
adb shell dumpsys meminfo com.example.app                # 应用内存详情（PSS 分解）
adb shell dumpsys cpuinfo                                # CPU 占用排行
adb shell dumpsys wifi                                   # Wi-Fi 状态
adb shell dumpsys notification --noredir                  # 当前所有通知
adb shell dumpsys package com.example.app                # 包信息
adb shell dumpsys -l                                     # 列出全部可用服务
```

进程排查：`adb shell ps -A | grep com.example`（`-A` 全部进程，toybox 语法）、`adb shell pidof -s com.example.app`（单行 PID，喂给 logcat --pid 很好用）。

---

## 6. 应用操控：am 命令

`am`（activity manager）从命令行操控应用生命周期和 Intent——自动化测试的「遥控器」。

### 6.1 启动：am start

```bash
# 按组件名精确启动（包名/.Activity 相对写法）
adb shell am start -n com.example.app/.MainActivity
adb shell am start -n com.android.settings/.Settings        # 打开系统设置

# 按 Intent 启动（隐式跳转）
adb shell am start -a android.intent.action.VIEW -d "https://example.com"       # 浏览器打开网页
adb shell am start -a android.intent.action.DIAL -d "tel:10086"                 # 拨号盘
adb shell am start -a android.intent.action.SENDTO -d "sms:10086"               # 短信
adb shell am start -a android.intent.action.VIEW -d "geo:39.9,116.4?z=15"       # 地图坐标
adb shell am start -a android.intent.action.VIEW -d "market://details?id=com.example.app"  # 应用商店详情页

# 附加参数与 flag
adb shell am start -n com.example.app/.MainActivity --es msg "hi" --ei count 3 --ez flag true
adb shell am start -n com.example.app/.MainActivity --activity-clear-top        # 复用已有实例
```

`--es/--ei/--ez/--ed` = 附加 String/Int/Bool/Double 额外参数；找组件名的办法：`adb shell dumpsys package com.example.app | grep -A1 "Activity"` 或反编译 AndroidManifest。

### 6.2 停止 / 杀进程 / 广播 / 服务

```bash
adb shell am force-stop com.example.app     # 彻底停止（冷启动前的标准动作）
adb shell am kill com.example.app           # 温和杀后台（无后台则无效）
adb shell am broadcast -a com.example.app.MY_ACTION   # 发广播（测试自定义 BroadcastReceiver）
adb shell am start-foreground-service -n com.example.app/.MyService   # 启动前台服务
adb shell am startservice -n com.example.app/.MyService               # 启动服务（老 API）
```

### 6.3 monkey：随机压力测试

```bash
adb shell monkey -p com.example.app -v 500             # 对该应用随机注入 500 个事件
adb shell monkey -p com.example.app --throttle 100 -s 42 -v 500
# --throttle 事件间隔(ms)；-s 固定随机种子（bug 可复现）
adb shell monkey --kill-process-after-error -p com.example.app 1000
```

monkey 疯狂点遍全 UI，专测 ANR 和崩溃；出问题后 `-s 种子号` 能复现同一路径。

---

## 7. 输入模拟：input 与按键事件

自动化点击的核心命令。坐标系为屏幕物理像素，原点左上角（可用 `wm size` 查分辨率）。

```bash
adb shell input tap 500 1200                        # 单击
adb shell input swipe 500 1500 500 500 300          # 滑动：起(x1,y1)→终(x2,y2)，时长 ms
adb shell input swipe 500 1200 500 1200 800         # 长按 = 同点 swipe + 长时长
adb shell input draganddrop 500 1200 500 500 500    # 拖拽（放手才生效的 UI）
adb shell input text "hello%sworld"                 # 文本（%s=空格；不支持中文！）
adb shell input keyevent 4                          # 按键事件（见下表）
adb shell input motionevent DOWN 500 1200           # 原始事件流（新版支持，做复杂手势）
```

**常用 keyevent 码表**（`adb shell input keyevent KEYCODE_BACK` 也可以直接写常量名）：

| 码 | 常量 / 含义 | 码 | 常量 / 含义 |
|----|------------|----|------------|
| 3 | HOME | 4 | BACK |
| 26 | POWER（亮/灭屏） | 82 | MENU |
| 24 / 25 | 音量+ / 音量- | 164 | 静音 |
| 66 | ENTER | 67 | DEL（退格） |
| 61 / 62 | TAB / 空格 | 112 | FORWARD_DEL（删除键） |
| 223 / 224 | SLEEP / WAKEUP | 187 | APP_SWITCH（最近任务） |
| 126~131 | 媒体：播放暂停/停止/下一首/上一首… | 19~23 | 方向键与中心键 |

规律：字母 A~Z = 29~54（`29 + (字母-'A')`），数字 0~9 = 7~16，完整表见 `KEYCODE_*` 官方文档。

**中文输入**：`input text` 走的按键注入通道不支持中文。常用方案是装一个 [ADBKeyBoard](https://github.com/senzhk/ADBKeyBoard) 输入法应用，然后 `am broadcast -a ADB_INPUT_TEXT --es msg '中文内容'`。

---

## 8. 截屏、录屏与显示设置

### 8.1 截屏

```bash
# 方式一：直接落到本机（exec-out 保证二进制不损坏，推荐）
adb exec-out screencap -p > screen.png

# 方式二：先存设备再拉
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png
```

### 8.2 录屏

```bash
adb shell screenrecord --time-limit 30 /sdcard/demo.mp4   # Ctrl+C 或超时自动保存
adb pull /sdcard/demo.mp4
```

参数：`--time-limit`（默认/最长 180 秒）、`--bit-rate N`（码率，卡顿拖影就调高）、`--size WxH`（指定输出分辨率）、`--bugreport`（叠加时间戳等信息）。限制：无声音、单段最长 3 分钟、高分辨率长录会压缩；要长时间/带声音录制，用 **scrcpy --record file.mp4**（镜像+录制一体，强烈推荐装一个）。

### 8.3 显示参数：wm

```bash
adb shell wm size                 # 查看物理/覆盖分辨率
adb shell wm size 1080x2400       # 强制改分辨率（老年模式/兼容测试）
adb shell wm size reset           # 恢复
adb shell wm density              # 查看 DPI
adb shell wm density 480          # 改显示密度（大字体大图标）
adb shell wm density reset
adb shell wm overscan 0,0,0,100   # 四边留黑边（老电视盒子适配）
```

> ⚠️ `wm density` 设过小/过大的值可能让界面错乱到无法操作——好在 ADB 通道还在，连上执行 `wm density reset` 即可救回。

---

## 9. 日志：logcat 详解

### 9.1 基本结构与过滤

每条日志 = `日期 时间 PID TID 级别 TAG: 消息`。日志按 **缓冲区** 分流（main 主 / system 系统 / crash 崩溃 / events 事件 / radio 通话），按 **级别** 分档：V(Verbose) < D(Debug) < I(Info) < W(Warn) < E(Error) < F(Fatal)。

```bash
adb logcat                                  # 实时流（Ctrl+C 停止）
adb logcat -v time                          # 精简时间格式
adb logcat *:E                              # 只看 Error 及以上
adb logcat MyApp:D *:S                      # 只看 MyApp 这个 tag 的 Debug+（*:S 静默其余全部）
adb logcat -s MyApp                         # 上一条的简写（等价 MyApp:V *:S）
adb logcat -s MyApp ActivityManager         # 多个 tag
adb logcat --pid=$(adb shell pidof -s com.example.app)   # 只看某进程（pidof -s 单值）
adb logcat -b crash -d                      # 崩溃缓冲区一次性导出（查闪退第一步！）
adb logcat -b events | head                 # 事件缓冲：am_proc_start 等系统事件流
```

### 9.2 导出与清空

```bash
adb logcat -d > full.log          # -d：导出当前缓冲并退出（非实时）
adb logcat -d -v threadtime > log.txt   # threadtime 格式信息最全（线程ID+精确时间）
adb logcat -c                     # 清空缓冲区（复现问题前先清，好定位）
adb logcat -t "2026-09-25 10:00:00.000"   # 从某时间点开始
adb logcat -f /sdcard/run.log     # 设备端落盘（适配长时间挂后台抓日志）
```

> 高级日志请认准 `-v threadtime`；`grep -E "FATAL|AndroidRuntime"` 一把抓崩溃栈；ANR 痕迹在 `logcat -b system` 里搜 `ANR in`，完整现场用 `bugreport`（第 13 章）。

---

## 10. 端口转发与网络

### 10.1 forward：本机端口 → 设备端口

```bash
adb forward tcp:8080 tcp:8080     # 访问 localhost:8080 即到达设备的 8080（设备上跑着 web 服务时）
adb forward --list                # 查看现有转发
adb forward --remove tcp:8080     # 删除指定
adb forward --remove-all
```

### 10.2 reverse：设备端口 → 本机端口（开发者最爱）

```bash
adb reverse tcp:3000 tcp:3000     # 设备上的 App 访问 localhost:3000 → 你电脑的 3000
```

典型场景：手机 App 连接你电脑上的开发服务器（Vite/webpack/本地 API）——**不用查电脑局域网 IP，不用同一路由器，USB 线直达**。调试 WebView 直接开 Chrome 的 `chrome://inspect`（自动依赖 adb，无需手动 forward）。

### 10.3 设备端网络控制

```bash
adb shell svc wifi enable / disable    # 开关 Wi-Fi
adb shell svc data enable / disable    # 开关移动数据
adb shell ping -c 3 example.com        # 从设备发起连通性测试
adb shell ip route                     # 路由表（看当前默认网络）
adb shell netstat -tlnp 2>/dev/null | head    # 监听端口（部分版本无 -p）
```

---

## 11. 系统设置：settings 命令

`settings` 直接读写系统设置数据库，三个命名空间对应设置项的存储位置：

| 命名空间 | 存放内容举例 |
|----------|-------------|
| `system` | 亮度、字体缩放、声音、时间格式等用户偏好 |
| `secure` | 位置模式、默认输入法、android_id、已授权服务 |
| `global` | 全局行为：飞行模式、动画缩放、休眠策略、ADB 开关 |

```bash
adb shell settings get secure android_id                  # 设备 android_id
adb shell settings get global window_animation_scale      # 查询
adb shell settings put global window_animation_scale 0    # 关窗口动画
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0   # 三动画全关 = 自动化提速利器
adb shell settings put global stay_on_while_plugged_in 7  # 插电不休眠（1=AC 2=USB 4=无线，7=全部）
adb shell settings put system screen_brightness 120       # 亮度 0~255（新版另有 screen_brightness_float 0~1）
adb shell settings put system font_scale 1.2              # 字体缩放
adb shell settings list system | grep -i screen           # 整表导出+过滤
adb shell settings list secure | head -30
adb shell settings list global
adb shell settings delete global my_test_key              # 删自建的键
```

> adb shell 用户持有 `WRITE_SECURE_SETTINGS` 权限，所以以上命令无需 root——这也是很多「免 root 玩机」的原理。改坏了一般 `put` 回默认值即可；不确定默认值就先 `get` 存下来。

---

## 12. 刷机与底层：fastboot 与 sideload

### 12.1 进入与查看

```bash
adb reboot bootloader        # 手机重启进 fastboot 模式（adb 就此失效）
fastboot devices             # fastboot 自己的设备列表（没输出 = Windows 缺 fastboot 驱动）
fastboot reboot              # 回到系统
fastboot reboot recovery     # 直进 recovery（新版支持）
```

### 12.2 常见刷写操作

```bash
fastboot flash boot boot.img           # 刷 boot 分区（Magisk 修补后通常刷这个）
fastboot flash recovery recovery.img
fastboot flash system system.img
fastboot flash dtbo dtbo.img           # A/B 设备：fastboot flash boot_a ... 或带 slot 后缀
fastboot reboot-bootloader             # 刷完留在 fastboot（刷多分区时连续操作）
fastboot getvar current-slot           # 查询当前 slot（A/B 分区设备）
fastboot oem device-info               # 查看解锁状态（部分厂商）
```

### 12.3 解锁与警告

```bash
fastboot flashing unlock       # 官方解锁流程（需先在开发者选项打开 OEM 解锁）
fastboot flashing lock         # 重新锁定
```

> ⚠️ **三重警告**：解锁会**清空全部数据**；部分品牌/运营商永久锁定或解绑保修；解锁后 bank/Pay 类应用可能拒用。刷错镜像可能导致无法开机——刷之前确认镜像与机型/分区完全匹配，并学会进 recovery 的按键组合救砖。

### 12.4 sideload：卡刷 OTA

```bash
adb reboot sideload                 # 重启进入 sideload 模式（等价于 recovery 菜单里选 Apply update from ADB）
adb sideload ota_update.zip         # 推送并安装整个 OTA 包
```

适用于官方 OTA 手动升级、magisk/uninstall 等特殊 zip。

---

## 13. 性能调试与整机诊断

```bash
adb bugreport bug.zip               # 整机诊断大礼包：全量日志+dumpsys+内存/CPU 快照（Android 7+ 出 zip）
adb shell dumpsys meminfo -a        # 全系统内存概况
adb shell dumpsys meminfo com.example.app   # 单应用 PSS 分解（内存泄漏排查）
adb shell dumpsys cpuinfo           # CPU 占用快照
adb shell dumpsys gfxinfo com.example.app           # 渲染性能总览
adb shell dumpsys gfxinfo com.example.app framestats # 最近 120 帧的逐帧时间（卡顿分析）
adb shell dumpsys battery set level 20    # 伪造电量（测试低电量逻辑；reset 恢复）
adb shell dumpsys battery unplug          # 伪造"未充电"状态（reset 恢复）
adb shell top -m 10                 # 内存前 10 的进程
```

- **bugreport** 是给官方 issue tracker / 深度排障用的，解包后 `FS/data/anr/`、`dumpsys.txt` 都在；
- 卡顿分析进阶用 **Perfetto**（`adb shell perfetto` 或直接用 [ui.perfetto.dev](https://ui.perfetto.dev) 抓 trace）；命令行 profiling 用设备自带的 **simpleperf**（`adb shell simpleperf list`）；
- 内存泄漏三板斧：`dumpsys meminfo` 反复观察 PSS 趋势 → Android Studio Memory Profiler 抓 heap dump → MAT/Profiler 看 Bitmap/Activity 残留。

---

## 14. 场景 Cookbook：组合命令实战

以下命令按场景组装，可直接抄。多设备时记得加 `-s 序列号`。

**① 装包 → 清场 → 冷启动一条龙**
```bash
adb install -r -t app.apk && adb shell pm clear com.example.app \
  && adb shell am start -n com.example.app/.MainActivity
```

**② 每隔 2 秒截一张屏（自动化记录 UI 变化）**
```bash
for i in $(seq 1 10); do adb exec-out screencap -p > shot_$i.png; sleep 2; done
```

**③ 无 UI 自动化冒烟：启动 → 等 3 秒 → 点登录 → 输账号 → 截图验证**
```bash
adb shell am start -n com.example.app/.LoginActivity && sleep 3 \
  && adb shell input tap 540 1800 && sleep 1 \
  && adb shell input text "user%sname" \
  && adb shell input keyevent 66 && sleep 2 \
  && adb exec-out screencap -p > after_login.png
```

**④ 抓崩溃/ANR 现场**
```bash
adb logcat -c && echo "现在去复现问题..." && adb logcat -b crash -d > crash.log
adb logcat -d | grep -E "FATAL|ANR in" -A 20 >> crash.log
```

**⑤ 提取某应用 APK 发给别人**
```bash
apk=$(adb shell pm path com.example.app | sed 's/package://;s/\r//') && adb pull "$apk"
```

**⑥ 把手机变成"无人值守测试机"**
```bash
adb shell settings put global stay_on_while_plugged_in 7    # 插电永不锁屏休眠
adb shell settings put global window_animation_scale 0      # 关动画提速
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
```

**⑦ 冻结应用实验（比卸载安全，可随时复活）**
```bash
adb shell pm disable-user --user 0 com.xxx.adsdk && adb shell pm enable com.xxx.adsdk
```

**⑧ 拉取 debug 包的数据库/SharedPreferences**
```bash
adb exec-out run-as com.example.app cat databases/user.db > user.db
adb exec-out run-as com.example.app cat shared_prefs/user.xml > user.xml
```

**⑨ 无线调试迁移（腾出 USB 口给别的设备）**
```bash
adb tcpip 5555 && sleep 2 && adb connect 192.168.1.20:5555 && adb devices
```

**⑩ 手机访问电脑上的开发服务器（reverse，无需同网段）**
```bash
adb reverse tcp:8080 tcp:8080
# 然后手机 App 里请求 http://localhost:8080 即是你电脑的服务
```

**⑪ 批量并行操作多台设备**
```bash
for s in $(adb devices | awk 'NR>1 && $2=="device" {print $1}'); do
  adb -s $s shell am force-stop com.example.app
  adb -s $s install -r app.apk
done
```

**⑫ 语音/媒体控制小玩具**
```bash
adb shell input keyevent 126      # 播放
adb shell input keyevent 25 3     # 音量减（可重复次数参数）
adb shell am start -a android.intent.action.DIAL -d "tel:10086"
```

---

## 15. 安全与注意事项

1. **授权即信任**：点过「一律允许」的电脑能以 shell 权限做上面**所有事**（读通知、装应用、改设置、截屏录屏）。不用的电脑撤销授权，借出去手机先「撤销 USB 调试授权」。
2. **公共 USB 口/来路不明的数据线**：手机插进别人的电脑 = 对方拿到 shell。机场/商场充电口同理（juice jacking）。日常只充电建议选「仅充电」模式，或考虑数据线隔离器。
3. **无线调试是局域网内的后门**：配对后任何能连上同一 Wi-Fi 的设备理论上都可能尝试连接。用完即关（开发者选项关掉无线调试 / `adb disconnect`）。公共 Wi-Fi 绝不开启。
4. **adb server 无鉴权**：它只监听本机 5037，本机任何进程（包括恶意软件）都能直接操作你的设备。多人共用/不受信的本机环境要留意。
5. **危险命令清单**（都无需 root，误伤不留回收站）：
   - `pm uninstall --user 0` 系统关键组件（Play 服务、SystemUI、输入法）→ 系统异常；
   - `wm density`/`wm size` 极端值 → 界面错乱（ADB 还在就能 reset 救回）；
   - `settings put global adb_enabled 0` → 自断 adb（USB 重插或重启可恢复，无线模式下会失联）；
   - `rm -rf` 于 `/system`、`/data`（需 root）；`fastboot flash` 错误镜像 / `fastboot flashing unlock`（清数据+失保）；
   - `recovery` 里 wipe data/factory reset → 全清。
6. **公司设备（MDM 管理）**：很多策略禁止 USB 调试或会审计/上报，别在打工设备上折腾。

---

## 16. 常见错误速查表

### 16.1 连接类

| 报错/现象 | 原因 | 处理 |
|-----------|------|------|
| `unauthorized` | 手机上没点允许 / 授权被撤销 | 看手机弹窗；开发者选项撤销授权重来 |
| `offline` | server 状态错乱、线松、驱动抽风 | `adb kill-server` 重连；换线换口 |
| `no devices/emulators found` | USB 调试没开 / 驱动缺 / 选了仅充电 | 开调试、选文件传输模式、装 OEM 驱动 |
| `more than one device/emulator` | 多设备未指定 | 加 `-s serial`（或 `-d`/`-e`/`-t`） |
| `adb server version doesn't match this client` | 电脑上有多个不同版本 adb（常见：模拟器自带 vs platform-tools） | `adb kill-server`；统一只留一份并加 PATH |
| `adb connect` 连不上 | 端口错 / 不同网段 / 手机休眠断开了 | 确认"无线调试"端口；同 Wi-Fi；手机亮屏重试 |
| `device still authorizing` | 授权弹窗还没处理 | 手机亮屏确认 |
| fastboot 没有设备 | Windows 缺驱动 | 装 OEM fastboot 驱动 / 通用 WinUSB 驱动 |
| `device '(null)' not found` 等怪错 | server 缓存了失效设备 | `adb kill-server` 重来 |

### 16.2 安装类（`adb install` 的 Failure）

| 错误码 | 含义 | 处理 |
|--------|------|------|
| `INSTALL_FAILED_ALREADY_EXISTS` | 同包名已存在且签名/路径冲突 | `adb uninstall` 后重装，或 `-r` |
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | 已装不同签名版本（如官方版 vs 自编译 debug 包） | 先 `adb uninstall`（会清数据） |
| `INSTALL_FAILED_VERSION_DOWNGRADE` | 要装的版本号更低 | `-d` 允许降级，或先卸载 |
| `INSTALL_FAILED_TEST_ONLY` | test-only 包未获允许 | 加 `-t` |
| `INSTALL_FAILED_NO_MATCHING_ABIS` | APK 不含本机 ABI | 换含 arm64-v8a 的包 / `--abi` 指定 |
| `INSTALL_PARSE_FAILED_NO_CERTIFICATES` | APK 未签名 | 用 debug keystore 签名后再装 |
| `INSTALL_FAILED_INVALID_APK` | APK 损坏 / split 装漏 | 重新导出；用 `install-multiple` 装 bundle 拆分包 |
| `INSTALL_FAILED_INSUFFICIENT_STORAGE` | 空间不足 | 清 `/data` 空间（`df -h /data`） |
| `INSTALL_FAILED_CONFLICTING_PROVIDER` | ContentProvider authority 撞名 | 改你应用里的 authority |

### 16.3 shell 行为类

| 现象 | 原因 | 处理 |
|------|------|------|
| `input text` 打不出中文 | 注入通道只支持 ASCII | ADBKeyBoard 方案（第 7 章） |
| `screencap -p > x.png` 打不开 | shell 模式 \r\n 污染 | 改用 `adb exec-out` |
| `grep`/`pidof` command not found | 老安卓 toybox 精简 | 在本机过滤：`adb shell ... | grep` |
| URL/参数含 `&` 命令被截断 | 本机 shell 把 `&` 当后台符 | 整体加引号 |
| 带空格参数没传对 | 两层解析少包了一层引号 | 外层引号包住，内层再引号：`adb shell "cmd 'a b'"` |
| 截屏黑屏（部分银行/视频 App） | 应用开了 FLAG_SECURE 防截屏 | 无解，属安全特性 |
| `adbd cannot run as root` | 量产 user 版系统 | 属正常；需要 root 走解锁+Magisk |

---

## 17. 学习路径与资源

建议练习顺序：

1. 第 1、2 章：连上真机，把 `devices`/`-s`/无线连接玩熟；
2. 第 3~5 章：装卸应用、push/pull、getprop/dumpsys 摸底你的手机；
3. 第 6~8 章：am 启动跳转、input 写一个「自动签到」小脚本（配合配套的 adb_demo.py 改造）；
4. 第 9 章：`logcat -b crash -d` 抓一次真崩溃并读懂栈；
5. 第 14 章 Cookbook：挑 3 个场景跑通，再组合出你自己的；
6. 进阶：Perfetto trace 分析、fastboot 刷机流程（先在备用机/模拟器练）。

权威资源：

- 官方 ADB 文档：<https://developer.android.com/tools/adb>（速查页 <https://developer.android.com/tools/adb/shellshell> 收录 shell 命令）
- platform-tools 发布页：<https://developer.android.com/tools/releases/platform-tools>
- ADB 源码（理解原理的终极材料）：<https://android.googlesource.com/platform/packages/modules/adb/>
- scrcpy（投屏录屏神器，与 adb 天然互补）：<https://github.com/Genymobile/scrcpy>
- ADBKeyBoard（中文输入方案）：<https://github.com/senzhk/ADBKeyBoard>

---

## 18. 附录：目录文件与快速参考

### 18.1 本目录文件

| 文件 | 说明 |
|------|------|
| `README.md` | 本文档 |
| `adb_demo.py` | 用 Python `subprocess` 封装 ADB 的最小自动化示例（零第三方依赖） |

### 18.2 一页速查（最常用的 20 条）

```bash
adb devices -l                        # 设备列表
adb -s <serial> shell                 # 进入指定设备 shell
adb install -r -t app.apk             # 覆盖装包
adb uninstall com.example.app         # 卸载
adb shell pm list packages -3         # 第三方包列表
adb shell pm clear com.example.app    # 清应用数据
adb push local /sdcard/               # 推文件
adb pull /sdcard/file .               # 拉文件
adb shell am start -n pkg/.Activity   # 启动 Activity
adb shell am force-stop pkg           # 杀应用
adb shell input tap x y               # 点击
adb shell input swipe x1 y1 x2 y2 ms  # 滑动/长按
adb shell input keyevent 4            # BACK 键
adb exec-out screencap -p > s.png     # 截屏到本机
adb shell screenrecord /sdcard/v.mp4  # 录屏
adb logcat -v threadtime              # 实时日志
adb logcat -b crash -d                # 导出崩溃日志
adb shell dumpsys battery             # 电量状态
adb shell getprop ro.build.version.release   # 系统版本
adb tcpip 5555 && adb connect IP      # 转无线调试
```
