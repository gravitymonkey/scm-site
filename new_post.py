#!/usr/bin/env python3
"""
Create a new draft post with pre-filled frontmatter.

Usage:
    python3 new_post.py "My Post Title"
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
POSTS_DIR = ROOT / "content" / "posts"
AUTHORS_DIR = ROOT / "content" / "authors"

sys.path.insert(0, str(ROOT))
from build import slugify  # noqa: E402


def default_author():
    authors = sorted(AUTHORS_DIR.glob("*.yml"))
    return authors[0].stem if authors else "jason"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 new_post.py \"Post Title\"")
        sys.exit(1)

    title = " ".join(sys.argv[1:])
    slug = slugify(title)
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    author = default_author()

    dest = POSTS_DIR / ("%s.md" % slug)
    if dest.exists():
        print("Error: %s already exists" % dest)
        sys.exit(1)

    title_yaml = yaml.dump(title, default_flow_style=None).strip()
    content = """\
---
title: {title}
slug: {slug}
author: {author}
tags: []
date: {date}
updated: {date}
draft: true
---

Write your post here.
""".format(title=title_yaml, slug=slug, author=author, date=date_str)

    dest.write_text(content)
    print("Created: %s" % dest.relative_to(ROOT))
    print("Preview: python3 dev_server.py --drafts")


if __name__ == "__main__":
    main()
