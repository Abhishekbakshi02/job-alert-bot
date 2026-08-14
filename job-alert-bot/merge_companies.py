"""
Run right before committing companies.json, inside the GitHub Actions
workflow. Only does anything if THIS run actually removed dead
companies (removed_company_urls.json exists) - otherwise companies.json
was never rewritten locally, so there's nothing to merge or commit.

When there ARE removals: fetches the CURRENT remote companies.json
(which may have picked up manual additions made while this run was in
progress) and removes only the specific URLs this run found dead from
THAT list - rather than overwriting the remote with this run's stale
local snapshot, which would silently discard any manual edits made
during the run.
"""

import json
import os
import subprocess

COMPANIES_FILE = "companies.json"
REMOVED_MARKER_FILE = "removed_company_urls.json"

if not os.path.exists(REMOVED_MARKER_FILE):
    print("[INFO] No companies were removed this run - nothing to merge for companies.json")
else:
    with open(REMOVED_MARKER_FILE) as f:
        removed_urls = set(json.load(f))

    try:
        remote_content = subprocess.check_output(
            ["git", "show", "origin/main:companies.json"], text=True, stderr=subprocess.DEVNULL
        )
        remote_companies = json.loads(remote_content)
    except subprocess.CalledProcessError:
        with open(COMPANIES_FILE) as f:
            remote_companies = json.load(f)

    merged = [c for c in remote_companies if c["url"] not in removed_urls]

    with open(COMPANIES_FILE, "w") as f:
        json.dump(merged, f, indent=2)

    removed_count = len(remote_companies) - len(merged)
    print(f"[INFO] Merged companies.json with remote - removed {removed_count} dead compan(ies) found this run, "
          f"{len(merged)} total remaining (any manual additions on remote were preserved)")

    os.remove(REMOVED_MARKER_FILE)
