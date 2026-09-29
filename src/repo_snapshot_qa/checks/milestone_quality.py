"""M5 Milestone 质量检查：聚合性、需求可验证性、代码覆盖与拆分粒度。

输入为里程碑定义与完整提交历史；每个维度都用可计算的启发式规则评估，
返回归一化到 0~1 的得分与明细。
"""
from __future__ import annotations

import re
from collections import Counter

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

_SCOPE_RE = re.compile(r"^\w+\(([^)]*)\):")


def _commits_in_range(
    commits: list[CommitInfo], milestone: Milestone
) -> list[CommitInfo]:
    """从倒序提交列表中截取里程碑区间（含两端）。"""
    index = {c.sha: i for i, c in enumerate(commits)}
    if milestone.start_commit not in index or milestone.end_commit not in index:
        return []
    lo, hi = sorted((index[milestone.start_commit], index[milestone.end_commit]))
    return commits[lo : hi + 1]


def _scope_of(commit: CommitInfo) -> str:
    """提取 Conventional Commits 中的 scope，如 feat(snapshot) -> snapshot。"""
    match = _SCOPE_RE.match(commit.message)
    return match.group(1) if match else ""


def check_cohesion(
    milestones: list[Milestone], commits: list[CommitInfo]
) -> CheckResult:
    """聚合性：里程碑内提交主题集中，且标题与说明完整。"""
    if not milestones:
        return CheckResult("聚合性", False, 0.0, ["未配置里程碑"])

    passing = 0
    detail_lines: list[str] = []
    for milestone in milestones:
        ms_commits = _commits_in_range(commits, milestone)
        desc_ok = bool(milestone.title.strip()) and len(milestone.description.strip()) >= MIN_DESC_CHARS
        if not ms_commits:
            detail_lines.append(f"{milestone.title or '(无标题)'}: 区间无提交")
            continue
        scopes = [s for s in (_scope_of(c) for c in ms_commits) if s]
        dominant = max(Counter(scopes).values(), default=0) / len(ms_commits) if scopes else 0.0
        ok = desc_ok and dominant >= COHESION_RATIO
        passing += int(ok)
        detail_lines.append(
            f"{milestone.title}: 主题集中度 {dominant:.0%}"
            f"（{'✓ 说明完整' if desc_ok else '✗ 说明不足'}）"
        )

    passed = passing == len(milestones)
    return CheckResult("聚合性", passed, passing / len(milestones), detail_lines)


def check_verifiability(
    milestones: list[Milestone], commits: list[CommitInfo]
) -> CheckResult:
    """需求可验证性：每个里程碑的说明应陈述一个可验证的目标。"""
    if not milestones:
        return CheckResult("需求可验证性", False, 0.0, ["未配置里程碑"])

    passing = 0
    detail_lines: list[str] = []
    for milestone in milestones:
        desc = milestone.description.strip()
        has_goal = any(k in desc for k in _GOAL_KEYWORDS)
        ok = len(desc) >= MIN_DESC_CHARS and has_goal
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
    milestones: list[Milestone], commits: list[CommitInfo]
) -> CheckResult:
    """拆分粒度：里程碑数量与单个里程碑包含的提交数应在合理区间。"""
    if not milestones:
        return CheckResult("拆分粒度", False, 0.0, ["未配置里程碑"])

    count_ok = MIN_MILESTONES <= len(milestones) <= MAX_MILESTONES
    sizes = [len(_commits_in_range(commits, m)) for m in milestones]
    size_ok = all(MIN_COMMITS_PER <= s <= MAX_COMMITS_PER for s in sizes)
    passed = count_ok and size_ok
    return CheckResult(
        "拆分粒度",
        passed,
        (int(count_ok) + int(size_ok)) / 2,
        [
            f"里程碑数 {len(milestones)}（要求 {MIN_MILESTONES}~{MAX_MILESTONES}）{'✓' if count_ok else '✗'}",
            f"各里程碑提交数 {sizes}（要求 {MIN_COMMITS_PER}~{MAX_COMMITS_PER}）{'✓' if size_ok else '✗'}",
        ],
    )


def run_milestone_quality_checks(
    milestones: list[Milestone], commits: list[CommitInfo]
) -> list[CheckResult]:
    """执行全部 Milestone 质量检查。"""
    return [
        check_cohesion(milestones, commits),
        check_verifiability(milestones, commits),
        check_coverage(milestones, commits),
        check_granularity(milestones, commits),
    ]
