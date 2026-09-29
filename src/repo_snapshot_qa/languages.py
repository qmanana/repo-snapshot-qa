"""语言注册表：识别代码文件并对其做轻量语法校验。

本模块让质检链路从「只认 Python」泛化为「多语言」：代码文件按扩展名分类，
语法校验则按语言分别实现——Python/JSON/TOML 用标准库真实解析，C 系语言用
「括号配平 + 跳过字符串/注释」的启发式烟测，其余语言标记为 unsupported
（计入代码规模，但排除出可解析率的分母）。全程零第三方依赖。
"""
from __future__ import annotations

import ast
import json
import tomllib
from pathlib import Path

# 扩展名 -> 语言名。这是「代码文件」的判定依据，参与代码规模统计。
CODE_EXTENSIONS: dict[str, str] = {
    ".py": "Python",
    ".pyw": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".hh": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".json": "JSON",
    ".toml": "TOML",
    ".yaml": "YAML",
    ".yml": "YAML",
}

# 数据/配置类语言（非源码），用于在「遗留标记」等检查中排除噪音。
CONFIG_LANGS = frozenset({"JSON", "TOML", "YAML"})

# 纯源码扩展名（排除 JSON/TOML/YAML），用于子系统与聚合性统计。
SOURCE_EXTENSIONS = frozenset(
    ext for ext, lang in CODE_EXTENSIONS.items() if lang not in CONFIG_LANGS
)

# 用「括号配平」做启发式烟测的 C 系语言集合。
_C_LIKE = frozenset({
    "JavaScript", "TypeScript", "Go", "Rust", "Java", "C", "C++",
    "C#", "Ruby", "PHP", "Swift", "Kotlin", "Scala",
})


def classify(path: Path) -> str | None:
    """返回文件所属语言名，非代码文件返回 None。"""
    return CODE_EXTENSIONS.get(path.suffix.lower())


def is_code_file(path: Path) -> bool:
    """判断文件是否为代码文件（按扩展名）。"""
    return path.suffix.lower() in CODE_EXTENSIONS


def is_source_path(path: str) -> bool:
    """判断提交改动的路径是否为源码文件（排除 __init__ 与数据/配置）。"""
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    if name == "__init__.py":
        return False
    return Path(name).suffix.lower() in SOURCE_EXTENSIONS


def verify_syntax(path: Path, lang: str) -> str:
    """校验单个文件的语法，返回 ``"ok" | "bad" | "unsupported"``。"""
    text = path.read_text(encoding="utf-8", errors="ignore")
    if lang == "Python":
        try:
            ast.parse(text)
            return "ok"
        except (SyntaxError, ValueError):
            return "bad"
    if lang == "JSON":
        try:
            json.loads(text)
            return "ok"
        except ValueError:
            return "bad"
    if lang == "TOML":
        try:
            tomllib.loads(text)
            return "ok"
        except (tomllib.TOMLDecodeError, ValueError):
            return "bad"
    if lang in _C_LIKE:
        return "ok" if _balanced(text) else "bad"
    return "unsupported"


def _balanced(text: str) -> bool:
    """启发式括号配平：跳过字符串与行/块注释后校验 ()[]{} 是否配平。

    这是轻量烟测而非真实解析：不处理语言特有的原始字符串、正则字面量等
    复杂词法，只用于捕捉明显的括号不匹配。
    """
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt == "/":  # 行注释
            i += 2
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":  # 块注释
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        if ch in "\"'`":  # 字符串（单/双/反引号）
            quote = ch
            i += 1
            while i < n and text[i] != quote:
                if text[i] == "\\" and i + 1 < n:
                    i += 2
                else:
                    i += 1
            i += 1
            continue
        if ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            if not stack or stack[-1] != pairs[ch]:
                return False
            stack.pop()
        i += 1
    return not stack
