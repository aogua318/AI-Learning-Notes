# Network — 计算机网络机制原理与排障 Resources

> 标注 ✅ 的条目为实际访问核实过内容；其余为高可信来源，使用前建议抽查最新版本。

## Knowledge

- [IEEE 802.1D-2004（STP 标准）](https://standards.ieee.org/standard/802_1D-2004.html) ✅
  BPDU 字段定义、root 选举规则、端口状态机的权威出处。第一课的全部机制都能在这里找到原文。用途：遇到「为什么这样选」的问题，回标准查措辞。
- [IEEE 802.1 工作组](https://www.ieee802.org/1/) ✅
  802.1w（RSTP）、802.1Q（VLAN）等修订的官方入口。用途：RSTP 快速收敛、VLAN tag 等后续课程的标准出处。
- [华为企业业务支持（文档库）](https://support.huawei.com/enterprise/zh/index.html)
  搜索「S5700 STP 配置」可定位 VRP 命令参考与 `display stp` 输出的官方文档。站点为 JS 渲染，无法直接抓取，需用站内搜索。用途：VRP 命令语法的最终依据（设备自带 `?` 帮助同样权威）。
- [Wireshark 用户指南](https://www.wireshark.org/docs/wsug_html_chunked/) ✅
  抓包过滤、流分析、BPDU/ARP 等协议的解码视图。用途：每课的抓包实验配套；eNSP 右键链路「开始抓包」直接调起。
- [eNSP（华为官方模拟器）](https://support.huawei.com/enterprise/zh/index.html)
  华为企业业务支持 → 工具 → eNSP，需华为账号（免费）。S 系列交换机与 AR 路由器以本地进程运行，2–4 台设备轻量。用途：全部课程的实验环境。

## Wisdom (Communities)

- [华为企业互动社区](https://forum.huawei.com/enterprise/zh)
  华为设备一线工程师与厂商支持聚集地，VRP 命令与排障案例的高信号来源。用途：eNSP 实验卡住、命令行为与文档不符时先搜这里。
- [Network Engineering Stack Exchange](https://networkengineering.stackexchange.com/)
  英文网络工程问答站，机制级问题（协议行为、选路逻辑）回答质量高。用途：机制细节的交叉验证。
- [r/networking](https://www.reddit.com/r/networking/)
  资讯与讨论流量大，信噪比一般。用途：跟踪行业动态，不作机制依据。

## Gaps

- 中文「机制级」网络教材稀缺：经典《TCP/IP 详解 卷1》机制扎实但版本偏老（缺 RSTP 等新协议）；主流中文资料偏命令手册，缺「为什么」。本课程的 HTML 课要承担中文机制补齐的责任。
- eNSP 各版本支持的设备与 VRP 版本碎片化，实验手册中的命令以设备自带 `?` 帮助为准。

## 社区偏好

- 用户未表示排斥社区；以上按需取用，不强制。
