"""质检报告：把各阶段 CheckResult 汇总为可读文本或 JSON。"""
from __future__ import annotations

import json
from pathlib import Path

from .models import CheckResult


def results_to_dict(results: list[CheckResult]) -> list[dict]:
    """把检查结果转为可序列化的字典列表。"""
    return [
        {
            "name": r.name,
            "passed": r.passed,
            "score": round(r.score, 3),
            "details": r.details,
        }
        for r in results
    ]


def format_results(results: list[CheckResult], title: str) -> str:
    """把一组检查结果格式化为多行文本。"""
    lines = [f"== {title} =="]
    for r in results:
        mark = "通过" if r.passed else "未通过"
        lines.append(f"[{mark}] {r.name}（得分 {r.score:.0%}）")
        for detail in r.details:
            lines.append(f"    - {detail}")
    return "\n".join(lines)


def render_report(
    admission: list[CheckResult],
    repo_quality: list[CheckResult] | None = None,
    milestone_quality: list[CheckResult] | None = None,
) -> str:
    """汇总三阶段结果为完整文本报告。"""
    parts = [format_results(admission, "准入检查")]
    if repo_quality is not None:
        parts.append(format_results(repo_quality, "Repo 质量检查"))
    if milestone_quality is not None:
        parts.append(format_results(milestone_quality, "Milestone 质量检查"))
    return "\n\n".join(parts)


def write_json_report(
    path: Path, stages: dict[str, list[CheckResult]]
) -> Path:
    """把各阶段结果写为 JSON 文件。"""
    payload = {name: results_to_dict(results) for name, results in stages.items()}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
