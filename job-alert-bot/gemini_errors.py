"""
Shared exception used by classifier.py and resume_tailor.py to signal
that Gemini itself appears unavailable (retries exhausted) - as opposed
to a company-specific failure. main.py treats this specially: it stops
making further Gemini calls for the rest of the run instead of retrying
the same failure for every remaining company.
"""


class GeminiUnavailable(Exception):
    pass
