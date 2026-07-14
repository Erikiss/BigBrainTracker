import datetime as dt
import tempfile
import unittest
from pathlib import Path

from tracker.model import Publication
from tracker.state import State


def _publication(pid="arxiv:2507.01234", title="A Paper"):
    return Publication(
        source="arxiv",
        pid=pid,
        title=title,
        url="https://arxiv.org/abs/2507.01234",
        published=dt.date(2026, 7, 10),
    )


class StateTests(unittest.TestCase):
    def test_roundtrip(self):
        today = dt.date(2026, 7, 14)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data" / "seen.json"
            state = State.load(path)
            publication = _publication()
            self.assertFalse(state.is_seen("Yann LeCun", publication))
            state.mark_seen("Yann LeCun", publication, today)
            self.assertTrue(state.is_seen("Yann LeCun", publication))
            # Andere Person: eigener Schlüsselraum
            self.assertFalse(state.is_seen("Quoc Le", publication))
            state.save()

            reloaded = State.load(path)
            self.assertTrue(reloaded.is_seen("Yann LeCun", publication))

    def test_same_title_other_source_is_seen(self):
        today = dt.date(2026, 7, 14)
        state = State("unused.json")
        state.mark_seen("Yann LeCun", _publication(), today)
        other_source = Publication(
            source="openalex",
            pid="doi:10.1000/xyz",
            title="A  Paper",  # gleicher Titel, andere Quelle/ID
            url="https://doi.org/10.1000/xyz",
            published=dt.date(2026, 7, 11),
        )
        self.assertTrue(state.is_seen("Yann LeCun", other_source))

    def test_prune(self):
        today = dt.date(2026, 7, 14)
        state = State("unused.json", {
            "A|arxiv:1": "2020-01-01",
            "B|arxiv:2": today.isoformat(),
            "C|arxiv:3": "kein-datum",
        })
        state.prune(today, keep_days=400)
        self.assertNotIn("A|arxiv:1", state.entries)
        self.assertIn("B|arxiv:2", state.entries)
        self.assertIn("C|arxiv:3", state.entries)  # unlesbares Datum wird behalten


if __name__ == "__main__":
    unittest.main()
