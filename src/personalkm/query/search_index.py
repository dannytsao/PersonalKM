from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable


_CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")
_LATIN_RE = re.compile(r"[a-z0-9][a-z0-9+.#-]*", re.IGNORECASE)

# Groups of interchangeable terms so keyword search isn't purely literal
# substring matching. A query term belonging to a group is expanded to the
# whole group before matching against the index, so entries phrased with a
# synonym (e.g. an entry's highlight says "\u6d77\u7522" while the user searched
# "\u6d77\u9bae") aren't silently dropped. Add new groups here as they're found \u2014
# this is a lightweight substitute for real semantic search, not a
# replacement for one.
# Bars are rarely described with the literal word "酒吧": registry entries say
# "Cocktail Bar", "Lounge", "調酒", "精釀啤酒" instead. Bug found 2026-11-10:
# "士林酒吧" returned only the one store whose subject was literally "酒吧"
# (itself a café misfiled as a bar), missing Hangout Cocktail Bar,
# 醺Two British Bar, RedHut Lounge Bar, ... which are all tagged "美食".
BAR_TERMS: tuple[str, ...] = (
    "酒吧", "bar", "pub", "lounge", "cocktail", "調酒", "威士忌", "whisky", "精釀", "生啤",
)

SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"\u6d77\u9bae", "\u6d77\u7522", "\u6f01\u7522"}),
    frozenset(BAR_TERMS),
    frozenset({"溫泉", "泡湯", "湯屋"}),
)


# 臺→台 plus the simplified characters that actually occur in registry
# addresses copied from Google Maps (e.g. "桃园市芦竹区", "宜兰县员山乡").
# Applied to both the index and the query so either spelling matches.
_PLACE_CHAR_MAP = str.maketrans({
    "臺": "台", "区": "區", "县": "縣", "乡": "鄉", "镇": "鎮", "园": "園",
    "芦": "蘆", "兰": "蘭", "员": "員", "坜": "壢", "东": "東", "义": "義",
    "丰": "豐", "凤": "鳳", "华": "華", "门": "門", "罗": "羅", "莲": "蓮",
    "宁": "寧", "龙": "龍", "湾": "灣",
})


def normalize_place_text(text: str) -> str:
    return text.translate(_PLACE_CHAR_MAP)


def _expand_synonyms(terms: set[str]) -> set[str]:
    expanded = set(terms)
    for term in terms:
        for group in SYNONYM_GROUPS:
            if term in group:
                expanded.update(group)
    return expanded


@dataclass(frozen=True, slots=True)
class SearchIndex:
    entries: tuple[object, ...]
    postings: dict[str, tuple[int, ...]]


def _terms(text: str) -> set[str]:
    text = normalize_place_text(text)
    terms = {match.group(0).lower() for match in _LATIN_RE.finditer(text)}
    for run in _CJK_RUN_RE.findall(text):
        if len(run) >= 2:
            terms.add(run)
        for size in (2, 3, 4):
            terms.update(run[index : index + size] for index in range(len(run) - size + 1))
    return terms


def build_search_index(entries: Iterable[object]) -> SearchIndex:
    materialized = tuple(entries)
    postings: dict[str, set[int]] = defaultdict(set)
    for index, entry in enumerate(materialized):
        text = " ".join(
            str(getattr(entry, field, ""))
            for field in ("city", "subject", "store", "address", "highlights")
        )
        for term in _terms(text):
            postings[term].add(index)
    return SearchIndex(
        entries=materialized,
        postings={term: tuple(sorted(indices)) for term, indices in postings.items()},
    )


def query_terms(query: str, *, ignored: Iterable[str] = ()) -> set[str]:
    ignored_terms = {term.lower() for term in ignored if len(term) >= 2}
    cleaned = query.lower()
    for ignored_term in sorted(ignored_terms, key=len, reverse=True):
        cleaned = cleaned.replace(ignored_term, " ")
    terms = {
        term
        for term in _terms(cleaned)
        if "的" not in term
        and term not in ignored_terms
        and not any(ignored in term for ignored in ignored_terms)
    }
    return _expand_synonyms(terms)


def search(
    index: SearchIndex,
    terms: Iterable[str],
    *,
    predicate: Callable[[object], bool] | None = None,
) -> list[object]:
    scores: dict[int, int] = defaultdict(int)
    for term in terms:
        for entry_index in index.postings.get(term, ()):
            entry = index.entries[entry_index]
            if predicate is None or predicate(entry):
                scores[entry_index] += 1
    return [
        index.entries[entry_index]
        for entry_index, _score in sorted(
            scores.items(),
            key=lambda item: (-item[1], -(getattr(index.entries[item[0]], "rating", None) or 0), getattr(index.entries[item[0]], "store", "")),
        )
    ]
