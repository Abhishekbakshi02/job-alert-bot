import re


TARGET_TITLE_PATTERNS = [
    # AI / ML Engineering
    r"\bmachine[\s-]+learning engineer\b",
    r"\bml engineer\b",
    r"\bartificial intelligence engineer\b",
    r"\bai engineer\b",

    r"\bsoftware developer\b",
    r"\bSDE\b",
    r"\bsde1\b",
    r"\bFDE\b",
    r"\bforward deployment engineer\b",
    r"\bPython engineer\b",
    r"\bpython developer\b",

    # Applied AI / ML
    r"\bapplied (?:ai|ml|machine learning)\b",

    # LLM / Generative AI
    r"\bllm engineer\b",
    r"\bllm developer\b",
    r"\b(?:generative ai|gen(?:erative)? ai|genai) engineer\b",
    r"\bprompt engineer\b",

    # Deep Learning
    r"\bdeep learning engineer\b",
    r"\bdeep learning researcher\b",
    r"\bdeep learning scientist\b",

    # NLP
    r"\b(?:nlp|natural language processing) engineer\b",
    r"\b(?:nlp|natural language processing) researcher\b",

    # AI / ML Research
    r"\bai researcher\b",
    r"\bai research engineer\b",
    r"\bai research scientist\b",
    r"\bmachine learning researcher\b",
    r"\bmachine learning research engineer\b",
    r"\bmachine learning scientist\b",
    r"\bml researcher\b",
    r"\bml research engineer\b",
    r"\bml scientist\b",
    r"\bresearch engineer\b",
    r"\bresearch scientist\b",

    # MLOps / Infrastructure
    r"\bmlops engineer\b",
    r"\bml ops engineer\b",
    r"\bmachine learning platform engineer\b",
    r"\bml platform engineer\b",
    r"\bai platform engineer\b",
    r"\bml infrastructure engineer\b",
    r"\bai infrastructure engineer\b",

    # Robotics / Intelligent Systems
    r"\brobotics engineer\b",
    r"\brobotics (?:ai|machine learning) engineer\b",
    r"\brobotics research engineer\b",
    r"\bautonomous systems engineer\b",
    r"\bintelligent systems engineer\b",

    # AI Systems
    r"\bai systems engineer\b",
    r"\bmachine learning systems engineer\b",
    r"\bml systems engineer\b",

    # Data Science
    r"\bdata scientist\b",
    r"\bmachine learning data scientist\b",
    r"\bml data scientist\b",
    r"\bai data scientist\b",

    # AI Solutions
    r"\bai solutions engineer\b",
    r"\bmachine learning solutions engineer\b",
]


EXCLUDED_TITLE_PATTERNS = [
    r"\bintern\b",
    r"\binternship\b",
    r"\bvoice trainer\b",
    r"\bai trainer\b",
    r"\bdata trainer\b",
    r"\bsenior\b",
]


def title_matches(title: str) -> bool:
    title_lower = title.lower()

    # Reject exclusions first
    if any(re.search(pattern, title_lower) for pattern in EXCLUDED_TITLE_PATTERNS):
        return False

    # Check target roles
    return any(re.search(pattern, title_lower) for pattern in TARGET_TITLE_PATTERNS)
