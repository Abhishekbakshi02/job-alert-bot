"""
Shared title-matching logic used by every platform-specific fetcher.
Two layers: a positive list (role must match one of these) and an
exclusion list (reject immediately regardless of positive matches) -
the exclusions are enforced here, deterministically, rather than left
to the AI classifier to catch every time. Cheaper (no wasted API call)
and more reliable (not dependent on model judgment) for categories that
are almost always identifiable from the title alone.
"""

TARGET_TITLE_KEYWORDS = [
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "llm engineer",
    "applied ai",
    "applied ml",
    "AI Systems Engineer"
]

EXCLUDED_TITLE_KEYWORDS = [
    "intern",
    "internship",
    "voice trainer",
    "ai trainer",
    "data trainer",
]


def title_matches(title: str) -> bool:
    title_lower = title.lower()
    if any(excluded in title_lower for excluded in EXCLUDED_TITLE_KEYWORDS):
        return False
    return any(keyword in title_lower for keyword in TARGET_TITLE_KEYWORDS)
