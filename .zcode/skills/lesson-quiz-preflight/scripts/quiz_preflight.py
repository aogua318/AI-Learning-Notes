#!/usr/bin/env python3
"""HTML 互动课 quiz 静态预检。

用途：
    python quiz_preflight.py lesson.html [more.html ...]

只覆盖当前教学工作区使用的固定模板：
    QUIZ_ANSWERS = [{ correct, okMsg, errMsg }, ...]
    .quiz[data-quiz] / button[data-choice] / .quiz-feedback / .quiz-score

检查结构、答案键是否落在选项里、反馈语气是否接反、计分分母、锁题与反馈映射。
它不判断题目事实是否正确；那一步需要人工核对和浏览器验收。
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

POSITIVE_MARKERS = ("对", "正确", "是的", "没错")
NEGATIVE_MARKERS = ("不对", "错", "不是", "不正确", "错误", "有误")
POSITIVE_SYMBOLS = "✔✓√"
NEGATIVE_SYMBOLS = "✘✗×"
LEADING_SYMBOLS = POSITIVE_SYMBOLS + NEGATIVE_SYMBOLS
MESSAGE_LIMIT = 90


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    level: str
    code: str
    message: str


@dataclass
class Button:
    choice: str | None
    line: int


@dataclass
class QuizCard:
    qid_raw: str | None
    line: int
    buttons: list[Button] = field(default_factory=list)
    feedback_line: int | None = None
    feedback_count: int = 0
    nested: bool = False


@dataclass
class QuizConfig:
    index: int
    line: int
    fields: dict[str, str] = field(default_factory=dict)
    lines: dict[str, int] = field(default_factory=dict)
    duplicate_fields: set[str] = field(default_factory=set)


class QuizHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[QuizCard] = []
        self.scores: list[dict[str, object]] = []
        self._card: QuizCard | None = None
        self._depth = 0
        self._score: dict[str, object] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: (value or "") for key, value in attrs}
        classes = attributes.get("class", "").split()

        if tag == "div" and "quiz" in classes:
            if self._card is not None:
                self._card.nested = True
                self._card = None
            self._card = QuizCard(qid_raw=attributes.get("data-quiz"), line=self.getpos()[0])
            self.cards.append(self._card)
            self._depth = 1
            return

        if self._card is not None:
            if tag == "div":
                self._depth += 1
            elif tag == "button":
                self._card.buttons.append(Button(attributes.get("data-choice"), self.getpos()[0]))
            elif tag == "p" and "quiz-feedback" in classes:
                self._card.feedback_count += 1
                if self._card.feedback_line is None:
                    self._card.feedback_line = self.getpos()[0]

        if tag == "p" and "quiz-score" in classes:
            self._score = {"line": self.getpos()[0], "text": ""}
            self.scores.append(self._score)

    def handle_endtag(self, tag: str) -> None:
        if self._card is not None and tag == "div":
            self._depth -= 1
            if self._depth <= 0:
                self._card = None
        if self._score is not None and tag == "p":
            self._score = None

    def handle_data(self, data: str) -> None:
        if self._score is not None:
            self._score["text"] = str(self._score["text"]) + data


def line_of(text: str, position: int) -> int:
    return text.count("\n", 0, max(0, position)) + 1


def shorten(value: str, limit: int = MESSAGE_LIMIT) -> str:
    flattened = " ".join(value.split())
    return flattened if len(flattened) <= limit else flattened[: limit - 1] + "…"


def leading_text(value: str) -> str:
    value = value.lstrip()
    while value and (value[0] in LEADING_SYMBOLS or value[0] in "：:—- "):
        value = value[1:].lstrip()
    return value


def polarity(value: str) -> str | None:
    stripped = value.lstrip()
    if stripped[:1] in NEGATIVE_SYMBOLS:
        return "negative"
    if stripped[:1] in POSITIVE_SYMBOLS:
        return "positive"
    stripped = leading_text(stripped)
    for marker in NEGATIVE_MARKERS:
        if stripped.startswith(marker):
            return "negative"
    for marker in POSITIVE_MARKERS:
        if stripped.startswith(marker):
            return "positive"
    return None


def skip_js_literal(text: str, index: int, end: int) -> int | None:
    if index + 1 < end and text[index] == "/" and text[index + 1] == "/":
        newline = text.find("\n", index + 2, end)
        return end if newline < 0 else newline + 1
    if index + 1 < end and text[index] == "/" and text[index + 1] == "*":
        closing = text.find("*/", index + 2, end)
        return end if closing < 0 else closing + 2
    if index < end and text[index] in "'\"`":
        quote = text[index]
        cursor = index + 1
        while cursor < end:
            if text[cursor] == "\\":
                cursor += 2
                continue
            if text[cursor] == quote:
                return cursor + 1
            cursor += 1
        return end
    return None


def find_matching(text: str, start: int, open_char: str, close_char: str) -> int:
    if start < 0 or start >= len(text) or text[start] != open_char:
        return -1
    depth = 0
    index = start
    while index < len(text):
        skipped = skip_js_literal(text, index, len(text))
        if skipped is not None:
            index = skipped
            continue
        char = text[index]
        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def iter_top_level_objects(text: str, start: int, end: int):
    index = start
    depth = 0
    object_start: int | None = None
    while index < end:
        skipped = skip_js_literal(text, index, end)
        if skipped is not None:
            index = skipped
            continue
        char = text[index]
        if char == "{":
            if object_start is None:
                object_start = index
                depth = 1
            else:
                depth += 1
        elif char == "}" and object_start is not None:
            depth -= 1
            if depth == 0:
                yield object_start, index + 1
                object_start = None
        index += 1


def decode_js_string(raw: str) -> str:
    if len(raw) < 2:
        return raw
    quote = raw[0]
    body = raw[1:-1]
    if quote == "`" and "${" in body:
        raise ValueError("不支持带插值的模板字符串")
    output: list[str] = []
    escapes = {
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "b": "\b",
        "f": "\f",
        "v": "\v",
        "0": "\0",
        "\\": "\\",
        "'": "'",
        '"': '"',
        "`": "`",
        "/": "/",
    }
    index = 0
    while index < len(body):
        char = body[index]
        if char != "\\":
            output.append(char)
            index += 1
            continue
        index += 1
        if index >= len(body):
            break
        escape = body[index]
        index += 1
        if escape in escapes:
            output.append(escapes[escape])
        elif escape == "x" and index + 2 <= len(body):
            output.append(chr(int(body[index : index + 2], 16)))
            index += 2
        elif escape == "u" and index + 4 <= len(body):
            output.append(chr(int(body[index : index + 4], 16)))
            index += 4
        elif escape in "\r\n":
            if escape == "\r" and index < len(body) and body[index] == "\n":
                index += 1
        else:
            output.append(escape)
    return "".join(output)


FIELD_RE = re.compile(
    r"(?<![\w$])(correct|okMsg|errMsg)\s*:\s*"
    r"(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)",
    re.DOTALL,
)
QUIZ_RE = re.compile(r"\bQUIZ_ANSWERS\s*=\s*\[")


def extract_js_configs(text: str) -> tuple[int, list[QuizConfig]]:
    match = QUIZ_RE.search(text)
    if not match:
        raise ValueError("未找到 QUIZ_ANSWERS 数组")
    array_start = text.find("[", match.start())
    array_end = find_matching(text, array_start, "[", "]")
    if array_end < 0:
        raise ValueError("QUIZ_ANSWERS 数组没有闭合")

    configs: list[QuizConfig] = []
    for index, (object_start, object_end) in enumerate(
        iter_top_level_objects(text, array_start + 1, array_end)
    ):
        object_text = text[object_start:object_end]
        config = QuizConfig(index=index, line=line_of(text, object_start))
        for field_match in FIELD_RE.finditer(object_text):
            key = field_match.group(1)
            raw = field_match.group(2)
            if key in config.fields:
                config.duplicate_fields.add(key)
                continue
            try:
                value = decode_js_string(raw)
            except ValueError:
                value = raw[1:-1]
            config.fields[key] = value
            config.lines[key] = line_of(text, object_start + field_match.start(1))
        configs.append(config)
    return match.start(), configs


def check_config(path: Path, config: QuizConfig, card: QuizCard, findings: list[Finding]) -> None:
    label = f"quiz[{config.index}]"
    if config.duplicate_fields:
        findings.append(
            Finding(
                path,
                config.line,
                "WARN",
                "duplicate-field",
                f"{label}: 重复字段 {sorted(config.duplicate_fields)}，只采用第一次出现的值",
            )
        )

    choices: list[str] = []
    for button in card.buttons:
        if button.choice is None:
            findings.append(
                Finding(path, button.line, "ERROR", "choice", f"{label}: button 缺少 data-choice")
            )
        elif button.choice in choices:
            findings.append(
                Finding(
                    path,
                    button.line,
                    "ERROR",
                    "choice",
                    f"{label}: data-choice={button.choice!r} 重复",
                )
            )
        else:
            choices.append(button.choice)
    if len(card.buttons) < 2:
        findings.append(
            Finding(
                path,
                card.line,
                "ERROR",
                "choice",
                f"{label}: 至少需要两个选项，当前 {len(card.buttons)} 个",
            )
        )
    if card.feedback_count == 0:
        findings.append(
            Finding(path, card.line, "ERROR", "feedback", f"{label}: 缺少 .quiz-feedback 元素")
        )
    elif card.feedback_count > 1:
        findings.append(
            Finding(
                path,
                card.line,
                "WARN",
                "feedback",
                f"{label}: 有 {card.feedback_count} 个 .quiz-feedback，通常应只有一个",
            )
        )

    correct = config.fields.get("correct")
    correct_line = config.lines.get("correct", config.line)
    if not correct:
        findings.append(
            Finding(path, correct_line, "ERROR", "answer-key", f"{label}: 缺少 correct")
        )
    elif correct not in choices:
        findings.append(
            Finding(
                path,
                correct_line,
                "ERROR",
                "answer-key",
                f"{label}: correct={correct!r} 不在选项 {choices!r} 中",
            )
        )

    ok_msg = config.fields.get("okMsg")
    err_msg = config.fields.get("errMsg")
    if not ok_msg or not ok_msg.strip():
        findings.append(
            Finding(
                path,
                config.lines.get("okMsg", config.line),
                "ERROR",
                "feedback-text",
                f"{label}: 缺少 okMsg",
            )
        )
    if not err_msg or not err_msg.strip():
        findings.append(
            Finding(
                path,
                config.lines.get("errMsg", config.line),
                "ERROR",
                "feedback-text",
                f"{label}: 缺少 errMsg",
            )
        )
    if ok_msg and err_msg and ok_msg.strip() == err_msg.strip():
        findings.append(
            Finding(path, config.line, "ERROR", "feedback-text", f"{label}: okMsg 与 errMsg 相同")
        )

    if ok_msg and ok_msg.strip():
        kind = polarity(ok_msg)
        if kind == "negative":
            findings.append(
                Finding(
                    path,
                    config.lines.get("okMsg", config.line),
                    "ERROR",
                    "polarity",
                    f"{label}: correct={correct!r}，但 okMsg 以否定语气开头：{shorten(ok_msg)!r}",
                )
            )
        elif kind is None:
            findings.append(
                Finding(
                    path,
                    config.lines.get("okMsg", config.line),
                    "WARN",
                    "polarity",
                    f"{label}: okMsg 未以已知肯定词开头，需人工确认：{shorten(ok_msg)!r}",
                )
            )
        if len(ok_msg.strip()) < 4:
            findings.append(
                Finding(
                    path,
                    config.lines.get("okMsg", config.line),
                    "WARN",
                    "feedback-text",
                    f"{label}: okMsg 过短，可能没有解释原因",
                )
            )

    if err_msg and err_msg.strip():
        kind = polarity(err_msg)
        if kind == "positive":
            findings.append(
                Finding(
                    path,
                    config.lines.get("errMsg", config.line),
                    "ERROR",
                    "polarity",
                    f"{label}: correct={correct!r}，但 errMsg 以肯定语气开头：{shorten(err_msg)!r}",
                )
            )
        elif kind is None:
            findings.append(
                Finding(
                    path,
                    config.lines.get("errMsg", config.line),
                    "WARN",
                    "polarity",
                    f"{label}: errMsg 未以已知否定词开头，需人工确认：{shorten(err_msg)!r}",
                )
            )
        if len(err_msg.strip()) < 4:
            findings.append(
                Finding(
                    path,
                    config.lines.get("errMsg", config.line),
                    "WARN",
                    "feedback-text",
                    f"{label}: errMsg 过短，可能没有解释原因",
                )
            )


def check_score(
    path: Path,
    parser: QuizHTMLParser,
    quiz_count: int,
    text: str,
    js_start: int,
    findings: list[Finding],
) -> None:
    if not parser.scores:
        findings.append(Finding(path, 1, "ERROR", "score", "缺少 .quiz-score 总分元素"))
        return
    if len(parser.scores) > 1:
        findings.append(
            Finding(
                path,
                int(parser.scores[1]["line"]),
                "WARN",
                "score",
                f"检测到 {len(parser.scores)} 个 .quiz-score，通常应只有一个",
            )
        )

    score = parser.scores[0]
    score_text = str(score["text"])
    score_line = int(score["line"])
    match = re.search(r"/\s*(\d+)", score_text)
    if not match:
        findings.append(
            Finding(path, score_line, "WARN", "score", f"总分文案未找到 '/ N'：{shorten(score_text)!r}")
        )
    elif int(match.group(1)) != quiz_count:
        findings.append(
            Finding(
                path,
                score_line,
                "ERROR",
                "score",
                f"总分分母是 {match.group(1)}，但 quiz 卡片有 {quiz_count} 个",
            )
        )

    script = text[js_start:]
    seen_denominators: set[int] = set()
    for js_match in re.finditer(r"[\"']\s*/\s*(\d+)\s*[\"']", script):
        denominator = int(js_match.group(1))
        if denominator in seen_denominators:
            continue
        seen_denominators.add(denominator)
        if denominator != quiz_count:
            findings.append(
                Finding(
                    path,
                    line_of(text, js_start + js_match.start()),
                    "ERROR",
                    "score",
                    f"JS 计分分母是 {denominator}，但 quiz 卡片有 {quiz_count} 个",
                )
            )


def check_js(path: Path, quiz_count: int, text: str, js_start: int, findings: list[Finding]) -> None:
    script = text[js_start:]
    required_patterns = [
        (
            r"isRight\s*\?\s*[^;\n]*okMsg\s*:\s*[^;\n]*errMsg",
            "feedback-map",
            "未找到 isRight 的 okMsg/errMsg 分支映射",
        ),
        (
            r"isRight\s*\?\s*[\"']✔\s*[\"']\s*:\s*[\"']✘",
            "feedback-marker",
            "未找到 isRight 的 ✔/✘ 标记映射",
        ),
        (
            r"isRight\s*\?\s*[\"']ok[\"']\s*:\s*[\"']err[\"']",
            "feedback-class",
            "未找到 isRight 的 ok/err 反馈类名映射",
        ),
    ]
    for pattern, code, message in required_patterns:
        if not re.search(pattern, script):
            findings.append(Finding(path, 1, "WARN", code, message))

    for needle, code, message in [
        ("QUIZ_ANSWERS[quizId]", "answer-index", "未找到 QUIZ_ANSWERS[quizId] 的题目索引"),
        ("answered[quizId]", "lock", "未找到 answered[quizId] 的锁题判断"),
    ]:
        if needle not in script:
            findings.append(Finding(path, 1, "WARN", code, message))

    if not re.search(r"\.disabled\s*=\s*true", script):
        findings.append(Finding(path, 1, "WARN", "lock", "未找到按钮禁用的 .disabled = true"))
    if not re.search(r"score\s*=\s*score\s*\+\s*1|score\s*\+\+|score\s*\+=\s*1", script):
        findings.append(Finding(path, 1, "WARN", "score", "未找到 score 加一的计分逻辑"))

    final_match = re.search(r"score\s*={2,3}\s*(\d+)", script)
    if not final_match:
        findings.append(Finding(path, 1, "WARN", "score", "未找到满分判断（score === N）"))
    elif int(final_match.group(1)) != quiz_count:
        findings.append(
            Finding(
                path,
                line_of(text, js_start + final_match.start()),
                "WARN",
                "score",
                f"满分判断是 {final_match.group(1)}，但 quiz 卡片有 {quiz_count} 个",
            )
        )

    answered_match = re.search(r"\banswered\s*=\s*\{", script)
    if not answered_match:
        findings.append(Finding(path, 1, "WARN", "lock", "未找到 answered 初始化映射"))
        return
    brace_start = script.find("{", answered_match.start())
    brace_end = find_matching(script, brace_start, "{", "}")
    if brace_end < 0:
        findings.append(
            Finding(
                path,
                line_of(text, js_start + answered_match.start()),
                "WARN",
                "lock",
                "answered 映射没有闭合",
            )
        )
        return

    block = script[brace_start : brace_end + 1]
    keys = {int(item) for item in re.findall(r"(?<![\w$])(\d+)\s*:", block)}
    expected = set(range(quiz_count))
    if keys != expected:
        findings.append(
            Finding(
                path,
                line_of(text, js_start + answered_match.start()),
                "WARN",
                "lock",
                f"answered 键与题目编号不一致：缺少 {sorted(expected - keys)}，多余 {sorted(keys - expected)}",
            )
        )


def check_file(path: Path, findings: list[Finding]) -> int:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        findings.append(Finding(path, 1, "ERROR", "read", f"无法读取文件：{exc}"))
        return 0

    parser = QuizHTMLParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:  # HTMLParser 对畸形输入也可能抛异常
        findings.append(Finding(path, 1, "ERROR", "html", f"HTML 解析失败：{exc}"))
        return len(parser.cards)

    cards = parser.cards
    try:
        js_start, configs = extract_js_configs(text)
    except ValueError as exc:
        findings.append(Finding(path, 1, "ERROR", "quiz-answers", str(exc)))
        js_start, configs = 0, []

    if not cards and not configs:
        findings.append(
            Finding(
                path,
                1,
                "WARN",
                "no-quiz",
                "未找到 .quiz[data-quiz] 卡片；如果这不是互动课，可忽略",
            )
        )
        return 0

    if not cards:
        findings.append(
            Finding(path, 1, "ERROR", "structure", "存在 QUIZ_ANSWERS，但没有 .quiz[data-quiz] 卡片")
        )
    if not configs:
        findings.append(
            Finding(path, 1, "ERROR", "structure", "存在 .quiz 卡片，但没有可用的 QUIZ_ANSWERS")
        )
    if cards and configs and len(cards) != len(configs):
        findings.append(
            Finding(
                path,
                1,
                "ERROR",
                "count",
                f"quiz 卡片 {len(cards)} 个，但 QUIZ_ANSWERS 有 {len(configs)} 项",
            )
        )

    cards_by_id: dict[int, QuizCard] = {}
    for card in cards:
        if card.nested:
            findings.append(
                Finding(path, card.line, "WARN", "nested-quiz", "检测到嵌套或未闭合的 .quiz 卡片")
            )
        if card.qid_raw is None:
            findings.append(Finding(path, card.line, "ERROR", "quiz-id", "缺少 data-quiz 属性"))
            continue
        try:
            qid = int(card.qid_raw)
        except ValueError:
            findings.append(
                Finding(
                    path,
                    card.line,
                    "ERROR",
                    "quiz-id",
                    f"data-quiz={card.qid_raw!r} 不是整数",
                )
            )
            continue
        if qid in cards_by_id:
            findings.append(
                Finding(path, card.line, "ERROR", "quiz-id", f"data-quiz={qid} 重复")
            )
            continue
        cards_by_id[qid] = card

    expected_ids = set(range(len(configs))) if configs else set(range(len(cards)))
    for qid in sorted(set(cards_by_id) - expected_ids):
        findings.append(
            Finding(
                path,
                cards_by_id[qid].line,
                "ERROR",
                "quiz-id",
                f"data-quiz={qid} 超出题目编号范围",
            )
        )
    for qid in sorted(expected_ids - set(cards_by_id)):
        findings.append(Finding(path, 1, "ERROR", "quiz-id", f"缺少 data-quiz={qid} 的卡片"))

    for config in configs:
        card = cards_by_id.get(config.index)
        if card is not None:
            check_config(path, config, card, findings)

    if cards:
        check_score(path, parser, len(cards), text, js_start, findings)
        check_js(path, len(cards), text, js_start, findings)

    return len(cards)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    argument_parser = argparse.ArgumentParser(
        description="检查 HTML 互动课的 quiz 结构、答案键、反馈极性、计分与锁题映射"
    )
    argument_parser.add_argument("files", nargs="+", type=Path, help="要检查的 HTML 课程文件")
    argument_parser.add_argument("--strict", action="store_true", help="把 WARN 也视为失败")
    args = argument_parser.parse_args(argv)

    findings: list[Finding] = []
    quiz_total = 0
    for path in args.files:
        quiz_total += check_file(path, findings)

    for finding in findings:
        print(f"{finding.path}:{finding.line} [{finding.level}] {finding.code}: {finding.message}")

    errors = sum(1 for finding in findings if finding.level == "ERROR")
    warnings = sum(1 for finding in findings if finding.level == "WARN")
    print(
        f"Summary: {len(args.files)} file(s), {quiz_total} quiz(zes), "
        f"{errors} error(s), {warnings} warning(s)"
    )
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
