# Reddit draft — Teardown #001 — Product Factory v0.4: one YAML in, four deliverables out

Suggested subreddit: r/SideProject (a human chooses the final subreddit)

Suggested post:

Teardown #001 — Product Factory v0.4: one YAML in, four deliverables out

I wrote a teardown of a small local pipeline. The short version:

- One clinic profile YAML in, four Markdown deliverables out, regenerated in seconds
- A validation gate must PASS before any output is treated as usable
- LLM-assisted drafts fall back to plain templates when no API key is set
- Input and output stay fully separated so an orchestrator can be added later
- Every generated document stays a draft until a human reviews it

Happy to share details in the comments. Critique welcome.

---

**Boundary (do not remove)**

Draft only. Human review is required before this text is used anywhere.
This is not a product launch, not a safety guarantee, and not a security claim.
Generated locally. Nothing here is published or sent by any system; a human
must explicitly approve and perform every external action.
