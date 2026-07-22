"""Lazy LLM configuration for OpenAI-compatible providers."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# LangGraph workers may inherit stale variables from a previous dev-server run.
# The project-local .env is the explicit source of truth for local development.
load_dotenv(override=True)

def is_configured() -> bool:
    """Return whether an LLM API key is available."""
    return bool(os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY"))


@lru_cache(maxsize=1)
def get_model() -> ChatOpenAI:
    """Create the configured LLM only when a node needs it."""
    api_key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing LLM_API_KEY or DEEPSEEK_API_KEY.")
    model_name = os.getenv("LLM_MODEL") or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL")
    return ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
    )
