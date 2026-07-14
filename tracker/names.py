"""Author-name normalisation and matching.

Matching policy: an author name matches a target name if, after folding
diacritics and punctuation, the first and the last token are identical.
Middle names and initials are ignored ("Quoc V. Le" ~ "Quoc Le"), but an
abbreviated first name is NOT accepted ("J. Wei" !~ "Jason Wei") so that
common surnames don't produce false positives.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

# Latin letters that NFKD does not decompose to ASCII.
_CHAR_MAP = str.maketrans({
    "ß": "ss", "ẞ": "SS",
    "æ": "ae", "Æ": "AE",
    "œ": "oe", "Œ": "OE",
    "ø": "o", "Ø": "O",
    "ł": "l", "Ł": "L",
    "đ": "d", "Đ": "D",
    "ð": "d", "Ð": "D",
    "þ": "th", "Þ": "Th",
    "ı": "i",
})

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def fold(text: str) -> str:
    """Fold diacritics and special latin letters to plain ASCII (best effort)."""
    text = text.translate(_CHAR_MAP)
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def name_tokens(name: str) -> list[str]:
    """Tokenise a person name; handles "Last, First" ordering."""
    name = name.strip()
    if "," in name:
        last, _, first = name.partition(",")
        name = f"{first} {last}"
    name = fold(name).casefold()
    return [token for token in _NON_ALNUM.split(name) if token]


def matches(author_name: str, target_names: Iterable[str]) -> bool:
    """True if ``author_name`` plausibly refers to one of ``target_names``."""
    author = name_tokens(author_name)
    if not author:
        return False
    for target_name in target_names:
        target = name_tokens(target_name)
        if not target:
            continue
        if author == target:
            return True
        if (
            len(author) >= 2
            and len(target) >= 2
            and author[0] == target[0]
            and author[-1] == target[-1]
        ):
            return True
    return False


def title_key(title: str) -> str:
    """Normalised title, used to deduplicate the same work across sources."""
    return " ".join(_NON_ALNUM.split(fold(title).casefold())).strip()
