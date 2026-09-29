"""命令行入口：串联快照采集与三阶段质检。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .checks import overall_passed
from .config import load_config
from .checks.admission import run_admission_checks
from .checks.milestone_quality import run_milestone_quality_checks
from .checks.repo_quality import run_repo_quality_checks
from .history import is_git_repo, parse_commit_history
from .models import Milestone
from .report import format_results, write_html_report, write_json_report
from .snapshot import capture_snapshot


def _load_milestones(path: str) -> list[Milestone]:
    """从 JSON 文件加载里程碑定义。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Milestone(**item) for item in data]


def cmd_snapshot(args: argparse.Namespace) -> int:
    """克隆仓库并固定到指定 commit，生成快照清单。"""
    _, manifest = capture_snapshot(
        args.url, Path(args.dest), ref=args.ref, commit_sha=args.commit, depth=args.depth
    )
    print(f"快照已生成：{manifest.commit_sha[:8]} @ {manifest.branch}")
    print(f"清单文件：{args.dest}/snapshot.json")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """对本地仓库按准入 → Repo → Milestone 顺序执行质检。"""
    repo_path = Path(args.repo)
    if not is_git_repo(repo_path):
        print(f"错误：{args.repo} 不是 git 仓库目录，无法执行质检。")
        return 1
    commits = parse_commit_history(repo_path)
    config = load_config(args.config)
    stages: dict[str, list] = {}

    admission = run_admission_checks(repo_path, commits, config=config.admission)
    stages["admission"] = admission
    print(format_results(admission, "准入检查"))
    if not overall_passed(admission):
        print("\n准入检查未通过，终止后续检查。")
        return 1

    repo_quality = run_repo_quality_checks(repo_path, commits, config=config.repo_quality)
    stages["repo_quality"] = repo_quality
    print("\n" + format_results(repo_quality, "Repo 质量检查"))
    if not overall_passed(repo_quality):
        print("\nRepo 质量检查未通过，终止后续检查。")
        return 1

    if args.milestones:
        milestones = _load_milestones(args.milestones)
        milestone_quality = run_milestone_quality_checks(
            milestones, commits, config=config.milestone_quality
        )
        stages["milestone_quality"] = milestone_quality
        print("\n" + format_results(milestone_quality, "Milestone 质量检查"))

    if args.json:
        out = write_json_report(Path(args.json), stages)
        print(f"\nJSON 报告已写入：{out}")
    if args.html:
        out = write_html_report(Path(args.html), stages)
        print(f"\nHTML 报告已写入：{out}")
    return 0


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

    p_check = sub.add_parser("check", help="对本地仓库执行三阶段质检")
    p_check.add_argument("repo", help="仓库路径")
    p_check.add_argument("--milestones", help="里程碑定义 JSON 文件")
    p_check.add_argument("--config", help="阈值配置 JSON 文件")
    p_check.add_argument("--json", help="输出 JSON 报告的文件路径")
    p_check.add_argument("--html", help="输出 HTML 报告的文件路径")
    p_check.set_defaults(func=cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
