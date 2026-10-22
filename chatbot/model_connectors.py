from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from collections.abc import Iterator
from typing import Protocol


class ChatModelConnector(Protocol):
    def generate(self, prompt: str) -> str:
        ...


@dataclass
class FakeModelConnector:
    response: str
    last_prompt: str = ""

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response

    def stream(self, prompt: str) -> Iterator[str]:
        self.last_prompt = prompt
        yield self.response


@dataclass
class OllamaConnector:
    model: str = "llama3.1:8b"
    endpoint: str = "http://127.0.0.1:11434/api/generate"
    timeout_seconds: int = 60

    def generate(self, prompt: str) -> str:
        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Could not reach local Ollama. Start Ollama and ensure the model is installed."
            ) from exc
        return str(data.get("response", "")).strip()

    def stream(self, prompt: str) -> Iterator[str]:
        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": True}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                for line in response:
                    if not line:
                        continue
                    data = json.loads(line.decode("utf-8"))
                    text = str(data.get("response", ""))
                    if text:
                        yield text
                    if data.get("done"):
                        break
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Could not reach local Ollama. Start Ollama and ensure the model is installed."
            ) from exc
