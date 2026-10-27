# NOTES.md — 工作笔记

## 用户偏好与背景（来自三轮设计拷问，2026-10-16）

- **身份**：网络设备相关运维工程师，用户方，公司设备完全黑盒，无测试机无 root。学习成果的检验场只能是自有硬件。
- **基础**：C 语言（会内存和指针），Python 应用层。所有权 / 借用是全新心智模型。
- **时间**：每周 5–10 小时。
- **文档口味**：仓库现有 md5 / bt / mp3 三篇是"原理先行、从零手搓、最终产出可用工具"的深度长文——用户吃这一套。课程产物要顺着这个习惯来。
- **语言规则（2026-10-19 用户明确要求）**：英语水平差。教学材料里凡代码关键字和特有名词之外的英文（规则原文、编译错误信息、工具界面文案等），保留英文并附中文对照。已写入 MISSION.md Constraints，所有后续课程和文档强制执行；第一课已做 retroactive 补译。
- **出题规则（2026-10-20 用户明确要求）**：布置的 rustlings 练习或自出题目，若含用户没学过的概念，必须先学完再做——做题时工作记忆只留给正在练的目标技能，不被生概念卡住。落实方式：练习避开未学概念（给等价的低门槛版本），或等对应专课开完再布置。已审计：第三课作业的 first_word 原含 iter().enumerate()（迭代器专课未到），已改为索引循环版（已编译验证等价）；rustlings 09_strings 四题审计通过（纯 String/&str 辨析与 API 表面，无新概念）。今后每布置作业前先对照已学概念清单过一遍。
- **课程形态选择**：用户主动选了 HTML 互动课为主线（"试试新风格"），短课 15–20 分钟 / 节，页面内要带互动练习。
- **决策风格**：接受推荐、不纠结；但对"顺手要的附加文档"会点名（如焊接文档），说明重视可带走的沉淀物。

## 已确认的关键决策

1. 主线 = 嵌入式 USB 设备（Rust），从易到难三层：设备端固件 → PC 端用户态工具 → 内核驱动（只读）。
2. 第一阶段项目：格斗游戏摇杆。传统摇杆布局（八向摇杆 + 8 按键）、有线、通用 HID 描述符（不套 XInput）。蓝牙 / hitbox / 宏 = v2。
3. 平台：Raspberry Pi Pico（rp2040-hal，同步代码，不用 embassy）。ESP32 / embassy 留到第二阶段。
4. 环境：Windows 原生 + rustup + UF2 拖拽烧录；不用 WSL；调试先走 USB 串口 printf。
5. 第二阶段项目：USB 网络检测盒。功能 = 网段活跃设备 top N + 异常告警（ARP 扫描等）；设备端轻量采集，重分析在 PC 端 Rust 工具。芯片第二阶段再定。
6. WoL 手机开机：降级为语言预备期的周末练手项目，PC 端 Rust CLI + 同 WiFi 网页按钮，不写手机 App。
7. 焊接：第一版面包板原型零焊接；装壳阶段学 through-hole（已点名要焊接入门文档，见 soldering-tutorial.md）。

## 组件库状态

- `assets/zoomable-figure.js`（2026-10-19 用户升级）：滚轮以光标为中心缩放（1~8 倍）、指针事件拖拽平移、布局式缩放（改宽高+left/top，不用 transform 以保证 SVG 矢量清晰）、iframe 透明捕获层、computeZoom 纯函数可在 Node 单测。配套 CSS 契约在 `assets/lesson.css` 的"可放大图表组件"段：展开态媒体必须 `position:absolute`，否则 JS 的 left/top 平移静默失效。
- 该组件已部署到 Japanese-Travel/assets/（两边文件一致），但 Japanese-Travel 的 4 节课暂无 figure/img，脚本尚未被引入——组件已武装待用。
- 实际使用点：`lessons/0001-ownership-and-move.html` 的所有权生命周期图、`lessons/0003-slices-and-ranges.html` 的切片胖指针图（内嵌 SVG）。

## 工作区文件地图（新会话必读）

- `MISSION.md`：使命、约束、范围（为什么教、教什么、不教什么）
- `LEARNER-PROFILE.md`：学习者档案（学习者是谁、强项与固有模式、偏好、教学策略结论）——**新 AI 接手前必读，防止用通用教法；每课结束由 AI 更新（进度快照 + 新偏好/能力信号），维护规则见该文件第六节**
- `NOTES.md`（本文件）：进度、环境事实、决策、归档规则
- `learning-records/`：一课一聚类的心智模型演变记录（决策级，不存流水账）
- `my-notes/`：一课一份的学生笔记（AI 按主题整理落盘）
- `reference/glossary.html`：已晋升术语（跨会话用语一致）
- `lessons/`：课程本体（HTML 互动课）
- `RESOURCES.md`：经在线核实的资源清单

## 学习进度

- 2026-10-19：rustlings 环境就绪——项目在 `E:\demo\rust\rustlings`（init 生成，含 rust-analyzer.toml），runner 已装（`.cargo/bin/rustlings.exe`），用户已加 PATH，watch 模式正常运行，共 94 题。命令：n 下一题 / h 提示 / l 列表 / c 全量检查 / x 重置 / q 退出。**move_semantics 六题已通过（第一课作业验收）**，用户进度至 05_vecs 之后的分类。
- 学习记录归档规则（2026-10-19 用户拍板）：**一课一个聚类记录**，文件名对应课号（如 `0001-ownership-move-copy-drop.md`），课内多次追问按时间顺序追加小节，演进痕迹即价值；不再一条记录一个文件。截至 2026-10-27 已有 0001–0007 七份聚类。
- **学生笔记规则（2026-10-19 用户拍板）**：每课一份学生笔记，放 `my-notes/`，文件名对应课号（如 `my-notes/0001-ownership-and-move.md`）。用户的原始笔记是临时提问、缺逻辑性，由 AI 按主题重组通顺后再落盘；误区处标注"曾误→正解"，未决问题进队列，结尾附自查问题。已发布第一课整理版（覆盖所有权四连问、七条归纳、drop 三连问、编译期机制、rustlings 00~06 十一条）。
- 学习进度：move_semantics 六题已通过（第一课作业验收），用户进度至 rustlings 06 之后的分类。第二课《借用与引用》已发布（lessons/0002-borrowing-and-references.html）。用户开放问题排队中：const 语义、区间半开理由（第三课）、闭包与迭代器（其后）。
- 2026-10-20：第二课里程碑——课后任务三项全部完成（The Book 4.2/4.3 原文通读、WoL 项目 String→&str 重构就地完成并运行验证）；术语表晋升 4 词条（借用、不可变引用、可变引用、悬垂引用）；learning-records/0002 聚类与 my-notes/0002 整理落盘。批阅 8 条笔记：主体全对；两处精度问题（引用作用域到"最后一次使用"而非一次、排他管"作用域重叠"不管"前后脚"）；一处真误区（区间半开的设计原因被 first_word 用例带偏——三条真正理由用户第一课就写对过，第三课须形式化重锚）；iter() 产出引用而非元素本体（小精度）。用户独立重发现"排他=编译期互斥"的并发洞察（已补数据竞争 vs 同步的边界）。追问弧线后续闭合：move 变量模型、&str vs &String、NLL 完整操作化规则（用户自主综合，探针证实）、栈模型推断（反例击穿：非 LIFO 死亡、集合成员而非栈顶、真实机制是 MIR 区域数据流）。
- 2026-10-20：第三课《切片与区间》发布（lessons/0003-slices-and-ranges.html）——收 primitive_types4 的 [1..4] 之问：三条半开设计理由形式化重锚（长度=上界−下界 / 相邻无缝 / 空区间可写），明确拆 first_word 误区（用例≠设计原因）；&str/&[T] 全貌 + 手绘胖指针图（可放大组件）；first_word 两版对照展示"切片+借用规则"合力（E0502）；字面量即 &str；参数收最泛类型。课后任务：The Book 4.3 回看、first_word 实战（WoL，含 oui 可选进阶）、rustlings 09_strings。术语表晋升（切片/区间）已于 2026-10-21 作业完成后完成。
- 2026-10-21：第三课作业三项全部提交并批阅。first_word 实现正确（&str→&str 索引循环，无空格分支已验证）；半开三理由脱离 first_word 复述，第二课误区正式收口。批阅发现三处需拧：① 第一版 first_word 返回的是空格下标（作业写成"长度"——first_word 的词总从 0 开始，数值恰好相等，但语义与类型都不同）；② E0502 被解释成"clear 交出所有权"——实为 &mut self 借用与存活 word 的不可变借用重叠，已用 E0502/E0382 对照与 NLL 顺序探针纠正；③ strings3 手搓 trim 四个测试全过但空串/全空白均越界 panic（已实测），且用了未学的 iter().enumerate().rev()（肯定自学超前，正式概念留给迭代器专课）。WoL main 已收尾为可编译 NLL 演示，`cargo run` 通过。课程修正：互动练习 2/4 反馈文案颠倒已修；第 5 节加"第一版返回下标不是长度"精度补丁与"clear ≠ move"常见误读提示。产物：my-notes/0003、learning-records/0003 落盘；术语表晋升切片/区间（共 15 词条）；LEARNER-PROFILE 同步。rustlings 进度 strings1–4 完成，下一分类 10_modules。
- 2026-10-21：第四课《闭包与迭代器》发布（lessons/0004-closures-and-iterators.html）——从 vecs2 的 map/collect、strings3 的 iter/enumerate/rev、Book 版 first_word 三条已有代码切入；闭包捕获三方式与 Fn/FnMut/FnOnce 门牌；iter/iter_mut/into_iter 所有权表；适配器/消费者与惰性、零成本；first_word 迭代器版；parse_mac 流水线。预检：lesson-quiz-preflight 静态 0 error / 0 warning；浏览器双分支正确 4/4、错误 0/4，锁题与类名正常，控制台无错误。课后 checkpoint：CP1 Book 13.1/13.2 三问；CP2 first_word 迭代器版 + 四边界输出；CP3 parse_mac 流水线重构；加餐 strings3 trim→trim()。下一课 const。
- 2026-10-21：第四课 CP1–CP3 全部完成并批阅。CP1 弧线：用户起初"不知道闭包是什么意思"、把 iter() 类型说成 &i32 指向游标；补最小闭包例子、C 上下文结构体类比与 `it / it.next() / &i32` 类型链后收敛。纠偏：map 构造时不执行闭包，真正循环在 collect/for；collect 目标类型由上下文决定（无上下文 E0283）；索引版与迭代器版都按需读取，不存在"索引版减少全量预加载"的性能差异。CP2 first_word 迭代器版 + 四边界（Hello/Solo/空串/三空格）通过；CP3 parse_mac 改 split/map/collect、print_hex 改 iter/enumerate，`cargo run` 的 102 字节魔术包与重构前一致。产物：my-notes/0004、learning-records/0004、术语表晋升闭包/迭代器（共 17 词条）、LEARNER-PROFILE 同步、WoL README 第四课小节。下一课 const；rustlings 进度 10_modules。
- 2026-10-22：第五课《const 与编译期常量》发布（lessons/0005-const-and-compile-time.html）——收第一课排队的 const 之问。主线：三种归属（let 运行期绑定 / const 编译期求值、使用处内联 / static 固定地址一份）；C 锚点（Rust const ≈ #define / constexpr，Rust static ≈ 有地址的全局对象）；E0435 / E0015 / E0080 / E0133 错误编号表；const fn 与 `const _` 编译期断言；固件固定缓冲（WoL 102 字节）与 static mut 的替代方向。设计时实测发现 `static N: usize = 4; let buf = [0u8; N];` 合法——课程已把 const/static 分界写成“地址与份数”，而不是“能否编译期使用”，避免制造新误区。预检：lesson-quiz-preflight 静态 0 error / 0 warning；浏览器双分支正确 4/4、错误 0/4，锁题与类名正常，控制台无错误。课程代码均用 rustc 1.99.1 / edition 2021 实测。课后 checkpoint：CP1 三条概念笔记；CP2 WoL const 块 + 编译期断言；CP3 build_magic_packet 改 [u8; PACKET_LEN]。下一课：模块与可见性（对齐 rustlings 10_modules）。
- 2026-10-22：第五课 CP1 通过（三轮修正）。关键纠偏：const 不保证份数/固定地址，static 才是固定一份；普通 static 不可变，static mut 才能直接改且 unsafe；static mut 的 unsafe 原因是全局可写共享 + 编译器无法证明同步，unsafe 是担保不是防竞争。追问覆盖 static &str vs let 的双层内存、const 内联/地址、Java static 类比、static 不 Drop 与泄漏、`const _` 生命周期、立即数；均以探针/对照表回答。CP2 待交：WoL 顶部 const 块 + `const _` 编译期断言。
- 2026-10-22：第五课 CP2 通过。WoL 顶部新增 `MAGIC_LEN` / `MAC_LEN` / `REPEAT` / `PACKET_LEN` 与 `const _: () = assert!(PACKET_LEN == 102);`；`cargo check` 通过，`cargo run` 仍输出 102 字节魔术包；可选实验把 102 改成 101 成功触发 E0080，证明编译期护栏。剩余一个 doc comment 归属问题：`const _` 夹在 `///` 与 `fn build_magic_packet` 之间，文档注释会贴到 `const _` 上；开 CP3 前把 `const _` 挪到 `///` 之前。CP3 待交：`build_magic_packet` 返回 `[u8; PACKET_LEN]`。
- 2026-10-22：第五课 CP3 通过并结课。`build_magic_packet` 返回 `[u8; PACKET_LEN]`：前 `MAGIC_LEN` 字节用可变切片填 `0xFF`，嵌套循环按 `MAGIC_LEN + i * MAC_LEN + j` 写入 MAC；`cargo check` 无 warning，`cargo run` 102 字节与重构前一致。第一版只填了 `0xFF`、MAC 全是 `0x00`，并出现 `unused variable: mac_bytes`；补循环后通过。`parse_mac` 仍返回 `Vec`，完全无分配留到固件课。产物：my-notes/0005、learning-records/0005（CP1–CP3）、术语表晋升 const/static（语言核心共 19 词条）、LEARNER-PROFILE 同步、WoL README 第五课小节。下一课：模块与可见性（rustlings 10_modules）。
- 2026-10-22：第六课《模块与可见性》发布（lessons/0006-modules-and-visibility.html）——从 WoL 单文件切入；模块树、默认私有与 pub/pub(crate)、crate/self/super 路径、use/as/pub use、文件模块；用 E0603（私有函数/私有模块）与 E0433（use 不跨作用域）做错误编号对照。实测修正一个精度：`PACKET_LEN` 不必因为出现在公开函数返回类型就 `pub`，签名里的 `[u8; PACKET_LEN]` 对外是 `[u8; 102]`。预检：lesson-quiz-preflight 静态 0 error / 0 warning；浏览器正确 4/4、错误 0/4，锁题正常，控制台无错误（截图因浏览器不可见未取，结构快照与 DOM 已验证）。CP1 模块树/隐私/use 三条概念笔记；CP2 rustlings 10_modules modules1–3；CP3 WoL 拆出 src/protocol.rs。下一课：结构体与枚举（rustlings 07/08）。
- 2026-10-22：第六课 CP1 通过。三轮追问后分开 crate/package/file 三层：crate 是编译单元/根，package 是 Cargo.toml 项目，file 只是模块存放位置；lib 与 bin 是不同 crate，`pub(crate)` 不跨 crate；一个进程只有一个 binary 入口，但可链接 N 个 library crate。模块树、`parse_mac` 私有、嵌套盒子权限链、`use`/`pub use`、E0433 修法均正确。CP2 待交：rustlings 10_modules modules1–3。
- 2026-10-22：第六课 CP2 通过。rustlings 10_modules modules1–3 全过，状态推进 hashmaps1；modules1 给 `make_sausage` 加 `pub`，modules2 用两条 `pub use ... as ...`，modules3 最初写成 `pub use std::time::{...}`，已纠正为 `use`——std 的项本来就公开，`use` 只引入名字，`pub use` 是重新导出。CP3 待交：WoL 拆 `src/protocol.rs`，`parse_mac` 私有，`build_magic_packet` / `print_hex` 公开。
- 2026-10-22：第六课 CP3 通过并结课。WoL 拆成 `src/main.rs` + `src/protocol.rs`：main 只留 `mod protocol;`、`use protocol::{build_magic_packet, print_hex};`、`first_word` 与 `main`；protocol 里 `build_magic_packet` / `print_hex` 为 pub，`parse_mac` 与常量保持私有。`cargo fmt`、`cargo check` 通过，`cargo run` 仍输出 102 字节。产物：my-notes/0006、learning-records/0006（CP1–CP3）、术语表晋升 crate/module/visibility/use/pub use/package/workspace（语言核心 24 词条）、WoL README 第六课小节、LEARNER-PROFILE 同步。下一课：结构体与枚举（rustlings 07/08）。
- 2026-10-22：第七课《结构体与枚举》发布（lessons/0007-structs-and-enums.html）——从按键数据模型切入；命名字段/元组/单元结构体、impl 与 `&self`/`&mut self`/`self`、关联函数 `new`/`Self`、枚举变体携带数据、match 穷尽（E0004）/`_`/if let；结构体字段 mut 的 E0594；固件按键状态与事件模型。预检：lesson-quiz-preflight 静态 0 error / 0 warning；浏览器正确 4/4、错误 0/4，锁题正常，控制台无错误。CP1 三条概念笔记；CP2 rustlings 07_structs + 08_enums 六题；CP3 demo/button-model 按键事件模型。下一课：Option 与错误处理。
- 2026-10-27：第七课 CP1–CP3 全部通过并结课。CP1 三轮修正：元组结构体外层不是“一个元组”（`Pp(u8,u32,bool)` 是三个字段，`Pp((u8,u32,bool))` 才是一个元组字段）；字段全 Copy ≠ 结构体 Copy，整体赋值仍 move，`..base` 逐字段，`assert_eq!` 只借用；`Self` 是 impl 类型别名，`self` 是接收者。CP2 rustlings structs1–3、enums1–3 六题全过，状态下一题 hashmaps1；structs2 的 `..order_template` 解释通过（name 显式给出不移动 String；省略则部分移动）。CP3 `demo/button-model` 完成：`ButtonState` + `ButtonEvent` + `new`/`update`，`cargo run` 输出 pressed / held / released；理由：三个 bool 非法组合太多，enum 三选一 + match 穷尽更精确。产物：my-notes/0007、learning-records/0007、术语表晋升 13 词条（语言核心 37 词条）、demo/button-model/README、LEARNER-PROFILE 同步。下一课：Option 与错误处理。
- 2026-10-27：第八课《Option 与错误处理》发布（lessons/0008-option-and-error-handling.html）——收第七课的两个尾巴：button-model 的 false/false → `None`；WoL `parse_mac` 的 `unwrap_or(0)` → `Result`。主线：Option/Result 对照、`ok_or` 转换、unwrap/expect 边界（panic 退出码 101）、`?` 展开与返回类型匹配（E0277 三向对照：unit main / Option in Result / Result in Option）、`main -> Result`（E: Debug / Termination）、`MacError` 自定义错误与 pub 可见性（private_interfaces）。预检：lesson-quiz-preflight 静态 0 error / 0 warning；四道 quiz 的代码用 rustc 逐题复核；浏览器正确分支 4/4、错误分支 0/4、锁题有效、部分计分 1/4、控制台无错误。CP1 三条概念笔记；CP2 rustlings options1–3 + errors1–3（hashmaps1–3 暂跳，集合课再补）；CP3 button-model Option 收口 + WoL Result 改造。下一课：trait 与泛型。

## 待核实 / 后续事项

- [x] 环境搭建文档已写（setup-rust-windows.md）：rustup + rustlings，含 link.exe 问题的 GNU 工具链解法；第一课课后任务已同步为新版命令（rustlings init / rustlings，旧版 watch 已废弃——官网已核实）
- [ ] 第一课前核实 rp2040-hal 的 MSRV（crates.io 页面 JS 渲染，抓取失败；以 crates.io 显示为准）
- [ ] 摇杆 v1 功能边界细化：按键数 8 个是否含 Start/Select，外壳方案
- [ ] 网络检测盒第二阶段选型：ESP32-S3 + W5500 vs 树莓派 USB gadget
