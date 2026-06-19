#!/usr/bin/env python3
"""Ingest uutils/findutils external-testsuite results into the tracking JSON.

Since findutils commit bb6a5ba (June 2026) the compat.yml workflow no longer
publishes a date-keyed summary artifact. It now uploads a per-test result:

    gnu-full-result -> findutils-gnu-full-result.json
    bfs-full-result -> bfs-full-result.json

each shaped as:

    {"summary": {"total": N, "passed": P, "failed": F, "skipped": S},
     "tests": [{"name": "...", "status": "PASS|FAIL|SKIP"}, ...]}

This script fetches recent successful compat.yml runs on the findutils default
branch, and for every run not already recorded (keyed by commit sha) downloads
the suite artifact and appends a summary entry compatible with graph.py:

    "<RFC 2822 date>": {"sha", "total", "pass", "skip", "fail"[, "xpass", "error"]}

It is idempotent: runs whose sha is already present are skipped, so it both
backfills missed history and serves as the daily updater.
"""

import argparse
import datetime
import json
import subprocess
import sys
import tempfile
from email.utils import format_datetime
from pathlib import Path

REPO = "uutils/findutils"

SUITES = {
    "gnu": {
        "artifact": "gnu-full-result",
        "file": "findutils-gnu-full-result.json",
        "result": "gnu-result.json",
        # The per-test JSON folds unexpected passes / errors into FAIL, so these
        # are always 0 now; kept for backward compatibility with graph.py.
        "extra": {"xpass": "0", "error": "0"},
    },
    "bfs": {
        "artifact": "bfs-full-result",
        "file": "bfs-full-result.json",
        "result": "bfs-result.json",
        "extra": {},
    },
}


def gh_api(args):
    out = subprocess.run(
        ["gh", "api", *args], capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


def list_runs(branch, since):
    """Successful compat.yml runs on `branch`, newest first, created >= since."""
    runs = gh_api(
        [
            "-X", "GET",
            f"repos/{REPO}/actions/workflows/compat.yml/runs",
            "-f", f"branch={branch}",
            "-f", "status=success",
            "-f", "per_page=100",
            "--jq", ".workflow_runs",
        ]
    )
    return [r for r in runs if r["created_at"] >= since]


def download_summary(run_id, suite):
    """Download the suite artifact for `run_id` and return its summary dict, or
    None if the artifact is missing/expired."""
    spec = SUITES[suite]
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            ["gh", "run", "download", str(run_id),
             "-R", REPO, "-n", spec["artifact"], "-D", tmp],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            sys.stderr.write(
                f"  ! no {spec['artifact']} for run {run_id}: "
                f"{proc.stderr.strip()}\n"
            )
            return None
        matches = list(Path(tmp).rglob(spec["file"]))
        if not matches:
            sys.stderr.write(f"  ! {spec['file']} missing in artifact\n")
            return None
        return json.loads(matches[0].read_text())["summary"]


def entry(summary, sha, extra):
    e = {
        "sha": sha,
        "total": str(summary["total"]),
        "pass": str(summary["passed"]),
        "skip": str(summary["skipped"]),
        "fail": str(summary["failed"]),
    }
    e.update(extra)
    return e


def date_key(created_at):
    dt = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return format_datetime(dt)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("suite", choices=sorted(SUITES))
    ap.add_argument(
        "--since", default="2026-06-13",
        help="only consider runs created on/after this ISO date (default: %(default)s)",
    )
    ap.add_argument("--branch", default="main", help="findutils branch (default: %(default)s)")
    args = ap.parse_args()

    spec = SUITES[args.suite]
    path = Path(spec["result"])
    data = json.loads(path.read_text())
    known_shas = {v.get("sha") for v in data.values()}

    runs = list_runs(args.branch, args.since)
    # Oldest first so entries are appended in chronological order.
    runs.sort(key=lambda r: r["created_at"])

    added = 0
    for run in runs:
        sha = run["head_sha"]
        if sha in known_shas:
            continue
        summary = download_summary(run["id"], args.suite)
        if summary is None:
            continue
        key = date_key(run["created_at"])
        if key in data:
            continue
        data[key] = entry(summary, sha, spec["extra"])
        known_shas.add(sha)
        added += 1
        print(f"  + {key}  {sha[:12]}  {data[key]}")

    if added:
        path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"{args.suite}: added {added} entr{'y' if added == 1 else 'ies'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
