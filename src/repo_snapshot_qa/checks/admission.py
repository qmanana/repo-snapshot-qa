"""M3 准入检查：提交数量、代码规模、可解析率与 README 基础完整性。

每一项都返回一个 CheckResult（是否通过、得分、明细），得分统一归一化到 0~1，
便于上层汇总与报告展示。阈值以模块常量集中管理，方便后续按需调整。
"""
from __future__ import annotations

import ast
from pathlib import Path

from ..models import CheckResult, CommitInfo
from ..util import count_non_blank_lines, find_readme, iter_python_files

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


def check_code_scale(repo_path: Path, min_loc: int = MIN_LOC) -> CheckResult:
    """代码规模：统计 Python 源文件数与有效代码行数。"""
    files = list(iter_python_files(repo_path))
    loc = sum(count_non_blank_lines(p) for p in files)
    passed = loc >= min_loc
    score = min(loc / min_loc, 1.0)
    return CheckResult(
        name="代码规模",
        passed=passed,
        score=score,
        details=[f"共 {len(files)} 个 Python 文件、{loc} 行有效代码，要求不少于 {min_loc} 行"],
    )


def check_parse_rate(repo_path: Path) -> CheckResult:
    """可解析率：用 ast 解析全部 Python 源文件，要求 100% 可解析。"""
    files = list(iter_python_files(repo_path))
    if not files:
        return CheckResult(name="可解析率", passed=False, score=0.0, details=["未发现 Python 源文件"])

    ok = 0
    failures: list[str] = []
    for path in files:
        try:
            ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            ok += 1
        except SyntaxError as exc:
            failures.append(f"{path.name}:{exc.lineno} {exc.msg}")

    rate = ok / len(files)
    passed = rate >= 1.0
    details = [f"{ok}/{len(files)} 个文件可解析，可解析率 {rate:.0%}"]
    details += failures[:5]
    return CheckResult(name="可解析率", passed=passed, score=rate, details=details)


def check_readme(repo_path: Path) -> CheckResult:
    """README 基础完整性：存在、内容足够、且具备必要的章节结构。"""
    readme = find_readme(repo_path)
    if readme is None:
        return CheckResult(name="README 完整性", passed=False, score=0.0, details=["未找到 README 文件"])

    text = readme.read_text(encoding="utf-8", errors="ignore")
    headings = [line for line in text.splitlines() if line.strip().startswith("#")]
    has_install = any(k in text for k in ("安装", "Install"))
    has_usage = any(k in text for k in ("使用", "Usage"))

    checks = [
        (len(text.strip()) >= MIN_README_CHARS, f"内容长度 {len(text.strip())} 字符，要求不少于 {MIN_README_CHARS}"),
        (len(headings) >= MIN_README_HEADINGS, f"标题数 {len(headings)}，要求不少于 {MIN_README_HEADINGS}"),
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
    repo_path: Path, commits: list[CommitInfo]
) -> list[CheckResult]:
    """执行全部准入检查，返回结果列表。"""
    return [
        check_commit_count(commits),
        check_code_scale(repo_path),
        check_parse_rate(repo_path),
        check_readme(repo_path),
    ]
