from __future__ import annotations

from dataclasses import dataclass

from chatbot.chunk_loader import ChunkRecord
from chatbot.model_connectors import ChatModelConnector
from chatbot.retriever import retrieve_relevant_chunks


@dataclass(frozen=True)
class ChatbotAnswer:
    answer: str
    source_chunk_ids: list[str]


def _build_prompt(question: str, retrieved_text: str) -> str:
    return (
        "You are the PPLLM assistant. Answer using only the provided context. "
        "If the context does not contain the answer, say you do not know from the processed file. "
        "When asked what names, examples, or items are mentioned, list only names or items that appear in the context.\n\n"
        f"Context:\n{retrieved_text}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )


def answer_question(
    question: str,
    chunks: list[ChunkRecord],
    connector: ChatModelConnector,
    limit: int = 4,
) -> ChatbotAnswer:
    retrieved = retrieve_relevant_chunks(question, chunks, limit=limit)
    if not retrieved:
        return ChatbotAnswer(
            answer="I could not find relevant information in the processed chunks.",
            source_chunk_ids=[],
        )

    context_blocks = []
    for item in retrieved:
        context_blocks.append(f"[{item.chunk.chunk_id}] {item.chunk.text}")

    prompt = _build_prompt(question, "\n\n".join(context_blocks))
    return ChatbotAnswer(
        answer=connector.generate(prompt),
        source_chunk_ids=[item.chunk.chunk_id for item in retrieved],
    )
