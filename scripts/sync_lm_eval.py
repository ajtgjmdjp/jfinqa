"""Check drift between ``lm_eval_tasks/`` and lm-eval upstream.

Fetches ``lm_eval/tasks/jfinqa/`` from
``EleutherAI/lm-evaluation-harness`` at a pinned commit (or a
user-supplied ref) and diffs each file against the local mirror.

Exit code:
  0  local is identical to upstream at the selected ref
  1  drift detected (prints unified diff)
  2  network / fetch error

Usage:
  python scripts/sync_lm_eval.py                   # diff against pinned ref
  python scripts/sync_lm_eval.py --ref main        # diff against current main
  python scripts/sync_lm_eval.py --ref main --apply

This is intentionally a manual tool rather than a CI gate so that
upstream changes do not break our CI unexpectedly.
"""

from __future__ import annotations

import argparse
import base64
import difflib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

UPSTREAM_REPO = "EleutherAI/lm-evaluation-harness"
UPSTREAM_PATH = "lm_eval/tasks/jfinqa"
# Commit of PR #3570 merge. Update this (and lm_eval_tasks/README.md)
# when back-syncing to a newer upstream revision.
DEFAULT_REF = "eb9253ae7ce21ef2027b94cf5c93c9b44e8aec32"
USER_AGENT = "jfinqa-sync-lm-eval"
MIRRORED_FILES = (
    "_jfinqa.yaml",
    "utils.py",
    "jfinqa_numerical.yaml",
    "jfinqa_consistency.yaml",
    "jfinqa_temporal.yaml",
)
LOCAL_DIR = Path(__file__).resolve().parent.parent / "lm_eval_tasks"


def _fetch(filename: str, ref: str) -> str:
    url = (
        f"https://api.github.com/repos/{UPSTREAM_REPO}"
        f"/contents/{UPSTREAM_PATH}/{filename}?ref={ref}"
    )
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read())
    return base64.b64decode(payload["content"]).decode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="overwrite local with upstream"
    )
    parser.add_argument(
        "--ref",
        default=DEFAULT_REF,
        help=f"git ref (commit/branch/tag) to fetch, default={DEFAULT_REF[:12]}",
    )
    args = parser.parse_args()

    print(f"Comparing against {UPSTREAM_REPO}@{args.ref}")
    drift = False
    for filename in MIRRORED_FILES:
        try:
            upstream = _fetch(filename, args.ref)
        except (urllib.error.URLError, KeyError, ValueError) as exc:
            print(f"ERROR: cannot fetch {filename}: {exc}", file=sys.stderr)
            return 2

        local_path = LOCAL_DIR / filename
        local = local_path.read_text(encoding="utf-8") if local_path.exists() else ""

        if upstream == local:
            print(f"OK        {filename}")
            continue

        drift = True
        if args.apply:
            local_path.write_text(upstream, encoding="utf-8")
            print(f"UPDATED   {filename}")
        else:
            print(f"DRIFT     {filename}")
            diff = difflib.unified_diff(
                local.splitlines(keepends=True),
                upstream.splitlines(keepends=True),
                fromfile=f"local/{filename}",
                tofile=f"upstream/{filename}",
            )
            sys.stdout.writelines(diff)

    return 1 if drift and not args.apply else 0


if __name__ == "__main__":
    sys.exit(main())
