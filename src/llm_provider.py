from abc import ABC, abstractmethod
from loguru import logger


class LlmProvider(ABC):
    """Abstract interface for LLM backend integrations."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
        """Send a prompt pair and return the model's response text."""


class AnthropicProvider(LlmProvider):
    def __init__(self, api_key: str, model: str):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        logger.debug(f"AnthropicProvider initialised — model: {model}")

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
        logger.debug("Calling Anthropic API...")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        usage = response.usage
        logger.debug(
            f"Anthropic — input: {usage.input_tokens} | output: {usage.output_tokens} "
            f"| total: {usage.input_tokens + usage.output_tokens} tokens"
        )
        return response.content[0].text


class GroqProvider(LlmProvider):
    def __init__(self, api_key: str, model: str):
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model
        logger.debug(f"GroqProvider initialised — model: {model}")

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
        logger.debug("Calling Groq API...")
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        logger.debug(f"Groq — model: {self.model}")
        return response.choices[0].message.content
