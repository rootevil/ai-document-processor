import httpx
import pytest

from app.document_processing.ollama_provider import (
    OllamaProvider,
)

from app.document_processing.ai_provider import (
    AIProviderError,
)


def test_ollama_provider_returns_generated_response(
    monkeypatch,
):
    """
    Verify that the provider extracts the response field.

    The thinking field must not be returned to the application.
    """

    def mock_post(url, json, timeout):

        assert url.endswith("/api/generate")

        assert json["model"] == "qwen3.5:9b"

        assert json["format"] == "json"

        assert json["stream"] is False

        assert json["think"] is False

        assert json["options"] == {
            "temperature": 0,
            "num_predict": 512,
        }

        return httpx.Response(
            200,
            json={
                "response": '{"invoice_number": "INV-1001"}',
                "thinking": "Internal model reasoning",
                "done": True,
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(
        "app.document_processing.ollama_provider.httpx.post",
        mock_post,
    )

    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model="qwen3.5:9b",
    )

    result = provider.generate_json(
        "Extract invoice information"
    )

    assert result == '{"invoice_number": "INV-1001"}'

    assert "thinking" not in result


def test_ollama_provider_handles_timeout(monkeypatch):

    def mock_post(*args, **kwargs):

        raise httpx.TimeoutException(
            "Request timed out"
        )

    monkeypatch.setattr(
        "app.document_processing.ollama_provider.httpx.post",
        mock_post,
    )

    provider = OllamaProvider()

    with pytest.raises(AIProviderError):

        provider.generate_json("Test prompt")


def test_ollama_provider_handles_connection_error(
    monkeypatch,
):

    def mock_post(*args, **kwargs):

        raise httpx.ConnectError(
            "Connection refused"
        )

    monkeypatch.setattr(
        "app.document_processing.ollama_provider.httpx.post",
        mock_post,
    )

    provider = OllamaProvider()

    with pytest.raises(AIProviderError):

        provider.generate_json("Test prompt")


def test_ollama_provider_handles_invalid_api_response(
    monkeypatch,
):

    def mock_post(url, json, timeout):

        return httpx.Response(
            200,
            content=b"invalid-json",
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(
        "app.document_processing.ollama_provider.httpx.post",
        mock_post,
    )

    provider = OllamaProvider()

    with pytest.raises(AIProviderError):

        provider.generate_json("Test prompt")


def test_ollama_provider_rejects_empty_response(
    monkeypatch,
):

    def mock_post(url, json, timeout):

        return httpx.Response(
            200,
            json={
                "response": "",
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(
        "app.document_processing.ollama_provider.httpx.post",
        mock_post,
    )

    provider = OllamaProvider()

    with pytest.raises(AIProviderError):

        provider.generate_json("Test prompt")
