"""repo-snapshot-qa 的领域数据模型。

这些 dataclass 贯穿整个质检流水线，保证各阶段之间用统一的结构传递数据。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SnapshotManifest:
    """仓库固定快照的元信息。"""

    repo_url: str
    commit_sha: str
    branch: str
    tree_sha: str
    captured_at: str


@dataclass(frozen=True)
class CommitInfo:
    """单条提交的结构化信息，由 history 模块解析 git log 得到。"""

    sha: str
    author_name: str
    author_email: str
    date: str
    message: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    files: list[str] = field(default_factory=list)


@dataclass
class CheckResult:
    """一次质检的通用结果：是否通过、得分与明细说明。"""

    name: str
    passed: bool
    score: float
    details: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Milestone:
    """按业务开发顺序划分的一个里程碑，对应一段连续提交区间。"""

    title: str
    description: str
    start_commit: str
    end_commit: str
