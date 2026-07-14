import tempfile
import unittest
from pathlib import Path

from tracker.config import ConfigError, load_config

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write(tmp: str, text: str) -> Path:
    path = Path(tmp) / "researchers.yaml"
    path.write_text(text, encoding="utf-8")
    return path


class RealConfigTests(unittest.TestCase):
    def test_repo_config_loads(self):
        researchers = load_config(REPO_ROOT / "researchers.yaml")
        enabled = [researcher for researcher in researchers if researcher.enabled]
        self.assertGreaterEqual(len(researchers), 100)
        self.assertGreaterEqual(len(enabled), 100)

        by_name = {researcher.name: researcher for researcher in researchers}
        self.assertIn("Quoc V. Le", by_name["Quoc Le"].aliases)
        self.assertFalse(by_name["Anthropic (Interpretability Team)"].enabled)
        self.assertFalse(by_name["David Marr"].enabled)
        self.assertEqual(by_name["Satinder Singh"].sources, ("arxiv",))

    def test_folded_query_variant_added(self):
        researchers = load_config(REPO_ROOT / "researchers.yaml")
        kaiser = next(r for r in researchers if r.name == "Łukasz Kaiser")
        self.assertIn("Lukasz Kaiser", kaiser.query_names())


class ValidationTests(unittest.TestCase):
    def test_duplicate_name_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "researchers:\n  - Jane Doe\n  - name: Jane Doe\n")
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_unknown_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "researchers:\n  - name: Jane Doe\n    alias: [J. Doe]\n")
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_invalid_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "researchers:\n  - name: Jane Doe\n    sources: [scholar]\n")
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_plain_string_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "researchers:\n  - Jane Doe\n")
            researchers = load_config(path)
            self.assertEqual(researchers[0].name, "Jane Doe")
            self.assertEqual(researchers[0].sources, ("arxiv", "openalex"))
            self.assertTrue(researchers[0].enabled)


if __name__ == "__main__":
    unittest.main()
