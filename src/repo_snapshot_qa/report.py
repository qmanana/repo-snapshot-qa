"""质检报告：把各阶段 CheckResult 汇总为可读文本、JSON 或自包含 HTML。"""
from __future__ import annotations

import html
import json
from pathlib import Path

from .models import CheckResult

STAGE_TITLES = {
    "admission": "准入检查",
    "repo_quality": "Repo 质量检查",
    "health": "仓库健康度",
    "milestone_quality": "Milestone 质量检查",
}


def stage_title(name: str) -> str:
    """返回阶段的中文标题，未识别的阶段名原样返回。"""
    return STAGE_TITLES.get(name, name)


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


def _summary_dict(stages: dict[str, list[CheckResult]]) -> dict:
    """汇总各阶段通过情况为字典。"""
    total = sum(len(results) for results in stages.values())
    passed = sum(1 for results in stages.values() for r in results if r.passed)
    failed = [
        {"stage": name, "name": r.name}
        for name, results in stages.items()
        for r in results
        if not r.passed
    ]
    return {"total": total, "passed": passed, "failed": failed}


def stages_to_dict(stages: dict[str, list[CheckResult]]) -> dict:
    """把各阶段结果转为字典，附带顶层 summary 汇总块。"""
    payload = {name: results_to_dict(results) for name, results in stages.items()}
    payload["summary"] = _summary_dict(stages)
    return payload


def format_results(results: list[CheckResult], title: str) -> str:
    """把一组检查结果格式化为多行文本。"""
    lines = [f"== {title} =="]
    for r in results:
        mark = "通过" if r.passed else "未通过"
        lines.append(f"[{mark}] {r.name}（得分 {r.score:.0%}）")
        for detail in r.details:
            lines.append(f"    - {detail}")
    return "\n".join(lines)


def render_text_report(stages: dict[str, list[CheckResult]]) -> str:
    """汇总各阶段为完整文本报告。"""
    return "\n\n".join(
        format_results(results, stage_title(name)) for name, results in stages.items()
    )


def summarize(stages: dict[str, list[CheckResult]]) -> str:
    """一行汇总：总通过数与未通过项清单。"""
    summary = _summary_dict(stages)
    parts = [f"共 {summary['passed']}/{summary['total']} 项通过"]
    if summary["failed"]:
        failed_names = "、".join(
            f"{stage_title(item['stage'])}·{item['name']}" for item in summary["failed"]
        )
        parts.append("未通过：" + failed_names)
    return "；".join(parts)


def write_json_report(
    path: Path, stages: dict[str, list[CheckResult]]
) -> Path:
    """把各阶段结果（含 summary）写为 JSON 文件。"""
    path.write_text(
        json.dumps(stages_to_dict(stages), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


_CSS = """<style>
body { font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
       max-width: 860px; margin: 2rem auto; padding: 0 1rem; color: #1f2328; line-height: 1.6; }
h1 { border-bottom: 2px solid #d0d7de; padding-bottom: .4rem; }
h2 { margin-top: 1.6rem; }
ul { padding-left: 1.2rem; }
.summary { border: 1px solid #d0d7de; border-radius: 8px; padding: 1rem 1.2rem; margin: 1rem 0; }
.summary.ok { background: #f6ffed; border-color: #b7eb8f; }
.summary.bad { background: #fff1f0; border-color: #ffa39e; }
.badges { margin-top: .6rem; }
.badge { display: inline-block; padding: .15rem .6rem; border-radius: 12px; font-size: .85rem; margin-right: .5rem; }
.badge.ok { background: #d9f99d; }
.badge.bad { background: #ffd6d2; }
li.ok { color: #1a7f37; }
li.bad { color: #cf222e; }
li ul { color: #1f2328; }
</style>"""


def render_html(stages: dict[str, list[CheckResult]]) -> str:
    """把各阶段结果渲染为自包含的单页 HTML 报告（含汇总块与样式）。"""
    esc = html.escape
    summary = _summary_dict(stages)
    overall_ok = summary["passed"] == summary["total"]

    parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>repo-snapshot-qa 质检报告</title>",
        _CSS,
        "</head><body>",
        "<h1>repo-snapshot-qa 质检报告</h1>",
        f"<div class='summary {'ok' if overall_ok else 'bad'}'>",
        f"<h2>总览：{summary['passed']}/{summary['total']} 项通过 · {esc('全部通过' if overall_ok else '存在未通过项')}</h2>",
        "<div class='badges'>",
    ]
    for name, results in stages.items():
        stage_passed = sum(1 for r in results if r.passed)
        cls = "ok" if stage_passed == len(results) else "bad"
        parts.append(
            f"<span class='badge {cls}'>{esc(stage_title(name))} {stage_passed}/{len(results)}</span>"
        )
    parts.append("</div></div>")

    for name, results in stages.items():
        parts.append(f"<h2>{esc(stage_title(name))}</h2><ul>")
        for result in results:
            cls = "ok" if result.passed else "bad"
            mark = "通过" if result.passed else "未通过"
            detail_items = "".join(f"<li>{esc(d)}</li>" for d in result.details)
            parts.append(
                f"<li class='{cls}'><b>{esc(result.name)}</b>：{mark}（得分 {result.score:.0%}）"
                f"<ul>{detail_items}</ul></li>"
            )
        parts.append("</ul>")

    parts.append("</body></html>")
    return "\n".join(parts)


def write_html_report(
    path: Path, stages: dict[str, list[CheckResult]]
) -> Path:
    """把各阶段结果写为 HTML 文件。"""
    path.write_text(render_html(stages), encoding="utf-8")
    return path
