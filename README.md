# Stochastic Code Monkeys

Static site source for [stochasticcodemonkeys.com](https://www.stochasticcodemonkeys.com).

This repo uses a small Python build script to turn Markdown, YAML metadata, templates, and static assets into a deployable site under `dist/`.

## Project Layout

```text
.
├── build.py                # Static site generator
├── dev_server.py           # Dev server with file watching and auto-rebuild
├── new_post.py             # Scaffold a new draft post
├── content/                # Markdown content and site metadata
│   ├── authors/
│   ├── pages/
│   ├── posts/
│   ├── site.yml
│   └── tags.yml
├── static/                 # Copied directly into the built site
├── templates/              # HTML templates
├── serve-flat-site.sh      # One-shot build and serve (no watching)
└── package-flat-site.sh    # Build and package dist/ as a tarball
```

## Requirements

- Python 3
- PyYAML available to `python3`

If needed:

```bash
python3 -m pip install pyyaml
```

## Local Development

Use the dev server for day-to-day writing. It builds the site on startup, then watches `content/`, `templates/`, and `static/` for changes and rebuilds automatically.

```bash
python3 dev_server.py
```

Default preview URL:

```text
http://localhost:9405
```

Use a different port:

```bash
python3 dev_server.py 8080
```

To include draft posts in the preview:

```bash
python3 dev_server.py --drafts
```

## Content Workflow

### Create a new post

Scaffold a new draft post with pre-filled frontmatter:

```bash
python3 new_post.py "My Post Title"
```

This creates `content/posts/my-post-title.md` with `draft: true` set. Open the file and write the body. The dev server will pick up changes automatically if it's running.

### Publish a post

Remove (or delete) the `draft: true` line from the post's frontmatter and rebuild.

### Draft posts

Any post or page with `draft: true` in its frontmatter is excluded from normal builds. To preview drafts locally:

```bash
python3 dev_server.py --drafts
```

Draft posts rendered in draft mode display a visible "DRAFT" banner at the top of the page.

### Writing posts manually

If not using `new_post.py`, add a Markdown file under `content/posts/` with YAML frontmatter:

```yaml
---
title: Post Title
slug: post-slug
author: jason
tags:
  - field-notes
date: 2026-01-01T00:00:00+00:00
updated: 2026-01-01T00:00:00+00:00
---
```

### New page

Add a Markdown file under `content/pages/` with frontmatter including at least `title`, `slug`, `author`, `date`, and `updated`.

### Images

Put source images in `static/assets/images/`. Reference them in Markdown with paths like `/assets/images/example.png`. The build generates optimized derivatives automatically (see Image Pipeline).

### Metadata

- `content/site.yml` — site-wide metadata and canonical URL
- `content/tags.yml` — tag labels and descriptions
- `content/authors/` — author records used by posts and author pages

## Build

To build without serving:

```bash
python3 build.py
```

To build including drafts:

```bash
python3 build.py --drafts
```

Build output is written to `dist/`. The build emits:

- Homepage and content routes
- Post, page, tag, and author pages
- `feed.xml`
- `sitemap.xml`
- `llms.txt`
- `robots.txt`
- `.htaccess`

## Packaging

Create a deployable tarball containing `dist/`:

```bash
./package-flat-site.sh
```

This writes `flat-site-dist.tar.gz`.

## Image Pipeline

During the build, the generator creates optimized derivatives in `dist/assets/images/` for:

- post and page feature images (with responsive `srcset` variants)
- Markdown image embeds
- raw local `<img>` tags inside Markdown
- the repeated header/footer background tile

Current presets:

- feature images: max width `1400px`
- inline content images: max width `1200px`
- background tile: max width `220px`

The built pages reference generated derivatives automatically. Original source files are omitted from `dist/` when a derivative replaces them.

## Notes

- `static/` is copied into `dist/` during the build.
- `dist/` and `flat-site-dist.tar.gz` are generated artifacts and are ignored by Git.
- The Markdown renderer is intentionally minimal and supports headings, paragraphs, emphasis, links, images, lists, blockquotes, fenced code blocks, and raw HTML blocks.
