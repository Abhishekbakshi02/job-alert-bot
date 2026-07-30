"""
Loads and saves the list of companies to check. Stored as plain JSON in
companies.json - just names and URLs, no Python syntax - so it's easy to
add, remove, or edit companies directly.
"""

import json

COMPANIES_FILE = "companies.json"


def load_companies() -> list[dict]:
    with open(COMPANIES_FILE) as f:
        return json.load(f)


def save_companies(companies: list[dict]) -> None:
    with open(COMPANIES_FILE, "w") as f:
        json.dump(companies, f, indent=2)
