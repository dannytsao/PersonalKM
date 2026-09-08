from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable


_CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")
_LATIN_RE = re.compile(r"[a-z0-9][a-z0-9+.#-]*", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class SearchIndex:
    entries: tuple[object, ...]
    postings: dict[str, tuple[int, ...]]


def _terms(text: str) -> set[str]:
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
    return {
        term
        for term in _terms(cleaned)
        if "的" not in term
        and term not in ignored_terms
        and not any(ignored in term for ignored in ignored_terms)
    }


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
