from __future__ import annotations

import json
import time
import urllib.request

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
OLLAMA_URL = "http://127.0.0.1:11434"


def list_local_models() -> list[dict]:
    """Ask Ollama which models are installed and how big they are."""
    with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as response:
        data = json.loads(response.read().decode("utf-8"))
    return [
        {"name": item["name"], "size_gb": item.get("size", 0) / 1e9}
        for item in data.get("models", [])
    ]


def build_context(question: str, chunks: list[ChunkRecord]) -> dict:
    """Retrieve once, so every model receives the exact same prompt."""
    retrieved = retrieve_relevant_chunks(question, chunks)
    sources = [
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
    prompt = ""
    if retrieved:
        context_blocks = [f"[{item.chunk.chunk_id}] {item.chunk.text}" for item in retrieved]
        prompt = _build_prompt(question, "\n\n".join(context_blocks))
    return {
        "question": question,
        "total_chunks": len(chunks),
        "prompt": prompt,
        "sources": sources,
    }


def ask_model(prompt: str, model: str) -> dict:
    """Send one prompt to one model and keep Ollama's timing statistics."""
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=300) as response:
        data = json.loads(response.read().decode("utf-8"))
    seconds = time.perf_counter() - started

    tokens = data.get("eval_count", 0)
    eval_seconds = data.get("eval_duration", 0) / 1e9
    return {
        "model": model,
        "answer": str(data.get("response", "")).strip(),
        "seconds": seconds,
        "load_seconds": data.get("load_duration", 0) / 1e9,
        "tokens": tokens,
        "tokens_per_second": tokens / eval_seconds if eval_seconds else 0.0,
    }