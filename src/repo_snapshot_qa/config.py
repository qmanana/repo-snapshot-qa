"""质检阈值配置：集中管理各阶段阈值，支持从 JSON 文件覆盖默认值。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AdmissionConfig:
    min_commits: int = 10
    min_loc: int = 200
    min_readme_chars: int = 200
    min_readme_headings: int = 3


@dataclass
class RepoQualityConfig:
    min_subsystems: int = 3
    min_message_quality: float = 0.8


@dataclass
class MilestoneQualityConfig:
    min_desc_chars: int = 8
    min_milestones: int = 3
    max_milestones: int = 10
    min_commits_per: int = 2
    max_commits_per: int = 50
    cohesion_ratio: float = 0.5


@dataclass
class Config:
    """三阶段质检的完整配置。"""

    admission: AdmissionConfig = field(default_factory=AdmissionConfig)
    repo_quality: RepoQualityConfig = field(default_factory=RepoQualityConfig)
    milestone_quality: MilestoneQualityConfig = field(default_factory=MilestoneQualityConfig)


DEFAULT_CONFIG = Config()


def load_config(path: str | Path | None) -> Config:
    """从 JSON 文件加载配置，未指定的字段沿用默认值。

    配置文件形如：{"admission": {"min_commits": 20}, "repo_quality": {...}}
    """
    if path is None:
        return DEFAULT_CONFIG
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    config = Config()
    for section in ("admission", "repo_quality", "milestone_quality"):
        if section in data:
            target = getattr(config, section)
            for key, value in data[section].items():
                if hasattr(target, key):
                    setattr(target, key, value)
    return config
