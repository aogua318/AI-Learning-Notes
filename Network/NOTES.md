# NOTES.md — Network 教学工作区

## 用户偏好与背景（继承自 Rust-Driver / Git 工作区，2026-10-20 确认）

- **身份**：网络设备运维工程师（华为设备为主），用户方，公司设备完全黑盒，无测试机无 root。学习成果的检验场只能是自有环境。
- **基础**（2026-10-20 六题诊断定位）：会配 VLAN/trunk/STP 模式；ARP 网关模型、TCP 三次握手（含"为什么不是两次"）理解正确；分层排障有直觉。机制缺口：STP 内部过程（知道"阻塞端口"不知道"怎么决定阻塞哪个"）、OSPF 邻居条件记不全（缺子网掩码、MTU、Router-ID 唯一性）。**课程从机制缺口切入，不从零教起。**
- **时间**：每周 5–10 小时，与 Rust-Driver 主线并行拆分。
- **语言规则**：英语水平差。教学材料里凡代码关键字和特有名词之外的英文（规则原文、命令输出、工具界面文案等），保留英文并附中文对照。
- **文档口味**：机制先行（先讲"为什么"）、重视可带走的沉淀物；HTML 互动课（15–20 分钟/节，一个知识点 + 页面内互动练习）。
- **决策风格**：接受推荐、不纠结。

## 已确认的关键决策（2026-10-20）

1. 核心目标 = **机制原理 + 排障**（三选一中用户选定）：从"会配"到"懂为什么"，直接提升日常排障判断力；顺带服务 Rust-Driver 第二阶段"USB 网络检测盒"（ARP 扫描等知识前置）。
2. 实验环境 = **eNSP**（华为官方免费模拟器）+ Wireshark 抓包（eNSP 右键链路直接调起）。用户电脑能带简单拓扑（2–4 设备），10+ 设备的大拓扑不做或拆小。曾考虑自购二手华为真机（S5700 + AR1220），因电脑跑不动大型模拟且真机有噪音/刷机风险，最终改 eNSP——模拟器还能故意制造故障复现排障场景。
3. 与 Rust-Driver 的关系 = **并行支线**：每周时间拆分；网络课顺带服务检测盒项目。
4. 已删除 `Rust-Driver/demo/wol/src/main.rs.bak`（练习前的旧版 main.rs，练习已完成，备份无用）。

## 组件库状态

- `assets/lesson.css`：从 Rust-Driver 复制 + 追加 Network 课程样式（tab 切换、net-* 拓扑图语义类、术语表样式）。
- `assets/zoomable-figure.js`：从 Rust-Driver 复制（滚轮以光标为中心缩放、拖拽平移）。
- `assets/quiz.js`、`assets/diagram-tabs.js`：从 Git 复制。
- 图约定：`figure` 同时带 `figure-zoom` 与 `data-zoomable`，内置 `.zoom-badge`，页面底部引入 `../assets/zoomable-figure.js`。

## 课程进度

- 2026-10-20：工作区创建（MISSION + README 分阶段课表 + RESOURCES + lab 手册）。第一课《STP 机制——环路、选举与端口角色》已发布（`lessons/0001-stp-mechanism.html`），配套 `lab/0001-stp-lab.md`。
- 第一课设计要点：诊断缺口①（STP 只知道"是什么"不知道"怎么决定"）；四面板互动图手算选举（三交换机成环：C 为 root、A–B 网段平手比 Bridge ID、拔线重收敛）；精度点呼应诊断答案（阻塞≠down，照常收发 BPDU）。
- **第一课答案键：b / c / a / d**（root 选举 / 阻塞端口本质 / root port 依据 / RSTP 改进）。
- 下一课预告：《MAC 表与转发决策》（泛洪/转发/过滤三动作，VLAN 的地基）。

## 待办

- [ ] 用户完成第一课后：按课号写 `learning-records/0001-*.md` 与 `my-notes/0001-*.md`（规则沿用 Rust-Driver：一课一聚类记录 + 学生笔记整理版）
- [ ] 第二课《MAC 表与转发决策》待写（eNSP 实验：display mac-address 看学习/老化）
- [ ] 术语表速查页（`reference/glossary.html`）随课程积累，第一课可晋升词条：BPDU、Bridge ID、root bridge、root port、designated port、blocking、RSTP
