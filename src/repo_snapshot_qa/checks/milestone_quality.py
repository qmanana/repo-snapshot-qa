"""M5 Milestone 质量检查：聚合性、需求可验证性、代码覆盖与拆分粒度。

输入为里程碑定义与完整提交历史；每个维度都用可计算的启发式规则评估，
返回归一化到 0~1 的得分与明细。
"""
from __future__ import annotations

from collections import Counter

from ..config import MilestoneQualityConfig
from ..models import CheckResult, CommitInfo, Milestone

MIN_DESC_CHARS = 8
MIN_MILESTONES = 3
MAX_MILESTONES = 10
MIN_COMMITS_PER = 2
MAX_COMMITS_PER = 50
COHESION_RATIO = 0.5

_GOAL_KEYWORDS = (
    "实现", "支持", "提供", "输出", "解析", "检查", "生成", "采集",
    "报告", "识别", "完成", "构建", "划分", "克隆",
)

def _commits_in_range(
    commits: list[CommitInfo], milestone: Milestone
) -> list[CommitInfo]:
    """从倒序提交列表中截取里程碑区间（含两端）。"""
    index = {c.sha: i for i, c in enumerate(commits)}
    if milestone.start_commit not in index or milestone.end_commit not in index:
        return []
    lo, hi = sorted((index[milestone.start_commit], index[milestone.end_commit]))
    return commits[lo : hi + 1]


def _file_subsystem(path: str) -> str:
    """把文件路径归一到它所属的源码子系统。

    src/repo_snapshot_qa/checks/admission.py -> checks
    src/repo_snapshot_qa/snapshot.py          -> snapshot
    tests/test_snapshot.py                    -> test_snapshot
    """
    parts = path.replace("\\", "/").split("/")
    if "src" in parts:
        idx = parts.index("src")
        if idx + 2 < len(parts):
            return parts[idx + 2].removesuffix(".py")
        if idx + 1 < len(parts):
            return parts[idx + 1].removesuffix(".py")
    if "tests" in parts:
        idx = parts.index("tests")
        if idx + 1 < len(parts):
            return parts[idx + 1].removesuffix(".py")
    return (parts[-1] or "").removesuffix(".py")


_SOURCE_EXTENSIONS = (".py", ".java", ".js", ".ts", ".go", ".rs", ".c", ".cpp", ".h")


def _subsystem_counts(commits: list[CommitInfo]) -> Counter:
    """统计一批提交触及的各源码子系统次数（忽略文档与配置类文件）。"""
    counter: Counter = Counter()
    for commit in commits:
        for path in commit.files:
            name = path.rsplit("/", 1)[-1]
            if name == "__init__.py" or not name.endswith(_SOURCE_EXTENSIONS):
                continue
            counter[_file_subsystem(path)] += 1
    return counter


def check_cohesion(
    milestones: list[Milestone],
    commits: list[CommitInfo],
    min_desc_chars: int = MIN_DESC_CHARS,
    cohesion_ratio: float = COHESION_RATIO,
) -> CheckResult:
    """聚合性：里程碑内提交集中在同一源码子系统，且标题与说明完整。"""
    if not milestones:
        return CheckResult("聚合性", False, 0.0, ["未配置里程碑"])

    passing = 0
    detail_lines: list[str] = []
    for milestone in milestones:
        ms_commits = _commits_in_range(commits, milestone)
        desc_ok = bool(milestone.title.strip()) and len(milestone.description.strip()) >= min_desc_chars
        if not ms_commits:
            detail_lines.append(f"{milestone.title or '(无标题)'}: 区间无提交")
            continue
        counter = _subsystem_counts(ms_commits)
        total = sum(counter.values())
        dominant = max(counter.values(), default=0) / total if total else 0.0
        ok = desc_ok and dominant >= cohesion_ratio
        passing += int(ok)
        detail_lines.append(
            f"{milestone.title}: 文件主题集中度 {dominant:.0%}"
            f"（{'✓ 说明完整' if desc_ok else '✗ 说明不足'}）"
        )

    passed = passing == len(milestones)
    return CheckResult("聚合性", passed, passing / len(milestones), detail_lines)


def check_verifiability(
    milestones: list[Milestone],
    commits: list[CommitInfo],
    min_desc_chars: int = MIN_DESC_CHARS,
) -> CheckResult:
    """需求可验证性：每个里程碑的说明应陈述一个可验证的目标。"""
    if not milestones:
        return CheckResult("需求可验证性", False, 0.0, ["未配置里程碑"])

    passing = 0
    detail_lines: list[str] = []
    for milestone in milestones:
        desc = milestone.description.strip()
        has_goal = any(k in desc for k in _GOAL_KEYWORDS)
        ok = len(desc) >= min_desc_chars and has_goal
        passing += int(ok)
        detail_lines.append(
            f"{milestone.title}: {'✓' if ok else '✗'} 说明 {len(desc)} 字符，"
            f"可验证目标{'存在' if has_goal else '缺失'}"
        )

    passed = passing == len(milestones)
    return CheckResult("需求可验证性", passed, passing / len(milestones), detail_lines)


def check_coverage(
    milestones: list[Milestone], commits: list[CommitInfo]
) -> CheckResult:
    """代码覆盖：里程碑应完整覆盖全部提交，且区间之间不重叠。"""
    if not milestones:
        return CheckResult("代码覆盖", False, 0.0, ["未配置里程碑"])
    all_shas = [c.sha for c in commits]
    if not all_shas:
        return CheckResult("代码覆盖", False, 0.0, ["无提交记录"])

    covered = [c.sha for m in milestones for c in _commits_in_range(commits, m)]
    unique = set(covered)
    overlap = len(covered) - len(unique)
    missing = len(set(all_shas) - unique)
    score = max(0.0, (len(unique) - overlap) / len(all_shas))
    passed = missing == 0 and overlap == 0
    return CheckResult(
        "代码覆盖",
        passed,
        score,
        [f"覆盖 {len(unique)}/{len(all_shas)} 条提交", f"遗漏 {missing} 条、重叠 {overlap} 条"],
    )


def check_granularity(
    milestones: list[Milestone],
    commits: list[CommitInfo],
    min_milestones: int = MIN_MILESTONES,
    max_milestones: int = MAX_MILESTONES,
    min_commits_per: int = MIN_COMMITS_PER,
    max_commits_per: int = MAX_COMMITS_PER,
) -> CheckResult:
    """拆分粒度：里程碑数量与单个里程碑包含的提交数应在合理区间。"""
    if not milestones:
        return CheckResult("拆分粒度", False, 0.0, ["未配置里程碑"])

    count_ok = min_milestones <= len(milestones) <= max_milestones
    sizes = [len(_commits_in_range(commits, m)) for m in milestones]
    size_ok = all(min_commits_per <= s <= max_commits_per for s in sizes)
    passed = count_ok and size_ok
    return CheckResult(
        "拆分粒度",
        passed,
        (int(count_ok) + int(size_ok)) / 2,
        [
            f"里程碑数 {len(milestones)}（要求 {min_milestones}~{max_milestones}）{'✓' if count_ok else '✗'}",
            f"各里程碑提交数 {sizes}（要求 {min_commits_per}~{max_commits_per}）{'✓' if size_ok else '✗'}",
        ],
    )


def run_milestone_quality_checks(
    milestones: list[Milestone],
    commits: list[CommitInfo],
    config: MilestoneQualityConfig = MilestoneQualityConfig(),
) -> list[CheckResult]:
    """执行全部 Milestone 质量检查。"""
    return [
        check_cohesion(
            milestones,
            commits,
            min_desc_chars=config.min_desc_chars,
            cohesion_ratio=config.cohesion_ratio,
        ),
        check_verifiability(milestones, commits, min_desc_chars=config.min_desc_chars),
        check_coverage(milestones, commits),
        check_granularity(
            milestones,
            commits,
            min_milestones=config.min_milestones,
            max_milestones=config.max_milestones,
            min_commits_per=config.min_commits_per,
            max_commits_per=config.max_commits_per,
        ),
    ]
