# Gate1 Review Checklist — Marketing Drafts

Gate1 is a local, deterministic review gate for marketing drafts generated
by `marketing/content_repurposer.py`. It reads files, checks text, and
writes a JSON manifest. It takes no external action of any kind.

## Non-negotiable boundaries

1. **Draft generation does NOT equal approval.**
   `content_repurposer.py` producing files means nothing more than "text
   exists on disk". No draft is publishable because it was generated.
2. **A review manifest does NOT equal approval.**
   `review_gate.py` writing `"status": "PASS"` means only that the
   mechanical checks below passed. Every manifest carries
   `"human_approval_required": true` regardless of status.
3. **Only Subaru can approve external posting or contact.**
   Publishing a post, submitting to an aggregator, or contacting any
   person (including DMs) requires Subaru's explicit, per-item approval.
4. **Roles are separated:** Code implements, Codex reviews, Subaru approves.
5. **No agent may approve its own irreversible external action.**
   The agent that wrote or modified a draft can never be the one that
   signs off on sending it. Irreversible external actions always cross a
   human approval boundary first.

## What the gate checks

For every draft (`x_thread.md`, `hacker_news.md`, `reddit.md`, `devto.md`,
`linkedin.md`, `dm_outreach.md`):

- [ ] Contains the boundary "Draft only. Human review is required"
- [ ] States it is "not a product launch"
- [ ] States it is "not a safety guarantee"
- [ ] States it is "not a security claim"
- [ ] Contains no auto-publish / auto-send / automated submission wording
- [ ] Contains no "safe to trust" claim, unless the line clearly frames it
      as a rejected or failed claim

File-specific:

- [ ] `devto.md` contains `published: false` (dev.to front matter stays
      in draft mode)
- [ ] `dm_outreach.md` contains "Use only after a human selects the
      recipient" (no recipient lists, no bulk sending)

Any failed check sets the manifest status to `HALT` and the script exits
non-zero.

## How to run

```bash
# 1. Generate drafts (local only)
python marketing/content_repurposer.py teardowns/teardown-001.md --out output/marketing/teardown-001

# 2. Run the gate (local only)
python marketing/review_gate.py output/marketing/teardown-001 --out output/marketing/teardown-001/review_manifest.json

# 3. Run the tests
pytest -q
```

## Reading the manifest

- `"status": "PASS"` — drafts carry the required boundaries and are ready
  for **human** review. Nothing is approved.
- `"status": "HALT"` — at least one check failed. Fix the draft or the
  generator and re-run the gate. Do not hand a HALT pack to review.
- `"external_action_taken": false` — always. If this is ever not false,
  treat it as an incident, not a feature.

## After a PASS

A PASS manifest moves a draft to Subaru's review queue and nothing else.
Subaru edits or rejects freely; approval is per item and per channel, given
explicitly, and only by Subaru.
