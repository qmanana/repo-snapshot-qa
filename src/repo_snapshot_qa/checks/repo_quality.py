"""M4 Repo 质量检查：功能子系统、README 与代码一致性、提交说明质量。"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

from ..models import CheckResult, CommitInfo
from ..util import find_package_root, find_readme

MIN_SUBSYSTEMS = 3
MIN_MESSAGE_QUALITY = 0.8

_CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|chore|docs|test|refactor|perf|style|build|ci|revert)"
    r"(\([^)]*\))?: .+$"
)


def detect_subsystems(repo_path: Path) -> list[str]:
    """识别功能子系统：源码包下的顶层模块与子包。"""
    root = find_package_root(repo_path)
    if root is None:
        return []
    subsystems: list[str] = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "__init__.py").exists():
            subsystems.append(child.name)
        elif child.suffix == ".py" and child.stem != "__init__":
            subsystems.append(child.stem)
    return subsystems


def check_subsystems(
    repo_path: Path, min_subsystems: int = MIN_SUBSYSTEMS
) -> CheckResult:
    """功能子系统：源码应有清晰的模块/子包划分。"""
    subsystems = detect_subsystems(repo_path)
    passed = len(subsystems) >= min_subsystems
    score = min(len(subsystems) / min_subsystems, 1.0)
    return CheckResult(
        name="功能子系统",
        passed=passed,
        score=score,
        details=[
            f"识别到 {len(subsystems)} 个子系统：{', '.join(subsystems) or '无'}",
            f"要求不少于 {min_subsystems} 个",
        ],
    )


def _read_pyproject(repo_path: Path) -> dict:
    path = repo_path / "pyproject.toml"
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return {}


def check_readme_consistency(repo_path: Path) -> CheckResult:
    """README 与代码一致性：README 中应出现包名与命令行入口。"""
    readme = find_readme(repo_path)
    if readme is None:
        return CheckResult(name="README 一致性", passed=False, score=0.0, details=["未找到 README 文件"])

    text = readme.read_text(encoding="utf-8", errors="ignore")
    project = _read_pyproject(repo_path).get("project", {})
    package_name = project.get("name", "")
    scripts = project.get("scripts", {})

    checks: list[tuple[bool, str]] = []
    if package_name:
        checks.append((package_name.lower() in text.lower(), f"包名 {package_name!r} 出现在 README 中"))
    else:
        checks.append((False, "pyproject.toml 缺少项目名"))

    if scripts:
        checks.append(
            (any(name in text for name in scripts), f"命令入口 {', '.join(scripts)} 出现在 README 中")
        )
    else:
        checks.append((False, "pyproject.toml 未定义命令入口"))

    passed_count = sum(1 for ok, _ in checks if ok)
    passed = passed_count == len(checks)
    details = [f"{'✓' if ok else '✗'} {msg}" for ok, msg in checks]
    return CheckResult(
        name="README 一致性",
        passed=passed,
        score=passed_count / len(checks),
        details=details,
    )


def check_commit_message_quality(
    commits: list[CommitInfo], min_ratio: float = MIN_MESSAGE_QUALITY
) -> CheckResult:
    """提交说明质量：应遵循 Conventional Commits 规范且说明明确。"""
    if not commits:
        return CheckResult(name="提交说明质量", passed=False, score=0.0, details=["无提交记录"])

    good = 0
    bad: list[str] = []
    for commit in commits:
        message = commit.message.strip()
        if _CONVENTIONAL_RE.match(message) and len(message) <= 100:
            good += 1
        else:
            bad.append(message[:60])

    ratio = good / len(commits)
    passed = ratio >= min_ratio
    details = [
        f"{good}/{len(commits)} 条提交说明符合规范（占比 {ratio:.0%}，要求 {min_ratio:.0%}）"
    ]
    if bad:
        details.append("不规范示例：" + "；".join(bad[:3]))
    return CheckResult(name="提交说明质量", passed=passed, score=ratio, details=details)


def run_repo_quality_checks(
    repo_path: Path, commits: list[CommitInfo]
) -> list[CheckResult]:
    """执行全部 Repo 质量检查。"""
    return [
        check_subsystems(repo_path),
        check_readme_consistency(repo_path),
        check_commit_message_quality(commits),
    ]
