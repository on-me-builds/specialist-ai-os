"""Tests for the Gate1 marketing review gate.

Runs the real CLI scripts in subprocesses against drafts generated into a
temporary directory. Everything is local; nothing is published or sent.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPURPOSER = REPO_ROOT / "marketing" / "content_repurposer.py"
REVIEW_GATE = REPO_ROOT / "marketing" / "review_gate.py"
TEARDOWN = REPO_ROOT / "teardowns" / "teardown-001.md"


def generate_drafts(tmp_path):
    draft_dir = tmp_path / "drafts"
    subprocess.run(
        [sys.executable, str(REPURPOSER), str(TEARDOWN), "--out", str(draft_dir)],
        check=True,
        capture_output=True,
        text=True,
    )
    return draft_dir


def run_gate(draft_dir):
    manifest_path = draft_dir / "review_manifest.json"
    proc = subprocess.run(
        [sys.executable, str(REVIEW_GATE), str(draft_dir), "--out", str(manifest_path)],
        capture_output=True,
        text=True,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return proc, manifest


def check_by_name(manifest, name):
    return next(c for c in manifest["checks"] if c["name"] == name)


def replace_in_file(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_generated_drafts_pass(tmp_path):
    draft_dir = generate_drafts(tmp_path)
    proc, manifest = run_gate(draft_dir)
    assert proc.returncode == 0
    assert manifest["status"] == "PASS"
    assert manifest["human_approval_required"] is True
    assert manifest["external_action_taken"] is False
    assert all(c["status"] == "PASS" for c in manifest["checks"])


def test_missing_draft_only_boundary_halts(tmp_path):
    draft_dir = generate_drafts(tmp_path)
    replace_in_file(
        draft_dir / "x_thread.md",
        "Draft only. Human review is required",
        "Looks good",
    )
    proc, manifest = run_gate(draft_dir)
    assert proc.returncode == 1
    assert manifest["status"] == "HALT"
    halted = check_by_name(manifest, "draft_only_human_review_boundary")
    assert halted["status"] == "HALT"
    assert "x_thread.md" in halted["details"]


def test_devto_missing_published_false_halts(tmp_path):
    draft_dir = generate_drafts(tmp_path)
    replace_in_file(draft_dir / "devto.md", "published: false", "published: true")
    proc, manifest = run_gate(draft_dir)
    assert proc.returncode == 1
    assert manifest["status"] == "HALT"
    assert check_by_name(manifest, "devto_published_false")["status"] == "HALT"


def test_dm_outreach_missing_recipient_warning_halts(tmp_path):
    draft_dir = generate_drafts(tmp_path)
    replace_in_file(
        draft_dir / "dm_outreach.md",
        "Use only after a human selects the recipient",
        "Send to whoever seems relevant",
    )
    proc, manifest = run_gate(draft_dir)
    assert proc.returncode == 1
    assert manifest["status"] == "HALT"
    halted = check_by_name(manifest, "dm_outreach_human_recipient_approval")
    assert halted["status"] == "HALT"


def test_forbidden_auto_send_wording_halts(tmp_path):
    draft_dir = generate_drafts(tmp_path)
    with (draft_dir / "linkedin.md").open("a", encoding="utf-8") as f:
        f.write("\nThis post will auto-send to all contacts at 9am.\n")
    proc, manifest = run_gate(draft_dir)
    assert proc.returncode == 1
    assert manifest["status"] == "HALT"
    halted = check_by_name(manifest, "no_auto_publish_or_auto_send_claims")
    assert halted["status"] == "HALT"
    assert "linkedin.md" in halted["details"]
