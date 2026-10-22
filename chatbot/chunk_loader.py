from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ChunkRecord:
    doc_id: str
    source_filename: str
    file_type: str
    chunk_id: str
    chunk_index: int
    text: str
    char_start: int | None = None
    char_end: int | None = None


def load_chunk_artifact(path: str | Path) -> list[ChunkRecord]:
    artifact_path = Path(path)
    with artifact_path.open("r", encoding="utf-8") as handle:
        artifact = json.load(handle)

    chunks = artifact.get("chunks")
    if not isinstance(chunks, list):
        raise ValueError(f"Chunk artifact missing chunks list: {artifact_path}")

    records: list[ChunkRecord] = []
    for item in chunks:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        records.append(
            ChunkRecord(
                doc_id=str(artifact.get("doc_id", "")),
                source_filename=str(artifact.get("source_filename", "")),
                file_type=str(artifact.get("file_type", "")),
                chunk_id=str(item.get("chunk_id", "")),
                chunk_index=int(item.get("chunk_index", 0)),
                text=text,
                char_start=item.get("char_start"),
                char_end=item.get("char_end"),
            )
        )
    return records
