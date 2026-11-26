"""
AI provider interface.

Responsibilities:
1. Define a common interface for AI providers.
2. Keep document-processing code independent of a specific provider.
3. Allow future integration with OpenAI or other AI services.

The application communicates with providers through this interface.
"""

from abc import ABC, abstractmethod


class AIProviderError(Exception):
    """Raised when an AI provider cannot complete a request."""


class AIProvider(ABC):
    """
    Base interface for AI providers.

    Every AI provider must implement generate_json().

    This allows the application to switch providers without
    rewriting the extraction service.
    """

    @abstractmethod
    def generate_json(self, prompt: str) -> str:
        """
        Generate a JSON response from a supplied prompt.

        Args:
            prompt: Instructions and document content.

        Returns:
            Raw JSON response as a string.

        Raises:
            AIProviderError: If generation fails.
        """
        raise NotImplementedError