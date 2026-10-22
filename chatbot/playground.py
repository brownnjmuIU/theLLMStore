from __future__ import annotations

import time

from chatbot.chunk_loader import ChunkRecord
from chatbot.model_connectors import OllamaConnector
from chatbot.rag_service import _build_prompt
from chatbot.retriever import matched_query_terms, retrieve_relevant_chunks
from processing.chunker import chunk_text
from processing.cleaner import clean_text
from storage.json_store import load_raw_document_by_path


def chunk_in_memory(
    raw_artifact_path: str, chunk_size: int, chunk_overlap: int
) -> list[ChunkRecord]:
    """Re-chunk the raw document without saving anything to disk."""
    doc = load_raw_document_by_path(raw_artifact_path)
    if doc is None:
        raise ValueError(f"Document not found: {raw_artifact_path}")
    data = chunk_text(
        text=clean_text(doc["text"]),
        doc_id=doc["doc_id"],
        source_filename=doc["source_filename"],
        file_type=doc["file_type"],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    records = []
    for item in data["chunks"]:
        text = item["text"].strip()
        if not text:
            continue
        records.append(
            ChunkRecord(
                doc_id=data["doc_id"],
                source_filename=data["source_filename"],
                file_type=data["file_type"],
                chunk_id=item["chunk_id"],
                chunk_index=item["chunk_index"],
                text=text,
                char_start=item.get("char_start"),
                char_end=item.get("char_end"),
            )
        )
    return records


def answer_with_trace(question: str, chunks: list[ChunkRecord]) -> dict:
    """Retrieve, ask the model, and return the full trace including the answer."""
    started = time.perf_counter()
    connector = OllamaConnector()
    retrieved = retrieve_relevant_chunks(question, chunks)
    trace = {
        "question": question,
        "total_chunks": len(chunks),
        "model": getattr(connector, "model", "unknown"),
        "prompt": "",
        "sources": [],
        "answer": "",
        "seconds": 0.0,
    }
    if not retrieved:
        trace["answer"] = "I could not find relevant information in the processed chunks."
        trace["seconds"] = time.perf_counter() - started
        return trace

    context_blocks = [f"[{item.chunk.chunk_id}] {item.chunk.text}" for item in retrieved]
    prompt = _build_prompt(question, "\n\n".join(context_blocks))
    trace["prompt"] = prompt
    trace["answer"] = "".join(connector.stream(prompt)).strip()
    trace["sources"] = [
        {
            "chunk_id": item.chunk.chunk_id,
            "chunk_index": item.chunk.chunk_index,
            "score": item.score,
            "source_filename": item.chunk.source_filename,
            "matched_terms": matched_query_terms(question, item.chunk.text),
            "text": item.chunk.text,
        }
        for item in retrieved
    ]
    trace["seconds"] = time.perf_counter() - started
    return trace