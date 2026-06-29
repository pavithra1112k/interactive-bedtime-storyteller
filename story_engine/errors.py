class StoryEngineError(Exception):
    """Base error for story engine failures."""


class ConfigurationError(StoryEngineError):
    """Raised when local setup is missing or invalid."""


class ModelCallError(StoryEngineError):
    """Raised when the OpenAI call fails after retries."""


class ModelOutputError(StoryEngineError):
    """Raised when model output cannot be parsed."""

