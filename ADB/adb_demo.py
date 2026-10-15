#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
adb_demo.py —— 用 Python subprocess 封装 ADB 的最小自动化示例（零第三方依赖）
=============================================================================

文档（README.md）里所有命令都是给"人"敲的；做自动化时更常见的是让程序去调。
这个示例演示封装的核心模式，读懂它你就能自己写装机脚本、UI 冒烟脚本、批量截图工具。

前置条件：
    1. 本机已安装 adb 并加入 PATH（命令行敲 adb version 能出版本号）；
    2. 设备已连接且完成授权（adb devices 显示 device 状态）。

用法：
    python adb_demo.py                # 演示：设备列表 → 前台应用 → 截屏 → 系统信息
    python adb_demo.py app.apk        # 额外执行一次安装演示
"""

import subprocess
import sys

# 支持多设备：环境变量 ANDROID_SERIAL 或命令行第 2 个参数指定目标序列号
SERIAL = sys.argv[2] if len(sys.argv) > 2 else None


def run(*args, binary=False):
    """执行一条 adb 子命令，返回 stdout 内容。

    语法糖：*args 是可变位置参数，函数内 args 是元组，等价于
        def run(args_list): ... cmd = ["adb"] + list(args_list)
    但调用时可以自然地写 run("install", "-r", "app.apk")，不用手工组列表。

    语法糖：binary=False 是关键字参数默认值，等价于
        def run(args, b):  # 调用方永远要传 run(cmd, b=False)
    Python 用默认值表达"可选开关"，是比位置布尔参数更可读的写法。
    """
    cmd = ["adb", *args]  # 列表解包：等价于 ["adb"] + list(args)
    if SERIAL:
        cmd = ["adb", "-s", SERIAL, *args]  # 多设备时插入 -s 序列号

    # capture_output=True：同时捕获 stdout/stderr，等价于
    #   subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # 注意这里【没有】text=True：截屏等场景要拿原始字节，文本/二进制由调用方决定怎么解码
    result = subprocess.run(cmd, capture_output=True)

    if binary:
        return result.stdout  # 字节流原样返回（截图等二进制内容）

    # 语法糖：decode("utf-8", errors="replace") 解码字节为字符串；
    # errors="replace" 表示遇到非法字节不抛异常，替换成 � —— adb 输出里混有
    # 设备端日志时比直接崩掉友好得多。
    text = result.stdout.decode("utf-8", errors="replace")
    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError("adb %s 失败(exit %s): %s" % (" ".join(args), result.returncode, err))
    return text


def shell(cmd):
    """执行 adb shell <命令>，返回设备端输出文本。"""
    return run("shell", cmd)


def list_devices():
    """解析 adb devices 输出，返回 [(序列号, 状态), ...]。

    语法糖：列表推导式 [f(x) for x in xs if 条件]，等价于
        out = []
        for line in lines:
            if 条件:
                out.append(f(line))
    """
    lines = run("devices").strip().splitlines()[1:]  # 第 0 行是表头 "List of devices attached"
    devices = []
    for line in lines:
        if line.strip():  # 跳过空行
            parts = line.split()
            devices.append((parts[0], parts[1]))
    return devices


def current_focus():
    """当前前台应用，格式如 ActivityRecord{... u0 com.example/.MainActivity ...}。"""
    out = shell("dumpsys window | grep -E 'mCurrentFocus'")
    # 语法糖：str.strip() 去两端空白；如果没有匹配行，grep 返回空且 exit 1，
    # shell() 会抛 RuntimeError，这里直接让调用方在 try 里兜底处理。
    return out.strip()


def screenshot(path="screen.png"):
    """截屏并保存到本机。关键点：必须走 exec-out 拿原始字节（README 4.2 节）。"""
    png = run("exec-out", "screencap", "-p", binary=True)
    # 语法糖：with open(...) as f 是上下文管理器，等价于
    #   f = open(path, "wb"); try: ... finally: f.close()
    # "wb" = write + binary，写 PNG 必须用二进制模式（文本模式会做换行转换，损坏图片）。
    with open(path, "wb") as f:
        f.write(png)
    return path


def install(apk):
    """安装 APK，返回是否成功与输出（失败时 install 本身 exit 1，信息在 stdout）。"""
    out = run("install", "-r", "-t", apk)
    return "Success" in out, out.strip()


def tap(x, y):
    """模拟点击。参数拼进 shell 命令字符串——坐标是数字，无注入风险；
    若拼接用户可控文本（如 input text），务必先校验/转义。"""
    return shell("input tap %d %d" % (x, y))


def main():
    print("=" * 60)
    print("ADB 自动化最小示例")
    print("=" * 60)

    # 1) 设备检查：没设备就友好退出，而不是抛出难懂的错误栈
    try:
        devices = list_devices()
    except FileNotFoundError:
        print("未检测到 adb。请先安装 platform-tools 并加入 PATH。")
        sys.exit(1)

    ready = [d for d in devices if d[1] == "device"]
    print("\n[1] 设备列表:", devices or "（无）")
    if not ready:
        print("没有状态为 device 的设备（unauthorized=去手机上点允许；offline=拔插重连）。")
        sys.exit(1)

    # 2) 前台应用
    print("\n[2] 当前前台窗口:")
    try:
        print("   ", current_focus())
    except RuntimeError as exc:
        # 语法糖：as exc 把异常对象绑定到变量，等价于 except RuntimeError, exc:（Python2 写法，已废弃）
        print("    获取失败:", exc)

    # 3) 截屏
    print("\n[3] 截屏:")
    print("    已保存 ->", screenshot("adb_demo_screen.png"))

    # 4) 系统信息
    print("\n[4] 系统信息:")
    print("    型号:", shell("getprop ro.product.model").strip())
    print("    Android:", shell("getprop ro.build.version.release").strip())
    print("    电量:", end=" ")  # end=" " 让 print 不换行，等价于 sys.stdout.write("电量: ")
    print(shell("dumpsys battery | grep level").strip())

    # 5) 可选安装演示
    if len(sys.argv) > 1 and sys.argv[1].endswith(".apk"):
        print("\n[5] 安装 %s:" % sys.argv[1])
        ok, out = install(sys.argv[1])
        print("   ", out)

    print("\n完成。把 tap/swipe/input 组合起来，就能写出你自己的自动化脚本了。")


if __name__ == "__main__":
    main()
