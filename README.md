# Stochastic Code Monkeys

Static site source for [stochasticcodemonkeys.com](https://www.stochasticcodemonkeys.com).

This repo uses a small Python build script to turn Markdown, YAML metadata, templates, and static assets into a deployable site under `dist/`.

## Project Layout

```text
.
├── build.py                # Static site generator
├── content/                # Markdown content and site metadata
│   ├── authors/
│   ├── pages/
│   ├── posts/
│   ├── site.yml
│   └── tags.yml
├── static/                 # Copied directly into the built site
├── templates/              # HTML templates
├── serve-flat-site.sh      # Build and serve locally
└── package-flat-site.sh    # Build and package dist/ as a tarball
```

## Requirements

- Python 3
- PyYAML available to `python3`

If needed:

```bash
python3 -m pip install pyyaml
```

## Build

Run the generator from the repo root:

```bash
python3 build.py
```

Build output is written to `dist/`.

The build emits:

- Homepage and content routes
- Post, page, tag, and author pages
- `feed.xml`
- `sitemap.xml`
- `robots.txt`
- `.htaccess`

## Local Preview

Build and serve the site locally:

```bash
./serve-flat-site.sh
```

Default preview URL:

```text
http://localhost:9405
```

Use a different port if needed:

```bash
PORT=9410 ./serve-flat-site.sh
```

## Packaging

Create a deployable tarball containing `dist/`:

```bash
./package-flat-site.sh
```

This writes:

```text
flat-site-dist.tar.gz
```

## Content Workflow

### New post

1. Add a Markdown file under `content/posts/`.
2. Include YAML front matter with at least `title`, `slug`, `author`, `tags`, `date`, and `updated`.
3. Write the body in Markdown.
4. Put local images in `static/assets/images/`.
5. Reference site images with paths like `/assets/images/example.png`.
6. Run `python3 build.py`.

### New page

1. Add a Markdown file under `content/pages/`.
2. Include front matter with at least `title`, `slug`, `author`, `date`, and `updated`.
3. Write the body in Markdown.
4. Run `python3 build.py`.

### Metadata

- `content/site.yml` controls site-wide metadata and canonical URLs.
- `content/tags.yml` defines tag labels and descriptions.
- `content/authors/` defines author records used by posts and author pages.

## Notes

- `static/` is copied into `dist/` during the build.
- `dist/` and `flat-site-dist.tar.gz` are generated artifacts and are ignored by Git.
- The Markdown renderer is intentionally minimal and supports headings, paragraphs, emphasis, links, images, lists, blockquotes, fenced code blocks, and raw HTML blocks.
