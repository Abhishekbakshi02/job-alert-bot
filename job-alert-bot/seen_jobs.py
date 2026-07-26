"""
Keeps track of which job listings we've already processed, so re-running
the check every day doesn't re-email the same jobs. The list is saved to
a JSON file that the GitHub Action commits back to the repo after every
run.
"""

import json
import os

SEEN_FILE = "seen_jobs.json"


def load_seen() -> set:
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE) as f:
        return set(json.load(f))


def save_seen(seen: set) -> None:
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(seen), f, indent=2)
