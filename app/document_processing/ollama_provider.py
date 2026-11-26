"""
Ollama AI provider.

Responsibilities:
1. Communicate with the local Ollama API.
2. Send prompts to the configured language model.
3. Request JSON-formatted responses.
4. Extract the generated response.
5. Handle network and API errors.

The provider does not interpret invoice fields.
That responsibility belongs to ai_extraction_service.py.
"""

import httpx

from app.core.config import settings

from app.document_processing.ai_provider import (
    AIProvider,
    AIProviderError,
)


class OllamaProvider(AIProvider):
    """
    AI provider implementation using Ollama.

    The default model is qwen3.5:9b.

    Ollama runs locally, so document text is sent to the
    local Ollama server rather than an external AI API.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        self.base_url = (
            base_url or settings.ollama_base_url
        ).rstrip("/")

        self.model = model or settings.ollama_model

        self.timeout = (
            timeout or settings.ollama_timeout_seconds
        )

    def generate_json(self, prompt: str) -> str:
        """
        Send a prompt to Ollama and return its response.

        The thinking field returned by some models is deliberately
        ignored. Only the response field is used.

        Args:
            prompt: AI extraction instructions.

        Returns:
            JSON response as a string.

        Raises:
            AIProviderError: If Ollama is unavailable or returns
                             an invalid response structure.
        """

        endpoint = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            # Structured extraction does not need long reasoning traces.
            "think": False,
            # Nine invoice fields fit comfortably within this response cap.
            "options": {
                "temperature": 0,
                "num_predict": 512,
            },
        }

        try:
            response = httpx.post(
                endpoint,
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()

            response_data = response.json()

            if not isinstance(response_data, dict):
                raise AIProviderError(
                    "Ollama returned an unexpected response structure"
                )

        except httpx.TimeoutException as exc:
            raise AIProviderError(
                "Ollama request timed out"
            ) from exc

        except httpx.HTTPError as exc:
            raise AIProviderError(
                "Unable to communicate with Ollama"
            ) from exc

        except ValueError as exc:
            raise AIProviderError(
                "Ollama returned an invalid API response"
            ) from exc

        generated_text = response_data.get("response")

        if not isinstance(generated_text, str):
            raise AIProviderError(
                "Ollama response does not contain generated text"
            )

        if not generated_text.strip():
            raise AIProviderError(
                "Ollama returned an empty response"
            )

        return generated_text.strip()
