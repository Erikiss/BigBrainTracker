import datetime as dt
import unittest
from unittest import mock

from tracker import arxiv, openalex
from tracker.config import Researcher

ARXIV_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2507.01234v2</id>
    <published>2026-07-10T12:00:00Z</published>
    <title>Fresh  Paper
      With Linebreak</title>
    <author><name>Quoc V. Le</name></author>
    <author><name>Somebody Else</name></author>
    <category term="cs.LG"/>
    <category term="stat.ML"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <published>2024-01-01T00:00:00Z</published>
    <title>Old Paper</title>
    <author><name>Quoc V. Le</name></author>
    <category term="cs.LG"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2507.09999v1</id>
    <published>2026-07-11T12:00:00Z</published>
    <title>Wrong Author Paper</title>
    <author><name>Jerry Le</name></author>
    <category term="cs.LG"/>
  </entry>
</feed>
"""

OPENALEX_PAYLOAD = {
    "results": [
        {
            "id": "https://openalex.org/W111",
            "display_name": "Journal Paper",
            "publication_date": "2026-07-01",
            "doi": "https://doi.org/10.1000/xyz",
            "primary_location": {
                "landing_page_url": "https://example.com/paper",
                "source": {"display_name": "Nature Neuroscience"},
            },
            "authorships": [
                {"author": {"display_name": "Karl J. Friston"}, "raw_author_name": "Karl Friston"},
            ],
        },
        {
            "id": "https://openalex.org/W222",
            "display_name": "Arxiv Mirror Paper",
            "publication_date": "2026-07-02",
            "doi": "https://doi.org/10.48550/arXiv.2507.05555",
            "primary_location": {
                "landing_page_url": "https://arxiv.org/abs/2507.05555v1",
                "source": {"display_name": "arXiv"},
            },
            "authorships": [
                {"author": {"display_name": "Karl Friston"}, "raw_author_name": "K. Friston"},
            ],
        },
        {
            "id": "https://openalex.org/W333",
            "display_name": "Unrelated Person Paper",
            "publication_date": "2026-07-03",
            "doi": None,
            "primary_location": None,
            "authorships": [
                {"author": {"display_name": "Karla Friston-Smith"}, "raw_author_name": "Karla Friston-Smith"},
            ],
        },
        {
            "id": "https://openalex.org/W444",
            "display_name": "Too Old Paper",
            "publication_date": "2020-01-01",
            "doi": None,
            "primary_location": None,
            "authorships": [
                {"author": {"display_name": "Karl Friston"}, "raw_author_name": "Karl Friston"},
            ],
        },
    ]
}


class _FakeResponse:
    def __init__(self, content=b"", payload=None):
        self.content = content
        self._payload = payload

    def json(self):
        return self._payload


class ArxivTests(unittest.TestCase):
    def setUp(self):
        throttle = mock.patch.object(arxiv, "_throttle", lambda: None)
        throttle.start()
        self.addCleanup(throttle.stop)

    def test_fetch_filters_and_dedupes(self):
        person = Researcher(name="Quoc Le", aliases=("Quoc V. Le",))
        with mock.patch.object(arxiv.http, "get", return_value=_FakeResponse(ARXIV_FEED)) as get:
            publications = arxiv.fetch(person, cutoff=dt.date(2026, 7, 1))
        # eine Anfrage je Suchname, Ergebnisse per ID dedupliziert
        self.assertEqual(get.call_count, len(person.query_names()))
        self.assertEqual(len(publications), 1)
        publication = publications[0]
        self.assertEqual(publication.pid, "arxiv:2507.01234")
        self.assertEqual(publication.url, "https://arxiv.org/abs/2507.01234")
        self.assertEqual(publication.published, dt.date(2026, 7, 10))
        self.assertEqual(publication.title, "Fresh Paper With Linebreak")
        self.assertEqual(publication.categories, ["cs.LG", "stat.ML"])

    def test_category_prefix_filter(self):
        person = Researcher(name="Quoc Le", arxiv_categories=("q-bio.",))
        with mock.patch.object(arxiv.http, "get", return_value=_FakeResponse(ARXIV_FEED)):
            publications = arxiv.fetch(person, cutoff=dt.date(2026, 7, 1))
        self.assertEqual(publications, [])


class OpenAlexTests(unittest.TestCase):
    def setUp(self):
        throttle = mock.patch.object(openalex, "_throttle", lambda: None)
        throttle.start()
        self.addCleanup(throttle.stop)

    def test_fetch_matches_and_canonicalises(self):
        person = Researcher(name="Karl Friston", aliases=("Karl J. Friston",))
        with mock.patch.object(
            openalex.http, "get", return_value=_FakeResponse(payload=OPENALEX_PAYLOAD)
        ):
            publications = openalex.fetch(person, cutoff=dt.date(2026, 6, 1))
        pids = {publication.pid for publication in publications}
        # W333 (fremde Person) und W444 (zu alt) fliegen raus;
        # W222 wird auf die arXiv-ID kanonisiert.
        self.assertEqual(pids, {"doi:10.1000/xyz", "arxiv:2507.05555"})
        journal = next(p for p in publications if p.pid == "doi:10.1000/xyz")
        self.assertEqual(journal.venue, "Nature Neuroscience")
        self.assertEqual(journal.url, "https://doi.org/10.1000/xyz")

    def test_openalex_id_skips_name_check(self):
        person = Researcher(name="Ganz Anders", openalex_id="A5000000001")
        with mock.patch.object(
            openalex.http, "get", return_value=_FakeResponse(payload=OPENALEX_PAYLOAD)
        ) as get:
            publications = openalex.fetch(person, cutoff=dt.date(2026, 6, 1))
        self.assertEqual(get.call_count, 1)
        call_filter = get.call_args.kwargs["params"]["filter"] if get.call_args.kwargs else \
            get.call_args.args[1]["filter"]
        self.assertIn("authorships.author.id:A5000000001", call_filter)
        # Namensabgleich ist bei ID-Filter abgeschaltet -> alle frischen Werke bleiben
        self.assertEqual(len(publications), 3)


if __name__ == "__main__":
    unittest.main()
