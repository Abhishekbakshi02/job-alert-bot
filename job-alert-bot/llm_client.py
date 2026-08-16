"""
Unified client for calling any OpenAI-compatible chat completions API.
Tries a chain of free-tier providers in order - when one is rate
limited or unavailable, automatically falls through to the next.

Two different orderings are used for two different reasons:
  - CLASSIFY_PROVIDERS (Groq first): classification happens often - once
    per company with title matches - so it needs Groq's high daily quota
    to handle the volume. Gemini is a fallback if Groq is unavailable.
  - TAILOR_PROVIDERS (Gemini first): resume tailoring only happens for
    confirmed matches - a small number of calls - and output quality
    matters most here, so Gemini's scarce-but-higher-quality output is
    worth spending on the few calls this actually needs. Groq is the
    fallback if Gemini's daily quota runs out.

max_tokens is a PARAMETER, not a blanket constant - Groq's free tier
enforces a tokens-PER-MINUTE cap per model (as low as 6,000-10,000 on
some models), and that limit is charged against the RESERVED max_tokens
budget, not just what's actually generated. A classify call (small
JSON output) and a tailor call (bigger JSON output) need very different
budgets - reserving too much on every call wastes headroom and can
trigger 413 "request too large" errors even on tiny requests.
"""

import os
import time
import requests

from gemini_errors import GeminiUnavailable

GEMINI = {
    "name": "Gemini",
    "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    "api_key_env": "GEMINI_API_KEY",
    "model": "gemini-3.6-flash",
}
GROQ = {
    "name": "Groq",
    "url": "https://api.groq.com/openai/v1/chat/completions",
    "api_key_env": "GROQ_API_KEY",
    "model": "openai/gpt-oss-120b",
}
NEMOTRON = {
    "name": "Nemotron",
    "url": "https://integrate.api.nvidia.com/v1/chat/completions",
    "api_key_env": "NVIDIA_API_KEY",
    "model": "nvidia/nemotron-3-super-120b-a12b",
}

# Gemini deliberately excluded here - reserved for resume tailoring only.
CLASSIFY_PROVIDERS = [NEMOTRON, GROQ]
TAILOR_PROVIDERS = [GEMINI, GROQ]



def _call_one_provider(provider: dict, prompt: str, max_retries: int, max_tokens: int) -> str:
    api_key = os.environ.get(provider["api_key_env"], "").strip()
    if not api_key:
        raise GeminiUnavailable(f"{provider['name']}: no API key set ({provider['api_key_env']})")

    for attempt in range(max_retries):
        response = requests.post(
            provider["url"],
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": provider["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": max_tokens,
            },
            timeout=60,
        )

        if response.status_code == 429:
            wait_seconds = 10 * (attempt + 1)
            print(f"[INFO] {provider['name']} rate limit hit, waiting {wait_seconds}s (retry {attempt + 1}/{max_retries})")
            time.sleep(wait_seconds)
            continue

        if response.status_code == 413:
            print(f"[WARN] {provider['name']} rejected the request as too large (413) - "
                  f"falling through to next provider immediately")
            raise GeminiUnavailable(f"{provider['name']}: request too large (413)")

        if response.status_code in (500, 502, 503, 504):
            wait_seconds = 8 * (attempt + 1)
            print(f"[INFO] {provider['name']} returned {response.status_code} (temporary issue), "
                  f"waiting {wait_seconds}s (retry {attempt + 1}/{max_retries})")
            time.sleep(wait_seconds)
            continue

        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    raise GeminiUnavailable(f"{provider['name']} failed after {max_retries} retries")


def call_llm(prompt: str, providers: list, max_retries: int = 5, max_tokens: int = 2000) -> str:
    errors = []
    for provider in providers:
        try:
            print(f"[INFO] Trying {provider['name']}...")
            return _call_one_provider(provider, prompt, max_retries, max_tokens)
        except GeminiUnavailable as e:
            print(f"[INFO] {provider['name']} unavailable ({e}) - falling through to next provider")
            errors.append(str(e))
            continue

    raise GeminiUnavailable(f"All providers unavailable: {'; '.join(errors)}")
