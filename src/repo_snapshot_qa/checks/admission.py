"""M3 准入检查：提交数量、代码规模、可解析率与 README 基础完整性。

每一项都返回一个 CheckResult（是否通过、得分、明细），得分统一归一化到 0~1，
便于上层汇总与报告展示。阈值以模块常量集中管理，方便后续按需调整。
"""
from __future__ import annotations

from pathlib import Path

from ..config import AdmissionConfig
from ..languages import classify, verify_syntax
from ..models import CheckResult, CommitInfo
from ..util import count_non_blank_lines, find_readme, iter_code_files

MIN_COMMITS = 10
MIN_LOC = 200
MIN_README_CHARS = 200
MIN_README_HEADINGS = 3


def check_commit_count(commits: list[CommitInfo], min_commits: int = MIN_COMMITS) -> CheckResult:
    """提交数量：仓库应有足够多的提交以体现连续开发过程。"""
    n = len(commits)
    passed = n >= min_commits
    score = min(n / min_commits, 1.0)
    return CheckResult(
        name="提交数量",
        passed=passed,
        score=score,
        details=[f"共 {n} 条提交，要求不少于 {min_commits} 条"],
    )


def check_code_scale(
    repo_path: Path,
    min_loc: int = MIN_LOC,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> CheckResult:
    """代码规模：统计多语言代码文件数与有效代码行数。"""
    files = list(iter_code_files(repo_path, include=include, exclude=exclude))
    loc = sum(count_non_blank_lines(p) for p in files)
    by_lang: dict[str, int] = {}
    for path in files:
        lang = classify(path) or "其他"
        by_lang[lang] = by_lang.get(lang, 0) + 1
    lang_summary = "、".join(f"{lang} {n} 个" for lang, n in sorted(by_lang.items()))
    passed = loc >= min_loc
    score = min(loc / min_loc, 1.0)
    return CheckResult(
        name="代码规模",
        passed=passed,
        score=score,
        details=[
            f"共 {len(files)} 个代码文件、{loc} 行有效代码，要求不少于 {min_loc} 行",
            f"按语言：{lang_summary or '无'}",
        ],
    )


def check_parse_rate(
    repo_path: Path,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> CheckResult:
    """可解析率：对全部代码文件做语法校验，要求可校验文件 100% 通过。"""
    files = list(iter_code_files(repo_path, include=include, exclude=exclude))
    if not files:
        return CheckResult("可解析率", passed=False, score=0.0, details=["未发现代码文件"])

    ok = 0
    bad = 0
    unsupported = 0
    failures: list[str] = []
    unsupported_langs: set[str] = set()
    for path in files:
        lang = classify(path) or "未知"
        verdict = verify_syntax(path, lang)
        if verdict == "ok":
            ok += 1
        elif verdict == "bad":
            bad += 1
            failures.append(f"{path.name}（{lang}）")
        else:
            unsupported += 1
            unsupported_langs.add(lang)

    checkable = ok + bad
    rate = ok / checkable if checkable else 0.0
    passed = checkable > 0 and bad == 0
    details = [f"{ok}/{checkable} 个文件通过语法校验，可解析率 {rate:.0%}"]
    if unsupported:
        details.append(
            f"{unsupported} 个文件的语言暂不支持语法校验"
            f"（{', '.join(sorted(unsupported_langs))}），未计入可解析率"
        )
    details += failures[:5]
    return CheckResult("可解析率", passed=passed, score=rate, details=details)


def check_readme(
    repo_path: Path,
    min_chars: int = MIN_README_CHARS,
    min_headings: int = MIN_README_HEADINGS,
) -> CheckResult:
    """README 基础完整性：存在、内容足够、且具备必要的章节结构。"""
    readme = find_readme(repo_path)
    if readme is None:
        return CheckResult(name="README 完整性", passed=False, score=0.0, details=["未找到 README 文件"])

    text = readme.read_text(encoding="utf-8", errors="ignore")
    headings = [line for line in text.splitlines() if line.strip().startswith("#")]
    has_install = any(k in text for k in ("安装", "Install"))
    has_usage = any(k in text for k in ("使用", "Usage"))

    checks = [
        (len(text.strip()) >= min_chars, f"内容长度 {len(text.strip())} 字符，要求不少于 {min_chars}"),
        (len(headings) >= min_headings, f"标题数 {len(headings)}，要求不少于 {min_headings}"),
        (has_install, "包含安装说明"),
        (has_usage, "包含使用说明"),
    ]
    passed_count = sum(1 for ok, _ in checks if ok)
    passed = passed_count == len(checks)
    details = [f"{'✓' if ok else '✗'} {msg}" for ok, msg in checks]
    return CheckResult(
        name="README 完整性",
        passed=passed,
        score=passed_count / len(checks),
        details=details,
    )


def run_admission_checks(
    repo_path: Path,
    commits: list[CommitInfo],
    config: AdmissionConfig = AdmissionConfig(),
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[CheckResult]:
    """执行全部准入检查，返回结果列表。"""
    return [
        check_commit_count(commits, min_commits=config.min_commits),
        check_code_scale(repo_path, min_loc=config.min_loc, include=include, exclude=exclude),
        check_parse_rate(repo_path, include=include, exclude=exclude),
        check_readme(
            repo_path,
            min_chars=config.min_readme_chars,
            min_headings=config.min_readme_headings,
        ),
    ]
