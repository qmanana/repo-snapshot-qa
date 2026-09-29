"""milestone_quality（Milestone 质量检查）模块的单元测试。"""
from __future__ import annotations

import unittest

from repo_snapshot_qa.checks import overall_passed
from repo_snapshot_qa.checks.milestone_quality import (
    check_cohesion,
    check_coverage,
    check_granularity,
    check_verifiability,
    run_milestone_quality_checks,
)
from repo_snapshot_qa.models import CommitInfo, Milestone


def _commit(sha: str, message: str, files: list[str] | None = None) -> CommitInfo:
    return CommitInfo(
        sha=sha,
        author_name="Test",
        author_email="test@example.com",
        date="2026-01-01T00:00:00+00:00",
        message=message,
        files=files or [],
    )


def _history() -> list[CommitInfo]:
    """9 条提交，倒序（最新在前）：c8..c0，按子系统 a/b/c 分成三段。"""
    modules = {0: "a", 1: "a", 2: "a", 3: "b", 4: "b", 5: "b", 6: "c", 7: "c", 8: "c"}
    commits = []
    for i in range(8, -1, -1):
        commits.append(_commit(f"c{i}", f"feat({modules[i]}): 任务 {i}", files=[f"src/pkg/module_{modules[i]}.py"]))
    return commits


def _milestones() -> list[Milestone]:
    return [
        Milestone("里程碑一", "实现模块 a 的基础能力", start_commit="c0", end_commit="c2"),
        Milestone("里程碑二", "实现模块 b 的基础能力", start_commit="c3", end_commit="c5"),
        Milestone("里程碑三", "实现模块 c 的基础能力", start_commit="c6", end_commit="c8"),
    ]


class MilestoneQualityTest(unittest.TestCase):
    def test_all_checks_pass_for_well_partitioned(self) -> None:
        results = run_milestone_quality_checks(_milestones(), _history())
        self.assertEqual(len(results), 4)
        self.assertTrue(overall_passed(results))

    def test_cohesion(self) -> None:
        self.assertTrue(check_cohesion(_milestones(), _history()).passed)
        # 说明缺失会导致聚合性不通过。
        bad = [
            Milestone("m1", "太短", start_commit="c0", end_commit="c2"),
            Milestone("m2", "太短", start_commit="c3", end_commit="c5"),
            Milestone("m3", "太短", start_commit="c6", end_commit="c8"),
        ]
        self.assertFalse(check_cohesion(bad, _history()).passed)

    def test_cohesion_detects_mixed_subsystems(self) -> None:
        # 一个里程碑横跨 a/b/c 三个子系统，文件主题集中度 1/3，低于阈值，聚合性不通过。
        mixed = [
            Milestone("跨模块收尾", "实现三个模块的整体收尾工作", start_commit="c0", end_commit="c8"),
        ]
        self.assertFalse(check_cohesion(mixed, _history()).passed)

    def test_verifiability(self) -> None:
        self.assertTrue(check_verifiability(_milestones(), _history()).passed)

    def test_coverage_detects_gap(self) -> None:
        milestones = _milestones()[:-1]  # 去掉最后一段，造成遗漏。
        self.assertFalse(check_coverage(milestones, _history()).passed)

    def test_coverage_detects_overlap(self) -> None:
        milestones = _milestones()
        milestones[1] = Milestone(
            milestones[1].title, milestones[1].description, start_commit="c3", end_commit="c6"
        )
        self.assertFalse(check_coverage(milestones, _history()).passed)

    def test_granularity(self) -> None:
        self.assertTrue(check_granularity(_milestones(), _history()).passed)
        self.assertFalse(check_granularity(_milestones()[:2], _history()).passed)


if __name__ == "__main__":
    unittest.main()
