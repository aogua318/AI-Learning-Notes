---
name: lesson-quiz-preflight
description: "Preflight QA for HTML interactive lessons with inline quizzes before opening them: verify each answer key against okMsg/errMsg polarity, option coverage, scoring and lock logic, then browser-check both answer branches and organize the session by homework checkpoints. 用于开始或继续教学工作区的互动课、复用旧课，或修改课程答案与反馈文案之后；发现极性反转、答案不在选项中、分母不符等问题时先修复再交付。"
---

# Lesson Quiz Preflight

## 用途

在把含内联 quiz 的 HTML 互动课交给学生之前，先做一次可复现的预检：结构、答案键、反馈极性、计分、锁题、浏览器行为。它是 `teach` 的课前卫兵，不替代备课与教学流程。

## 何时使用

- 开始或继续教学工作区里的互动课，尤其是复用旧课。
- 复制课程模板、修改 `QUIZ_ANSWERS`、选项或反馈文案之后。
- 学生报告“答对却显示不对”“分数不对”“点了没反应”。

## 预检流程

### 1. 静态检查

运行：

```bash
python <skill-dir>/scripts/quiz_preflight.py <lesson.html> [more.html ...]
```

脚本只覆盖当前固定模板：`QUIZ_ANSWERS` + `.quiz[data-quiz]` + `button[data-choice]` + `.quiz-feedback` + `.quiz-score`。它检查数量、ID、选项覆盖、反馈极性、分母、锁题映射和反馈映射。遇到不认识的模板会报 unsupported，不会静默放行。

脚本不判断题目事实是否正确，必须继续做第 2、3 步。

### 2. 逐题语义核对

对每题确认：

1. `correct` 与题目事实一致：编译/运行题用最小示例复现；概念题回查对应课节。
2. `okMsg` 以肯定语气开头，解释“为什么对”；`errMsg` 以否定语气开头，解释“为什么错”并指回课节。
3. 反馈分支没有接反：正确选项不能显示错误解释，错误选项不能显示正确解释。
4. 题干是否定式（“以下哪个不对”）、存在多解、选项与解释不匹配时，人工判定，不能只看前缀。
5. 每题至少两个选项，`correct` 必须属于该题的 `data-choice`。

### 3. 浏览器双分支验收

用可用浏览器工具打开本地课程（`file:///...`），硬刷新并检查控制台。对每题分别：

- 点正确选项：出现 `✔` + `okMsg`，分数 +1，选项 `.correct`，反馈 `.ok`。
- 重新加载后点错误选项：出现 `✘` + `errMsg`，分数不变，所选项 `.wrong`，正确项被标出，反馈 `.err`。
- 答过再点：不再加分或改反馈。
- 全部答完：总分分母正确，最终提示正确。

浏览器不可用时，明确记录“交互未验证”，不得宣称预检通过。

### 4. 修复规则

- 答案键正确、文案接反：只交换 `okMsg` / `errMsg`。
- 答案键错误：改答案键，并重写两条反馈；不要只换文案迎合错误答案。
- 课程内容错误：改内容或删题；不要用反馈文案掩盖错误。
- 存在未解决的 `ERROR`：不开课、不交付；修复后重跑静态检查和浏览器验收。

### 5. 按作业 checkpoint 交接

预检通过后再开课。读取课程“课后任务/作业”一节，列出：

| checkpoint | 对应课节 | 交付物 | 验收证据 |
|---|---|---|---|

先给出完整顺序与依赖，再要求学生一次交一项；没有代码、报错原文、测试输出或运行结果，不标记完成。若开课后又改了课程，重新预检。

## 反馈极性的判定基准

- 肯定开头：`对`、`正确`、`是的`、`没错`、`✔`、`✓`。
- 否定开头：`不对`、`错`、`不是`、`不正确`、`错误`、`有误`、`✘`、`✗`。
- 这些只是静态启发式；带反讽、条件句或“对……但……”的文案必须人工判断。

## 来源案例

`Rust-Driver` 第三课曾出现练习 2/4 的 `correct: "err"`，但 `okMsg` 以“不对”开头、`errMsg` 以“对”开头；学生答对时会看到否定反馈。修复只交换两条文案，答案键保持不变。该案例说明：答案键与展示文案是两层，必须分别核对。

## 资源

- `scripts/quiz_preflight.py`：固定模板的静态检查器；用法见脚本 `--help`。
