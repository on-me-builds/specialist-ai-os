#!/usr/bin/env python3
"""Gate1 marketing review gate — local and deterministic.

Reads generated marketing drafts from a directory, verifies that every
draft carries the required human-review boundaries and contains no
auto-publish / auto-send wording, then writes a JSON review manifest.

This script never publishes, sends, or contacts anything external.
A PASS manifest is NOT approval: human approval is always still required,
and only a human (Subaru) can approve external posting or contact.
See docs/marketing/GATE1_REVIEW_CHECKLIST.md.
"""
import argparse
import json
import re
import sys
from pathlib import Path

DRAFT_FILES = [
    "x_thread.md",
    "hacker_news.md",
    "reddit.md",
    "devto.md",
    "linkedin.md",
    "dm_outreach.md",
]

# (check name, phrase that must appear in every draft)
REQUIRED_IN_ALL_DRAFTS = [
    ("draft_only_human_review_boundary", "Draft only. Human review is required"),
    ("not_a_product_launch", "not a product launch"),
    ("not_a_safety_guarantee", "not a safety guarantee"),
    ("not_a_security_claim", "not a security claim"),
]

# (check name, file, phrase that must appear in that file)
REQUIRED_IN_FILE = [
    ("devto_published_false", "devto.md", "published: false"),
    (
        "dm_outreach_human_recipient_approval",
        "dm_outreach.md",
        "Use only after a human selects the recipient",
    ),
]

FORBIDDEN_PATTERNS = [
    re.compile(r"auto[-_\s]?publish", re.IGNORECASE),
    re.compile(r"auto[-_\s]?send", re.IGNORECASE),
    re.compile(r"auto[-_\s]?post", re.IGNORECASE),
    re.compile(r"auto[-_\s]?submit", re.IGNORECASE),
    re.compile(r"automated\s+(submission|posting|publishing|sending)", re.IGNORECASE),
    re.compile(r"automatically\s+(publish|post|send|submit)\w*", re.IGNORECASE),
]

SAFE_TO_TRUST = re.compile(r"safe to trust", re.IGNORECASE)
# "safe to trust" is tolerated only on lines that clearly frame it as a
# rejected or failed claim.
REJECTION_CONTEXT = re.compile(
    r"(not|never|isn't|is not|was not|wasn't)\s+safe to trust"
    r"|rejected|failed|fails|do not trust|halt",
    re.IGNORECASE,
)


def run_checks(draft_dir):
    checks = []
    contents = {}
    missing = []
    for name in DRAFT_FILES:
        path = draft_dir / name
        if path.is_file():
            contents[name] = path.read_text(encoding="utf-8")
        else:
            missing.append(name)

    checks.append({
        "name": "all_draft_files_present",
        "status": "HALT" if missing else "PASS",
        "details": (
            "missing draft files: " + ", ".join(missing)
            if missing
            else f"all {len(DRAFT_FILES)} draft files present"
        ),
    })

    for check_name, phrase in REQUIRED_IN_ALL_DRAFTS:
        bad = sorted(
            [name for name, text in contents.items() if phrase not in text]
            + missing
        )
        checks.append({
            "name": check_name,
            "status": "HALT" if bad else "PASS",
            "details": (
                f'required phrase "{phrase}" missing from: ' + ", ".join(bad)
                if bad
                else f'required phrase "{phrase}" present in all drafts'
            ),
        })

    for check_name, file_name, phrase in REQUIRED_IN_FILE:
        text = contents.get(file_name)
        ok = text is not None and phrase in text
        checks.append({
            "name": check_name,
            "status": "PASS" if ok else "HALT",
            "details": (
                f'required phrase "{phrase}" present in {file_name}'
                if ok
                else f'{file_name} must contain "{phrase}"'
            ),
        })

    violations = []
    for name in sorted(contents):
        for pattern in FORBIDDEN_PATTERNS:
            match = pattern.search(contents[name])
            if match:
                violations.append(f'{name}: "{match.group(0)}"')
    checks.append({
        "name": "no_auto_publish_or_auto_send_claims",
        "status": "HALT" if violations else "PASS",
        "details": (
            "forbidden automation wording found -> " + "; ".join(violations)
            if violations
            else "no auto-publish / auto-send / automated submission wording found"
        ),
    })

    unqualified = []
    for name in sorted(contents):
        for line in contents[name].splitlines():
            if SAFE_TO_TRUST.search(line) and not REJECTION_CONTEXT.search(line):
                unqualified.append(f'{name}: "{line.strip()}"')
    checks.append({
        "name": "no_unqualified_safe_to_trust",
        "status": "HALT" if unqualified else "PASS",
        "details": (
            '"safe to trust" used without rejected/failed framing -> '
            + "; ".join(unqualified)
            if unqualified
            else 'no unqualified "safe to trust" claims found'
        ),
    })

    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Gate1 local review gate for marketing drafts."
    )
    parser.add_argument("draft_dir", help="Directory containing generated drafts")
    parser.add_argument("--out", required=True, help="Path for the JSON manifest")
    args = parser.parse_args(argv)

    checks = run_checks(Path(args.draft_dir))
    status = "PASS" if all(c["status"] == "PASS" for c in checks) else "HALT"

    manifest = {
        "status": status,
        "draft_dir": args.draft_dir,
        "checks": checks,
        "human_approval_required": True,
        "external_action_taken": False,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Gate1 review: {status} ({len(checks)} checks) -> {out_path}")
    if status == "HALT":
        for check in checks:
            if check["status"] == "HALT":
                print(f"  HALT {check['name']}: {check['details']}")
    print(
        "No external action was taken. Human approval is still required "
        "for any external use."
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
