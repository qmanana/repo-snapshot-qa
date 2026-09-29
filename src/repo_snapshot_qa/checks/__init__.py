"""质检阶段子包：准入检查、Repo 质量检查、Milestone 质量检查。"""
from __future__ import annotations

from ..models import CheckResult


def overall_passed(results: list[CheckResult]) -> bool:
    """所有检查项均通过才视为该阶段通过。"""
    return all(r.passed for r in results)
