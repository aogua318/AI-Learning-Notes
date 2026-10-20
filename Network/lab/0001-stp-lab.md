# 实验 0001：STP 选举与收敛（eNSP）

> 配套课程：`lessons/0001-stp-mechanism.html`。环境搭建见 `lab/README.md`。

## 拓扑

两台 **S5700**，两条铜线互连成环：

```
SW-A                          SW-B
GE0/0/1 ──────────────────── GE0/0/1
GE0/0/2 ──────────────────── GE0/0/2
```

搭建步骤：拖两台 S5700 进拓扑区 → 用 Copper 线把 SW-A 的 GE0/0/1 连 SW-B 的 GE0/0/1、SW-A 的 GE0/0/2 连 SW-B 的 GE0/0/2 → 启动两台设备。

## 实验一：观察默认选举

1. 启动后等约 30 秒（经典 STP 收敛时间），双击 SW-A 登录 CLI：

```
display stp brief
```

2. **预期输出**（关键行，格式随版本略有差异）：

```
MSTID    Port                        Role  STP State     Protection
0        GigabitEthernet0/0/1        DESI  FORWARDING    NONE
0        GigabitEthernet0/0/2        ALTE  DISCARDING    NONE
```

```
display stp
```

看 `CIST Root` 一行：哪台是 root（Bridge ID 最小的那台）。

3. **对照课程第 6 节**：两台设备时，root 的所有端口都是 DESI（指定端口）；非 root 选一个开销最小的端口当 ROOT（根端口），另一个被阻塞（ALTE/DISCARDING）。两台直连时两个端口开销相同，平手比 Bridge ID——输的那个端口被阻塞。

## 实验二：改优先级，换 root

1. 在**当前非 root** 的那台（比如 SW-B）上执行：

```
system-view
stp priority 4096
```

2. 回到 SW-A 再 `display stp brief`：**root 换成了 SW-B**，两台的端口角色全部重排（SW-A 原来转发的端口现在被阻塞）。

3. **观察点**：这就是「比小不比大」——4096 压过默认的 32768。把 SW-A 也改成 `stp priority 0` 再观察，root 又换回来。

## 实验三：对比 STP 与 RSTP 的收敛速度

1. 两台都切经典模式，先测基线：

```
system-view
stp mode stp
```

2. 拔掉转发中的那条线（右键链路 → 删除，或右键设备接口 → 关闭），计时到 `display stp brief` 显示新拓扑稳定：经典 STP 约 **30–50 秒**。

3. 恢复链路，两台都切 RSTP：

```
stp mode rstp
```

4. 再拔线计时：**秒级**恢复。这就是 Alternate 端口 + proposal/agreement 握手的价值。

> 注：VRP 较新版本默认 MSTP 模式，快速收敛行为与 RSTP 一致。若 `display stp brief` 显示协议 disabled，先 `stp enable`。

## 实验四：抓 BPDU

1. 右键 SW-A–SW-B 的任意一条链路 → **开始抓包**，Wireshark 自动打开。
2. 过滤框输入 `stp`，应看到**每 2 秒一个**的 BPDU。
3. 对照课程第 2 节的字段表，在 Wireshark 详情面板里找：
   - **Root ID**：当前认定的 root（实验一/二里它随选举结果变化）
   - **Root Path Cost**：发送者到 root 的开销
   - **Bridge ID**：发送这个 BPDU 的交换机
4. 拔线瞬间重抓，能看到 **TCN BPDU**（拓扑变化通知）——STP 的「报警」。

## 排障提示

| 现象 | 可能原因 |
|---|---|
| `display stp brief` 全是 FORWARDING | 设备没起 STP（检查 `stp enable` / `stp mode`），或两条链路没真正成环 |
| 两个端口都阻塞 | 拓扑里两条链路都断了，或设备没启动完就看了 |
| 抓包按钮点了没反应 | Wireshark 安装时没勾 Npcap，或 Wireshark 没装 |
| 命令报错 | 版本差异：用 `?` 看当前版本的语法，以设备帮助为准 |
