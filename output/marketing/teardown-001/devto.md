---
title: "Teardown #001 — Product Factory v0.4: one YAML in, four deliverables out"
published: false
tags: ["automation", "python", "teardown"]
---

# Teardown #001 — Product Factory v0.4: one YAML in, four deliverables out

Working notes repurposed from the original teardown write-up.

- One clinic profile YAML in, four Markdown deliverables out, regenerated in seconds
- A validation gate must PASS before any output is treated as usable
- LLM-assisted drafts fall back to plain templates when no API key is set
- Input and output stay fully separated so an orchestrator can be added later
- Every generated document stays a draft until a human reviews it

---

**Boundary (do not remove)**

Draft only. Human review is required before this text is used anywhere.
This is not a product launch, not a safety guarantee, and not a security claim.
Generated locally. Nothing here is published or sent by any system; a human
must explicitly approve and perform every external action.
