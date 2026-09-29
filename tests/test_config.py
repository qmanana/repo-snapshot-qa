"""config 模块的单元测试。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repo_snapshot_qa.config import Config, load_config


class ConfigTest(unittest.TestCase):
    def test_default_config(self) -> None:
        config = Config()
        self.assertEqual(config.admission.min_commits, 10)
        self.assertEqual(config.repo_quality.min_subsystems, 3)
        self.assertEqual(config.milestone_quality.min_milestones, 3)

    def test_load_config_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                '{"admission": {"min_commits": 20}, "milestone_quality": {"cohesion_ratio": 0.7}}',
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertEqual(config.admission.min_commits, 20)
            # 未覆盖的字段沿用默认值。
            self.assertEqual(config.admission.min_loc, 200)
            self.assertEqual(config.milestone_quality.cohesion_ratio, 0.7)
            self.assertEqual(config.repo_quality.min_subsystems, 3)

    def test_load_config_none_returns_default(self) -> None:
        config = load_config(None)
        self.assertEqual(config.admission.min_commits, 10)

    def test_health_config_default(self) -> None:
        config = Config()
        self.assertEqual(config.health.min_test_ratio, 0.05)
        self.assertEqual(config.health.max_file_loc, 500)

    def test_load_config_health_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text('{"health": {"max_file_loc": 100}}', encoding="utf-8")
            config = load_config(path)
            self.assertEqual(config.health.max_file_loc, 100)
            self.assertEqual(config.health.min_test_ratio, 0.05)


if __name__ == "__main__":
    unittest.main()
