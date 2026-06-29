"""
This file contains the function that calls the LLM. We are using the OpenAI API to call the model. I kept the template given 
in the assignment instructions.
"""

import os
import time

import openai

from story_engine.config import MAX_TOKENS
from story_engine.errors import ConfigurationError, ModelCallError


def call_model(prompt: str, temperature=0.1, max_tokens=MAX_TOKENS):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        raise ConfigurationError(
            "OPENAI_API_KEY is missing. Add your key to the local .env file."
        )

    openai.api_key = api_key
    last_error = None

    for attempt in range(1, 4):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            content = response.choices[0].message["content"]
            if not content or not content.strip():
                raise ModelCallError("Model returned an empty response.")

            return content

        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt)

    raise ModelCallError(f"OpenAI request failed after retries: {last_error}")
