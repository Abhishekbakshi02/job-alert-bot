"""
Run right before committing seen_jobs.json, inside the GitHub Actions
workflow. Fetches whatever version is CURRENTLY on the remote (which
may have moved since this run's checkout - another run, or a manual
edit) and unions it with what this run just computed locally, so an
update from elsewhere is never silently lost or overwritten.

seen_jobs.json is just a set of URLs, so a union is always the correct
merge - there's no meaningful "conflict" to resolve, unlike a normal
git merge.
"""

import json
import subprocess

SEEN_FILE = "seen_jobs.json"

try:
    remote_content = subprocess.check_output(
        ["git", "show", "origin/main:seen_jobs.json"], text=True, stderr=subprocess.DEVNULL
    )
    remote_seen = set(json.loads(remote_content))
except subprocess.CalledProcessError:
    remote_seen = set()

with open(SEEN_FILE) as f:
    local_seen = set(json.load(f))

merged = sorted(remote_seen | local_seen)

with open(SEEN_FILE, "w") as f:
    json.dump(merged, f, indent=2)

added_from_remote = len(remote_seen - local_seen)
print(f"[INFO] Merged seen_jobs.json with remote - picked up {added_from_remote} entr(ies) "
      f"saved by another run/edit, {len(merged)} total")
