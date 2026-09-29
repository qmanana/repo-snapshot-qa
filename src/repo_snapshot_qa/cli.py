"""命令行入口：串联快照采集与四阶段质检。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .checks import overall_passed
from .config import load_config
from .checks.admission import run_admission_checks
from .checks.health import run_health_checks
from .checks.milestone_quality import run_milestone_quality_checks
from .checks.repo_quality import run_repo_quality_checks
from .history import is_git_repo, parse_commit_history
from .models import Milestone
from .report import (
    render_html,
    render_text_report,
    stages_to_dict,
    summarize,
    write_html_report,
    write_json_report,
)
from .snapshot import capture_snapshot


def _load_milestones(path: str) -> list[Milestone]:
    """从 JSON 文件加载里程碑定义。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Milestone(**item) for item in data]


def _reconfigure_stdio() -> None:
    """让 stdout/stderr 以 UTF-8 输出。

    Windows 中文环境默认控制台/管道编码为 GBK，无法编码 `✓`/`✗` 等符号，
    会导致报告输出崩溃。统一重配为 UTF-8 可避免该问题（现代终端均按 UTF-8 解码）。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def _split_patterns(value: str | None) -> list[str] | None:
    """把逗号分隔的 glob 模式字符串解析为列表，空值返回 None。"""
    if not value:
        return None
    patterns = [p.strip() for p in value.split(",") if p.strip()]
    return patterns or None


def cmd_snapshot(args: argparse.Namespace) -> int:
    """克隆仓库并固定到指定 commit，生成快照清单。"""
    _, manifest = capture_snapshot(
        args.url, Path(args.dest), ref=args.ref, commit_sha=args.commit, depth=args.depth
    )
    print(f"快照已生成：{manifest.commit_sha[:8]} @ {manifest.branch}")
    print(f"清单文件：{args.dest}/snapshot.json")
    return 0


def _emit(args: argparse.Namespace, stages: dict[str, list]) -> None:
    """按 --format 输出报告到 stdout。"""
    if args.format == "json":
        print(json.dumps(stages_to_dict(stages), ensure_ascii=False, indent=2))
    elif args.format == "html":
        print(render_html(stages))
    else:
        print(render_text_report(stages))
        print()
        print(summarize(stages))


def cmd_check(args: argparse.Namespace) -> int:
    """对本地仓库按准入 → Repo → 健康度 → Milestone 顺序执行质检。"""
    repo_path = Path(args.repo)
    if not is_git_repo(repo_path):
        print(f"错误：{args.repo} 不是 git 仓库目录，无法执行质检。")
        return 1

    commits = parse_commit_history(repo_path, max_commits=args.max_commits)
    config = load_config(args.config)
    include = _split_patterns(args.include)
    exclude = _split_patterns(args.exclude)
    stages: dict[str, list] = {}

    admission = run_admission_checks(
        repo_path, commits, config=config.admission, include=include, exclude=exclude
    )
    stages["admission"] = admission
    if not args.no_fail_fast and not overall_passed(admission):
        _emit(args, stages)
        print("\n准入检查未通过，终止后续检查（可用 --no-fail-fast 继续）。")
        return 1

    repo_quality = run_repo_quality_checks(repo_path, commits, config=config.repo_quality)
    stages["repo_quality"] = repo_quality
    if not args.no_fail_fast and not overall_passed(repo_quality):
        _emit(args, stages)
        print("\nRepo 质量检查未通过，终止后续检查（可用 --no-fail-fast 继续）。")
        return 1

    stages["health"] = run_health_checks(
        repo_path, commits, config=config.health, include=include, exclude=exclude
    )

    if args.milestones:
        milestones = _load_milestones(args.milestones)
        stages["milestone_quality"] = run_milestone_quality_checks(
            milestones, commits, config=config.milestone_quality
        )

    _emit(args, stages)

    if args.json:
        out = write_json_report(Path(args.json), stages)
        print(f"JSON 报告已写入：{out}")
    if args.html:
        out = write_html_report(Path(args.html), stages)
        print(f"HTML 报告已写入：{out}")

    return 0 if all(overall_passed(results) for results in stages.values()) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-snapshot-qa",
        description="采集 GitHub 仓库固定快照，并对仓库与 Milestone 执行自动质检",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_snap = sub.add_parser("snapshot", help="克隆仓库并固定 commit，生成快照清单")
    p_snap.add_argument("url", help="仓库地址")
    p_snap.add_argument("-d", "--dest", required=True, help="克隆目标目录")
    p_snap.add_argument("-r", "--ref", help="分支或标签")
    p_snap.add_argument("-c", "--commit", help="固定到的 commit sha")
    p_snap.add_argument("--depth", type=int, help="浅克隆深度（仅拉取最近 N 条历史）")
    p_snap.set_defaults(func=cmd_snapshot)

    p_check = sub.add_parser("check", help="对本地仓库执行四阶段质检")
    p_check.add_argument("repo", help="仓库路径")
    p_check.add_argument("--milestones", help="里程碑定义 JSON 文件")
    p_check.add_argument("--config", help="阈值配置 JSON 文件")
    p_check.add_argument("--json", help="输出 JSON 报告的文件路径")
    p_check.add_argument("--html", help="输出 HTML 报告的文件路径")
    p_check.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="某阶段未通过时仍继续执行后续检查",
    )
    p_check.add_argument(
        "--include", help="仅扫描匹配的文件（逗号分隔的 glob 模式）"
    )
    p_check.add_argument(
        "--exclude", help="跳过匹配的文件（逗号分隔的 glob 模式）"
    )
    p_check.add_argument(
        "--format",
        choices=["text", "json", "html"],
        default="text",
        help="stdout 报告输出格式（默认 text）",
    )
    p_check.add_argument(
        "--max-commits", type=int, help="只解析最近 N 条提交（默认全部）"
    )
    p_check.set_defaults(func=cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    _reconfigure_stdio()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
