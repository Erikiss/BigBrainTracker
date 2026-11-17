import datetime as dt
import unittest

from tracker.config import Researcher
from tracker.model import Publication
from tracker.report import render_report


RUN_DATE = dt.date(2026, 11, 17)


def _publication(pid, title, source="arxiv"):
    return Publication(
        source=source,
        pid=pid,
        title=title,
        url=f"https://example.org/{pid}",
        published=RUN_DATE,
    )


class ReportTests(unittest.TestCase):
    def test_shared_paper_is_displayed_once_and_empty_sections_are_removed(self):
        shared = _publication("arxiv:2611.07071", "Shared paper")
        unique = _publication("arxiv:2611.99999", "Distinct paper")
        findings = [
            (Researcher("Alice Example"), [shared]),
            (Researcher("Bob Example"), [shared]),
            (Researcher("Carol Example"), [unique]),
        ]

        title, body = render_report(findings, RUN_DATE, 14, 45)

        self.assertIn("(2)", title)
        self.assertEqual(body.count("[Shared paper]"), 1)
        self.assertEqual(body.count("[Distinct paper]"), 1)
        self.assertIn("### Alice Example", body)
        self.assertNotIn("### Bob Example", body)
        self.assertIn("### Carol Example", body)
        self.assertEqual(body.count("### "), 2)
        # Rendering must not discard the caller's per-person findings.
        self.assertEqual([len(pubs) for _, pubs in findings], [1, 1, 1])
        self.assertEqual(render_report(findings, RUN_DATE, 14, 45), (title, body))

    def test_cross_source_titles_and_changed_titles_with_same_id_are_duplicates(self):
        original = _publication("arxiv:2611.07071", "Shared: Paper!")
        journal = _publication("doi:10.1000/shared", "shared paper", "openalex")
        revised = _publication("arxiv:2611.07071", "Revised title")
        findings = [
            (Researcher("Alice Example"), [original]),
            (Researcher("Bob Example"), [journal, revised]),
        ]

        title, body = render_report(findings, RUN_DATE, 14, 45)

        self.assertIn("(1)", title)
        self.assertEqual(body.count("- **"), 1)
        self.assertIn("[Shared: Paper!]", body)
        self.assertNotIn("### Bob Example", body)

    def test_late_duplicate_links_merge_previously_distinct_entries(self):
        original = _publication("arxiv:2611.07071", "Original title")
        journal = _publication("doi:10.1000/shared", "Updated title", "openalex")
        bridge = _publication("arxiv:2611.07071", "Updated title")
        findings = [
            (Researcher("Alice Example"), [original]),
            (Researcher("Bob Example"), [journal]),
            (Researcher("Carol Example"), [bridge]),
        ]

        title, body = render_report(findings, RUN_DATE, 14, 45)

        self.assertIn("(1)", title)
        self.assertEqual(body.count("- **"), 1)
        self.assertIn("[Original title]", body)
        self.assertEqual(body.count("### "), 1)

    def test_empty_title_keys_do_not_merge_distinct_publications(self):
        findings = [
            (Researcher("Alice Example"), [_publication("arxiv:2611.1", "")]),
            (Researcher("Bob Example"), [_publication("arxiv:2611.2", "...")]),
        ]

        title, body = render_report(findings, RUN_DATE, 14, 45)

        self.assertIn("(2)", title)
        self.assertEqual(body.count("- **"), 2)


if __name__ == "__main__":
    unittest.main()
