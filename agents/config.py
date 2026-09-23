"""LLM configuration - Google Gemini only (free-tier models).

Simplified from the original multi-provider setup: this app is built to run
on Google's Gemini API free tier, so Groq/OpenAI/Anthropic support was
removed. The Streamlit frontend sets ``GOOGLE_API_KEY`` / ``LLM_MODEL`` in
the process environment before building the graph, so every node's
``get_llm()`` call (no args) picks them up automatically.
"""

from __future__ import annotations

import os
import streamlit as st

from dotenv import load_dotenv

load_dotenv()

# Gemini models that are available on the free tier as of writing. Shown in
# the Streamlit sidebar as a dropdown.
FREE_MODELS: list[str] = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.0-flash",
]

DEFAULT_MODEL = FREE_MODELS[0]


GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

def get_llm(*, model: str | None = None, temperature: float = 0.0):
    """Return a ``ChatGoogleGenerativeAI`` instance for the configured model.

    Parameters
    ----------
    model:
        Overrides the model name. Falls back to the ``LLM_MODEL`` env var,
        then to :data:`DEFAULT_MODEL`.
    temperature:
        Sampling temperature. Defaults to ``0.0`` for deterministic output.

    Raises
    ------
    RuntimeError
        If ``GOOGLE_API_KEY`` is not set in the environment.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Enter your Gemini API key in the "
            "sidebar, or set it in a .env file."
        )

    model = model or os.getenv("LLM_MODEL") or DEFAULT_MODEL

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=model, temperature=temperature, api_key=api_key)
