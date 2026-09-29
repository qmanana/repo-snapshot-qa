"""仓库健康度检查：测试覆盖、遗留标记、贡献者分布、改动热点与超大文件。

本阶段提供准入/Repo/Milestone 之外的持续性维护信号，全部基于已有
CommitInfo 列表与文件扫描计算，无第三方依赖。
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..config import HealthConfig
from ..languages import CONFIG_LANGS, classify
from ..models import CheckResult, CommitInfo
from ..util import count_non_blank_lines, is_test_file, iter_code_files

MIN_TEST_RATIO = 0.05
MAX_TODO_PER_FILE = 10
MIN_AUTHORS = 2
BUS_FACTOR_MIN = 2
HOTSPOT_TOP_N = 5
MAX_FILE_LOC = 500

_TODO_MARKERS = ("TODO", "FIXME", "HACK", "XXX")
_COMMENT_MARKERS = ("#", "//", "/*")


def _count_markers(text: str) -> int:
    """统计注释里的遗留标记，忽略字符串字面量与普通代码行。"""
    total = 0
    in_block = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if in_block:
            total += sum(line.count(m) for m in _TODO_MARKERS)
            if "*/" in line:
                in_block = False
            continue
        if stripped.startswith(_COMMENT_MARKERS):
            total += sum(line.count(m) for m in _TODO_MARKERS)
            if stripped.startswith("/*") and "*/" not in line:
                in_block = True
            continue
        for start in _COMMENT_MARKERS:
            idx = line.find(start)
            if idx != -1:
                tail = line[idx:]
                total += sum(tail.count(m) for m in _TODO_MARKERS)
                if start == "/*" and "*/" not in tail:
                    in_block = True
                break
    return total


def check_test_ratio(
    repo_path: Path,
    min_test_ratio: float = MIN_TEST_RATIO,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> CheckResult:
    """测试覆盖比：测试文件数 / 源码文件数应达到最低比例。"""
    files = list(iter_code_files(repo_path, include=include, exclude=exclude))
    tests = [f for f in files if is_test_file(f)]
    sources = [f for f in files if not is_test_file(f)]
    if not sources:
        return CheckResult("测试覆盖比", False, 0.0, ["未发现源码文件"])
    ratio = len(tests) / len(sources)
    passed = ratio >= min_test_ratio
    score = min(ratio / min_test_ratio, 1.0) if min_test_ratio else 1.0
    return CheckResult(
        "测试覆盖比",
        passed,
        score,
        [f"测试文件 {len(tests)} 个、源码文件 {len(sources)} 个，比例 {ratio:.0%}（要求不低于 {min_test_ratio:.0%}）"],
    )


def check_todo_density(
    repo_path: Path,
    max_todo_per_file: int = MAX_TODO_PER_FILE,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> CheckResult:
    """遗留标记：源码文件内的 TODO/FIXME/HACK/XXX 数量应低于单文件上限。"""
    files = [
        f for f in iter_code_files(repo_path, include=include, exclude=exclude)
        if not is_test_file(f) and classify(f) not in CONFIG_LANGS
    ]
    offenders: list[str] = []
    total = 0
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        n = _count_markers(text)
        total += n
        if n > max_todo_per_file:
            offenders.append(f"{path.relative_to(repo_path).as_posix()}：{n} 处")
    passed = not offenders
    details = [f"共 {total} 处遗留标记，单文件上限 {max_todo_per_file}"]
    details += [f"超过上限：{o}" for o in offenders[:5]]
    return CheckResult("遗留标记", passed, 1.0 if passed else 0.0, details)


def check_bus_factor(
    commits: list[CommitInfo],
    min_authors: int = MIN_AUTHORS,
    bus_factor_min: int = BUS_FACTOR_MIN,
) -> CheckResult:
    """贡献者分布：贡献者数量与 bus factor（覆盖 50% 提交所需的最少作者数）。"""
    if not commits:
        return CheckResult("贡献者分布", False, 0.0, ["无提交记录"])
    counter = Counter(c.author_name for c in commits)
    authors = len(counter)
    total = len(commits)
    acc = 0
    bus = 0
    for count in sorted(counter.values(), reverse=True):
        acc += count
        bus += 1
        if acc >= total * 0.5:
            break
    top = "、".join(f"{name}（{count} 条）" for name, count in counter.most_common(3))
    passed = authors >= min_authors and bus >= bus_factor_min
    score = (min(authors / min_authors, 1.0) + min(bus / bus_factor_min, 1.0)) / 2
    return CheckResult(
        "贡献者分布",
        passed,
        score,
        [
            f"共 {authors} 位贡献者（要求不少于 {min_authors}），bus factor {bus}（覆盖 50% 提交需 {bus} 人）",
            f"主要贡献者：{top}",
        ],
    )


def check_churn_hotspots(
    commits: list[CommitInfo], top_n: int = HOTSPOT_TOP_N
) -> CheckResult:
    """改动热点：被最多提交触及的文件，帮助定位不稳定模块（仅展示，不判通过）。"""
    if not commits:
        return CheckResult("改动热点", False, 0.0, ["无提交记录"])
    touches: Counter = Counter()
    for commit in commits:
        for path in commit.files:
            touches[path] += 1
    top = touches.most_common(top_n)
    details = [f"{path}：被 {count} 个提交改动" for path, count in top] or ["无文件改动记录"]
    return CheckResult("改动热点", True, 1.0, details)


def check_large_files(
    repo_path: Path,
    max_file_loc: int = MAX_FILE_LOC,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> CheckResult:
    """超大文件：源码文件行数超过上限的数量应尽量少。"""
    files = [
        f for f in iter_code_files(repo_path, include=include, exclude=exclude)
        if not is_test_file(f)
    ]
    if not files:
        return CheckResult("超大文件", False, 0.0, ["未发现源码文件"])
    oversized: list[tuple[Path, int]] = []
    for path in files:
        loc = count_non_blank_lines(path)
        if loc > max_file_loc:
            oversized.append((path, loc))
    oversized.sort(key=lambda item: -item[1])
    passed = not oversized
    details = [f"扫描 {len(files)} 个源码文件，单文件上限 {max_file_loc} 行"]
    details += [
        f"{path.relative_to(repo_path).as_posix()}：{loc} 行" for path, loc in oversized[:5]
    ]
    return CheckResult("超大文件", passed, 1.0 if passed else 0.0, details)


def run_health_checks(
    repo_path: Path,
    commits: list[CommitInfo],
    config: HealthConfig = HealthConfig(),
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[CheckResult]:
    """执行全部仓库健康度检查。"""
    return [
        check_test_ratio(repo_path, min_test_ratio=config.min_test_ratio, include=include, exclude=exclude),
        check_todo_density(repo_path, max_todo_per_file=config.max_todo_per_file, include=include, exclude=exclude),
        check_bus_factor(commits, min_authors=config.min_authors, bus_factor_min=config.bus_factor_min),
        check_churn_hotspots(commits, top_n=config.hotspot_top_n),
        check_large_files(repo_path, max_file_loc=config.max_file_loc, include=include, exclude=exclude),
    ]
