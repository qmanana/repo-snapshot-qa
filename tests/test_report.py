"""report 模块的单元测试。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from repo_snapshot_qa.models import CheckResult
from repo_snapshot_qa.report import (
    format_results,
    render_html,
    results_to_dict,
    summarize,
    write_html_report,
    write_json_report,
)


class ReportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.results = [
            CheckResult("提交数量", True, 1.0, ["共 30 条提交"]),
            CheckResult("可解析率", False, 0.5, ["1/2 可解析"]),
        ]

    def test_format_results(self) -> None:
        text = format_results(self.results, "准入检查")
        self.assertIn("准入检查", text)
        self.assertIn("提交数量", text)
        self.assertIn("未通过", text)

    def test_results_to_dict(self) -> None:
        data = results_to_dict(self.results)
        self.assertEqual(data[0]["name"], "提交数量")
        self.assertTrue(data[0]["passed"])

    def test_json_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            write_json_report(path, {"admission": self.results})
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["admission"][0]["name"], "提交数量")

    def test_html_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.html"
            write_html_report(path, {"admission": self.results})
            content = path.read_text(encoding="utf-8")
            self.assertIn("<html>", content)
            self.assertIn("提交数量", content)

    def test_json_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            write_json_report(path, {"admission": self.results})
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["summary"]["total"], 2)
            self.assertEqual(data["summary"]["passed"], 1)
            self.assertEqual(len(data["summary"]["failed"]), 1)

    def test_summarize(self) -> None:
        text = summarize({"admission": self.results})
        self.assertIn("1/2", text)
        self.assertIn("可解析率", text)

    def test_html_escapes_details(self) -> None:
        results = [CheckResult("X", False, 0.0, ["<script>alert(1)</script>"])]
        output = render_html({"admission": results})
        self.assertNotIn("<script>alert", output)
        self.assertIn("&lt;script&gt;", output)


if __name__ == "__main__":
    unittest.main()
