#!/usr/bin/env python3
"""Repurpose a teardown Markdown file into local-only marketing drafts.

Local and deterministic by design:
- reads one Markdown file, writes Markdown drafts into --out
- never publishes, never sends, never calls external APIs
- every draft carries an explicit human-review boundary

Generating a draft is NOT approval. Only a human (Subaru) can approve any
external posting or contact. See docs/marketing/GATE1_REVIEW_CHECKLIST.md.
"""
import argparse
from pathlib import Path

MAX_POINTS = 5

DISCLAIMER = """\
---

**Boundary (do not remove)**

Draft only. Human review is required before this text is used anywhere.
This is not a product launch, not a safety guarantee, and not a security claim.
Generated locally. Nothing here is published or sent by any system; a human
must explicitly approve and perform every external action.\
"""

X_THREAD_TEMPLATE = """\
# X thread draft — {title}

{tweets}

{disclaimer}
"""

HACKER_NEWS_TEMPLATE = """\
# Hacker News draft — {title}

Suggested title: {title}

Suggested text:

I wrote a teardown of a small local pipeline. Key observations:

{bullets}

I would value critical feedback, especially on what is missing or overstated.

{disclaimer}
"""

REDDIT_TEMPLATE = """\
# Reddit draft — {title}

Suggested subreddit: r/SideProject (a human chooses the final subreddit)

Suggested post:

{title}

I wrote a teardown of a small local pipeline. The short version:

{bullets}

Happy to share details in the comments. Critique welcome.

{disclaimer}
"""

DEVTO_TEMPLATE = """\
---
title: "{title}"
published: false
tags: ["automation", "python", "teardown"]
---

# {title}

Working notes repurposed from the original teardown write-up.

{bullets}

{disclaimer}
"""

LINKEDIN_TEMPLATE = """\
# LinkedIn draft — {title}

I spent some time on a teardown: {title}.

What stood out:

{bullets}

If you are building something similar, I am happy to compare notes.

{disclaimer}
"""

DM_OUTREACH_TEMPLATE = """\
# DM outreach draft — {title}

Use only after a human selects the recipient and personally approves the
final text. No recipient list is attached to this draft.

Template (fill [NAME] and [CONTEXT] by hand):

Hi [NAME] — I put together a short teardown: "{title}".
One concrete takeaway: {first_point}
If this overlaps with [CONTEXT], I would value your critique. No pitch.

{disclaimer}
"""


def parse_teardown(text):
    """Extract the first H1 as title and the first MAX_POINTS bullets."""
    title = "Teardown"
    found_title = False
    points = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not found_title:
            title = stripped[2:].strip()
            found_title = True
        elif stripped.startswith("- ") and len(points) < MAX_POINTS:
            points.append(stripped[2:].strip())
    return title, points


def build_tweets(title, points):
    tweets = [
        f"1. {title} — notes from a hands-on teardown. "
        "Key takeaways in this thread."
    ]
    for i, point in enumerate(points, start=2):
        tweets.append(f"{i}. {point}")
    tweets.append(
        f"{len(points) + 2}. Full teardown is in the repo. "
        "Corrections and critique welcome."
    )
    return "\n".join(tweets)


def build_drafts(title, points):
    bullets = "\n".join(f"- {point}" for point in points)
    first_point = points[0] if points else title
    return {
        "x_thread.md": X_THREAD_TEMPLATE.format(
            title=title,
            tweets=build_tweets(title, points),
            disclaimer=DISCLAIMER,
        ),
        "hacker_news.md": HACKER_NEWS_TEMPLATE.format(
            title=title, bullets=bullets, disclaimer=DISCLAIMER
        ),
        "reddit.md": REDDIT_TEMPLATE.format(
            title=title, bullets=bullets, disclaimer=DISCLAIMER
        ),
        "devto.md": DEVTO_TEMPLATE.format(
            title=title, bullets=bullets, disclaimer=DISCLAIMER
        ),
        "linkedin.md": LINKEDIN_TEMPLATE.format(
            title=title, bullets=bullets, disclaimer=DISCLAIMER
        ),
        "dm_outreach.md": DM_OUTREACH_TEMPLATE.format(
            title=title, first_point=first_point, disclaimer=DISCLAIMER
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate local-only marketing drafts from a teardown."
    )
    parser.add_argument("source", help="Path to the teardown Markdown file")
    parser.add_argument("--out", required=True, help="Output directory for drafts")
    args = parser.parse_args(argv)

    text = Path(args.source).read_text(encoding="utf-8")
    title, points = parse_teardown(text)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, content in build_drafts(title, points).items():
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path}")

    print("Draft generation finished. Nothing was published or sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
