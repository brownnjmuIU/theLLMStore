from __future__ import annotations

import re
from dataclasses import dataclass

from chatbot.chunk_loader import ChunkRecord


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "can",
    "did",
    "do",
    "does",
    "be",
    "by",
    "for",
    "from",
    "after",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "some",
    "that",
    "this",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}

OVERVIEW_TERMS = {
    "about",
    "document",
    "file",
    "content",
    "summary",
    "summarize",
    "overview",
    "doc",
    "pdf",
}

MENTION_TERMS = {
    "mention",
    "mentioned",
    "list",
    "listed",
    "name",
    "named",
    "example",
    "examples",
}

NAME_SIGNAL_STOPWORDS = {
    "Analytical",
    "Collector",
    "Contents",
    "Field",
    "Folder",
    "Generation",
    "Legendary",
    "People",
    "Pokemon",
    "Pokémon",
    "Profiles",
    "Reference",
    "Section",
    "Stat",
    "Table",
    "The",
    "Type",
    "Ultimate",
    "Value",
}


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: ChunkRecord
    score: int


def _tokens(text: str) -> list[str]:
    return [
        _normalize_token(token)
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if token not in STOPWORDS and len(token) > 2
    ]


def _normalize_token(token: str) -> str:
    if len(token) > 4 and token.endswith("s"):
        return token[:-1]
    return token


def retrieve_relevant_chunks(
    question: str,
    chunks: list[ChunkRecord],
    limit: int = 4,
) -> list[RetrievedChunk]:
    query_terms = _tokens(question)
    if not query_terms:
        return []
    if _is_overview_query(query_terms):
        return [
            RetrievedChunk(chunk=chunk, score=0)
            for chunk in sorted(chunks, key=lambda item: item.chunk_index)[:limit]
        ]
    if _is_mentioned_examples_query(query_terms):
        return _retrieve_mentioned_example_chunks(chunks, limit)

    scored: list[RetrievedChunk] = []
    for chunk in chunks:
        chunk_terms = _tokens(chunk.text)
        score = sum(chunk_terms.count(term) for term in query_terms)
        if score > 0:
            scored.append(RetrievedChunk(chunk=chunk, score=score))

    ranked = sorted(
        scored,
        key=lambda item: (-item.score, item.chunk.chunk_index),
    )
    if not ranked:
        return []
    strongest_score = ranked[0].score
    minimum_score = max(1, strongest_score - 1)
    return [item for item in ranked if item.score >= minimum_score][:limit]


def matched_query_terms(question: str, text: str) -> list[str]:
    query_terms = _tokens(question)
    text_terms = set(_tokens(text))
    matches = []
    for term in query_terms:
        if term in text_terms and term not in matches:
            matches.append(term)
    return matches


def _is_overview_query(query_terms: list[str]) -> bool:
    return bool(query_terms) and all(term in OVERVIEW_TERMS for term in query_terms)


def _is_mentioned_examples_query(query_terms: list[str]) -> bool:
    return any(term in MENTION_TERMS for term in query_terms) and len(query_terms) <= 4


def _retrieve_mentioned_example_chunks(
    chunks: list[ChunkRecord], limit: int
) -> list[RetrievedChunk]:
    scored = [
        RetrievedChunk(chunk=chunk, score=_mentioned_example_score(chunk.text))
        for chunk in chunks
    ]
    ranked = sorted(scored, key=lambda item: (-item.score, item.chunk.chunk_index))
    return ranked[:limit]


def _mentioned_example_score(text: str) -> int:
    lower = text.lower()
    score = 0

    if "table of contents" in lower:
        score += 12
    if "contents" in lower:
        score += 4
    if "mentioned" in lower:
        score += 4
    if "section" in lower:
        score += 2
    if "profile" in lower:
        score += 2

    score += min(text.count(","), 6)
    score += min(text.count("|"), 4)
    score += min(text.count("—"), 4)
    score += min(len(re.findall(r"#\d+", text)), 6)

    name_like_tokens = re.findall(r"\b[A-Z][A-Za-zéÉ0-9]{2,}\b", text)
    meaningful_names = [
        token for token in name_like_tokens if token not in NAME_SIGNAL_STOPWORDS
    ]
    score += min(len(set(meaningful_names)), 10)

    uppercase_headings = re.findall(r"\b[A-Z][A-Z0-9]{3,}\b", text)
    score += min(len(set(uppercase_headings)), 5)

    return score
