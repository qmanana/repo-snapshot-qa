"""languages（语言注册表）模块的单元测试。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repo_snapshot_qa.languages import (
    _balanced,
    classify,
    is_code_file,
    is_source_path,
    verify_syntax,
)


def _write_file(tmp: str, name: str, content: str) -> Path:
    path = Path(tmp) / name
    path.write_text(content, encoding="utf-8")
    return path


class LanguagesTest(unittest.TestCase):
    def test_classify(self) -> None:
        self.assertEqual(classify(Path("a.py")), "Python")
        self.assertEqual(classify(Path("b.tsx")), "TypeScript")
        self.assertEqual(classify(Path("c.json")), "JSON")
        self.assertIsNone(classify(Path("README.md")))
        self.assertIsNone(classify(Path("LICENSE")))

    def test_is_code_file(self) -> None:
        self.assertTrue(is_code_file(Path("a.go")))
        self.assertTrue(is_code_file(Path("a.toml")))
        self.assertFalse(is_code_file(Path("a.txt")))

    def test_is_source_path(self) -> None:
        self.assertTrue(is_source_path("src/pkg/a.py"))
        self.assertTrue(is_source_path("lib/util.js"))
        self.assertFalse(is_source_path("src/pkg/__init__.py"))
        self.assertFalse(is_source_path("config/app.json"))
        self.assertFalse(is_source_path("README.md"))

    def test_balanced(self) -> None:
        self.assertTrue(_balanced("int main() { return 0; }"))
        self.assertFalse(_balanced("int main() { return 0;"))
        self.assertFalse(_balanced("fn f() { ]"))
        # 字符串与注释里的括号不参与配平
        self.assertTrue(_balanced('const s = "}"; // )'))
        self.assertTrue(_balanced("/* { */ int x;"))

    def test_verify_syntax_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            good = _write_file(tmp, "a.py", "def f():\n    return 1\n")
            self.assertEqual(verify_syntax(good, "Python"), "ok")
            bad = _write_file(tmp, "b.py", "def broken(:\n")
            self.assertEqual(verify_syntax(bad, "Python"), "bad")

    def test_verify_syntax_json_toml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            good_json = _write_file(tmp, "a.json", '{"a": 1}')
            self.assertEqual(verify_syntax(good_json, "JSON"), "ok")
            bad_json = _write_file(tmp, "b.json", "{bad")
            self.assertEqual(verify_syntax(bad_json, "JSON"), "bad")
            good_toml = _write_file(tmp, "c.toml", "a = 1\n")
            self.assertEqual(verify_syntax(good_toml, "TOML"), "ok")
            bad_toml = _write_file(tmp, "d.toml", "a = [\n")
            self.assertEqual(verify_syntax(bad_toml, "TOML"), "bad")

    def test_verify_syntax_c_like_and_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            good_js = _write_file(tmp, "a.js", "function f() { return 1; }\n")
            self.assertEqual(verify_syntax(good_js, "JavaScript"), "ok")
            bad_js = _write_file(tmp, "b.js", "function f() { return 1;\n")
            self.assertEqual(verify_syntax(bad_js, "JavaScript"), "bad")
            shell = _write_file(tmp, "s.sh", "echo hi\n")
            self.assertEqual(verify_syntax(shell, "Shell"), "unsupported")
            yaml = _write_file(tmp, "c.yaml", "a: 1\n")
            self.assertEqual(verify_syntax(yaml, "YAML"), "unsupported")


if __name__ == "__main__":
    unittest.main()
