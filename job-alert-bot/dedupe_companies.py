"""
Standalone script - not part of the daily job-check pipeline. Removes
duplicate entries from companies.json, matched by URL (the identifier
used everywhere else in the pipeline) since that's what actually causes
duplicate re-processing/re-emailing within a single run. Keeps the
first occurrence of each URL, drops the rest.
"""

import json

COMPANIES_FILE = "companies.json"


def main():
    with open(COMPANIES_FILE) as f:
        companies = json.load(f)

    seen_urls = set()
    deduped = []
    removed = []

    for company in companies:
        url = company.get("url", "").strip().rstrip("/")
        if url in seen_urls:
            removed.append(company.get("name", url))
            continue
        seen_urls.add(url)
        deduped.append(company)

    if removed:
        with open(COMPANIES_FILE, "w") as f:
            json.dump(deduped, f, indent=2)
        print(f"[INFO] Removed {len(removed)} duplicate compan(ies): {', '.join(removed)}")
        print(f"[INFO] {len(deduped)} unique compan(ies) remaining")
    else:
        print(f"[INFO] No duplicates found - {len(companies)} compan(ies), all unique")


if __name__ == "__main__":
    main()
