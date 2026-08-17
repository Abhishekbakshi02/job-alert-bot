import re

TITLE_KEYWORDS = [
    # Core ML/AI
    r"machine learning", r"\bml\b", r"artificial intelligence", r"\bai\b",
    r"deep learning", r"neural network",
    # LLM/GenAI specific
    r"\bllm\b", r"large language model", r"generative ai", r"\bgenai\b",
    r"nlp", r"natural language processing",
    # Applied/research roles
    r"applied scientist", r"research engineer", r"research scientist",
    r"applied ai", r"applied ml",
    # Adjacent
    r"computer vision", r"data scientist", r"mlops",
    r"prompt engineer", r"ai research",
]

pattern = re.compile("|".join(TITLE_KEYWORDS), re.IGNORECASE)

def title_matches(title: str) -> bool:
    return bool(pattern.search(title))
