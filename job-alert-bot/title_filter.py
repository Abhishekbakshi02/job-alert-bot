"""
Shared title-matching logic used by every platform-specific fetcher
(Greenhouse, Lever, Ashby, etc.) so the keyword list only lives in one
place.
"""

TARGET_TITLE_KEYWORDS = [
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "llm engineer",
    "applied ai",
    "applied ml",
    "ai/ml engineer",
    "prompt engineer"
]


def title_matches(title: str) -> bool:
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in TARGET_TITLE_KEYWORDS)
