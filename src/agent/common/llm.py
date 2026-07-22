"""Lazy LLM configuration for OpenAI-compatible providers."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def is_configured() -> bool:
    """Return whether an LLM API key is available."""
    return bool(os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY"))


@lru_cache(maxsize=1)
def get_model() -> ChatOpenAI:
    """Create the configured LLM only when a node needs it."""
    api_key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing LLM_API_KEY or DEEPSEEK_API_KEY.")
    return ChatOpenAI(
        model=os.getenv("LLM_MODEL") or os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        base_url=os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL"),
        api_key=api_key,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
    )
