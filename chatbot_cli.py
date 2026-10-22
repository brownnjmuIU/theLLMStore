import argparse

from chatbot.chunk_loader import load_chunk_artifact
from chatbot.model_connectors import OllamaConnector
from chatbot.rag_service import answer_question


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ask a question against a PPLLM chunk JSON file."
    )
    parser.add_argument("chunk_json")
    parser.add_argument("question")
    parser.add_argument("--model", default="llama3.1:8b")
    args = parser.parse_args()

    chunks = load_chunk_artifact(args.chunk_json)
    answer = answer_question(args.question, chunks, OllamaConnector(model=args.model))
    print(answer.answer)
    if answer.source_chunk_ids:
        print("\nSources:", ", ".join(answer.source_chunk_ids))


if __name__ == "__main__":
    main()
