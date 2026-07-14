import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tracker.__main__ import main
from tracker.model import Publication

CONFIG = """\
researchers:
  - name: Jane Doe
    categories: [testing]
"""


def _publication(pid, title, days_ago=1):
    return Publication(
        source="arxiv",
        pid=pid,
        title=title,
        url=f"https://arxiv.org/abs/{pid.split(':', 1)[1]}",
        published=dt.date.today() - dt.timedelta(days=days_ago),
        authors=["Jane Doe"],
        categories=["cs.LG"],
    )


class MainTests(unittest.TestCase):
    def _argv(self, tmp: Path) -> list[str]:
        return [
            "--config", str(tmp / "researchers.yaml"),
            "--state", str(tmp / "data" / "seen.json"),
            "--report", str(tmp / "report.md"),
            "--title-file", str(tmp / "report_title.txt"),
            "--latest", str(tmp / "LATEST.md"),
        ]

    def test_first_run_reports_second_run_is_quiet(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            (tmp / "researchers.yaml").write_text(CONFIG, encoding="utf-8")

            fresh = [
                _publication("arxiv:2507.11111", "Erste Arbeit"),
                _publication("arxiv:2507.22222", "Zweite Arbeit", days_ago=2),
            ]
            with mock.patch("tracker.arxiv.fetch", return_value=fresh), \
                    mock.patch("tracker.openalex.fetch", return_value=[]):
                exit_code = main(self._argv(tmp))

            self.assertEqual(exit_code, 0)
            report = (tmp / "report.md").read_text(encoding="utf-8")
            self.assertIn("Jane Doe", report)
            self.assertIn("Erste Arbeit", report)
            self.assertIn("(2)", (tmp / "report_title.txt").read_text(encoding="utf-8"))
            self.assertTrue((tmp / "LATEST.md").exists())
            self.assertTrue((tmp / "data" / "seen.json").exists())

            # Zweiter Lauf: gleiche Ergebnisse -> nichts Neues, kein Report
            (tmp / "report.md").unlink()
            with mock.patch("tracker.arxiv.fetch", return_value=fresh), \
                    mock.patch("tracker.openalex.fetch", return_value=[]):
                exit_code = main(self._argv(tmp))
            self.assertEqual(exit_code, 0)
            self.assertFalse((tmp / "report.md").exists())

    def test_cross_source_title_dedup(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            (tmp / "researchers.yaml").write_text(CONFIG, encoding="utf-8")

            arxiv_pub = _publication("arxiv:2507.33333", "Gleiche Arbeit")
            openalex_pub = Publication(
                source="openalex",
                pid="doi:10.1000/abc",
                title="Gleiche  Arbeit",
                url="https://doi.org/10.1000/abc",
                published=dt.date.today(),
                authors=["Jane Doe"],
                venue="Some Journal",
            )
            with mock.patch("tracker.arxiv.fetch", return_value=[arxiv_pub]), \
                    mock.patch("tracker.openalex.fetch", return_value=[openalex_pub]):
                exit_code = main(self._argv(tmp))

            self.assertEqual(exit_code, 0)
            title = (tmp / "report_title.txt").read_text(encoding="utf-8")
            self.assertIn("(1)", title)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            (tmp / "researchers.yaml").write_text(CONFIG, encoding="utf-8")
            with mock.patch("tracker.arxiv.fetch", return_value=[_publication("arxiv:2507.44444", "X")]), \
                    mock.patch("tracker.openalex.fetch", return_value=[]):
                exit_code = main(self._argv(tmp) + ["--dry-run"])
            self.assertEqual(exit_code, 0)
            self.assertFalse((tmp / "report.md").exists())
            self.assertFalse((tmp / "data" / "seen.json").exists())

    def test_all_sources_failing_marks_run_red(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            (tmp / "researchers.yaml").write_text(CONFIG, encoding="utf-8")
            boom = RuntimeError("API kaputt")
            with mock.patch("tracker.arxiv.fetch", side_effect=boom), \
                    mock.patch("tracker.openalex.fetch", side_effect=boom):
                exit_code = main(self._argv(tmp))
            self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
