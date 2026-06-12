# Teardown #001 — Product Factory v0.4: one YAML in, four deliverables out

## What this is

Working notes from tearing down Product Factory v0.4, a small local pipeline
that turns one clinic profile YAML into four Markdown deliverables
(FAQ, review replies, recruiting copy, sales onepager).

## Key points

- One clinic profile YAML in, four Markdown deliverables out, regenerated in seconds
- A validation gate must PASS before any output is treated as usable
- LLM-assisted drafts fall back to plain templates when no API key is set
- Input and output stay fully separated so an orchestrator can be added later
- Every generated document stays a draft until a human reviews it

## What worked

The single-source-of-truth profile keeps regeneration cheap. Changing one
YAML file and re-running the generator is faster than editing four documents
by hand, and the validator catches missing sections immediately.

## What did not work

Template output reads flat without human editing. The validator proves
structure, not quality: a pack can PASS while still needing a rewrite.
Treating PASS as "ready to ship" was the biggest mistake of early runs.

## Honest framing

This is a workflow teardown, not a product launch. Nothing in here is a
safety guarantee or a security claim about the generated content. Every
artifact stays a draft until a human reviews and approves it.
