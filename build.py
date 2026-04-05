#!/usr/bin/env python3
import html
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

import yaml


ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DIST = ROOT / "dist"


def load_yaml(path):
    return yaml.safe_load(path.read_text()) or {}


def load_template(name):
    return Template((TEMPLATES / name).read_text())


def parse_front_matter(text):
    if not text.startswith("---\n"):
        return {}, text
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text
    return yaml.safe_load(parts[0][4:]) or {}, parts[1]


def read_markdown_doc(path):
    metadata, body = parse_front_matter(path.read_text())
    metadata["body_markdown"] = body.strip() + "\n"
    return metadata


def strip_tags(value):
    return re.sub(r"<[^>]+>", "", value)


def slugify(value):
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def parse_date(value):
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def isoformat(value):
    if not value:
        return ""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def human_date(value):
    return value.strftime("%Y-%m-%d")


def atom_date(value):
    return value.astimezone(timezone.utc).strftime("%a %b %d %Y %H:%M:%S GMT+0000 (Coordinated Universal Time)")


def absolute_url(site, path):
    return site["url"].rstrip("/") + path


def html_attr(value):
    return html.escape(value or "", quote=True)


def read_time_minutes(markdown_text):
    plain = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", markdown_text)
    plain = re.sub(r"\[[^\]]+\]\([^)]+\)", "", plain)
    plain = re.sub(r"[#>*_`-]", " ", plain)
    words = [word for word in plain.split() if word]
    return max(1, (len(words) + 199) // 200)


def excerpt_from_markdown(markdown_text, limit=220):
    rendered = strip_tags(render_markdown(markdown_text))
    rendered = re.sub(r"\s+", " ", rendered).strip()
    if len(rendered) <= limit:
        return rendered
    return rendered[: limit - 1].rsplit(" ", 1)[0] + "…"


def apply_inline_markup(text):
    code_spans = []

    def store_code(match):
        code_spans.append("<code>%s</code>" % html.escape(match.group(1)))
        return "@@CODE%s@@" % (len(code_spans) - 1)

    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", store_code, text)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<em>\1</em>", text)
    for index, code_html in enumerate(code_spans):
        text = text.replace("@@CODE%s@@" % index, code_html)
    return text


def render_markdown(markdown_text):
    blocks = []
    current = []
    in_code = False
    code_lines = []

    def flush_current():
        nonlocal current
        if current:
            blocks.append(("text", current))
            current = []

    for line in markdown_text.splitlines():
        if line.startswith("```"):
            if in_code:
                blocks.append(("code", code_lines[:]))
                code_lines = []
                in_code = False
            else:
                flush_current()
                in_code = True
                code_lines = []
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            flush_current()
            continue

        current.append(line.rstrip())

    if in_code:
        blocks.append(("code", code_lines[:]))
    flush_current()

    rendered = []
    for kind, lines in blocks:
        if kind == "code":
            rendered.append("<pre><code>%s</code></pre>" % html.escape("\n".join(lines)))
            continue

        first = lines[0].strip()
        whole = "\n".join(lines).strip()

        if whole.startswith("<") and whole.endswith(">"):
            rendered.append(whole)
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", first)
        if heading and len(lines) == 1:
            level = len(heading.group(1))
            rendered.append("<h%s>%s</h%s>" % (level, apply_inline_markup(heading.group(2).strip()), level))
            continue

        image_only = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", first)
        if image_only and len(lines) == 1:
            alt, src = image_only.groups()
            rendered.append(
                '<figure class="kg-card kg-image-card"><img src="%s" class="kg-image" alt="%s" loading="lazy"></figure>'
                % (html_attr(src), html_attr(alt))
            )
            continue

        if all(re.match(r"^[-*]\s+", line.strip()) for line in lines):
            items = ["<li>%s</li>" % apply_inline_markup(re.sub(r"^[-*]\s+", "", line.strip())) for line in lines]
            rendered.append("<ul>%s</ul>" % "".join(items))
            continue

        if all(re.match(r"^\d+\.\s+", line.strip()) for line in lines):
            items = ["<li>%s</li>" % apply_inline_markup(re.sub(r"^\d+\.\s+", "", line.strip())) for line in lines]
            rendered.append("<ol>%s</ol>" % "".join(items))
            continue

        if all(line.strip().startswith(">") for line in lines):
            quote_text = " ".join(line.strip()[1:].strip() for line in lines)
            rendered.append("<blockquote><p>%s</p></blockquote>" % apply_inline_markup(quote_text))
            continue

        paragraph = " ".join(line.strip() for line in lines)
        rendered.append("<p>%s</p>" % apply_inline_markup(paragraph))

    return "".join(rendered)


def render_card(post, tags_by_slug):
    tag_names = [tags_by_slug[tag]["name"] for tag in post.get("tags", []) if tag in tags_by_slug]
    tag_html = html.escape(", ".join(tag_names))
    image_html = ""
    if post.get("feature_image"):
        image_html = '<img class="post-card-image" src="%s" alt="%s" loading="lazy">' % (
            html_attr(post["feature_image"]),
            html_attr(post["title"]),
        )
    return (
        '<a class="post-card" href="{url}"><header class="post-card-header">{image}'
        '<div class="post-card-tags">{tags}</div><h2 class="post-card-title">{title}</h2>'
        '</header><div class="post-card-excerpt"><p>{excerpt}</p></div><footer class="post-card-footer">'
        '<div class="post-card-footer-left"><span>Updated {updated}</span></div>'
        '<div class="post-card-footer-right"><div>{minutes} min read</div></div></footer></a>'
    ).format(
        url=post["url"],
        image=image_html,
        tags=tag_html,
        title=html.escape(post["title"]),
        excerpt=html.escape(post["excerpt"]),
        updated=human_date(post["updated_at"]),
        minutes=post["reading_time"],
    )


def build_page_shell(site, *, title, description, path, content_html, canonical_url, og_image="", twitter_card="summary_large_image", json_ld=""):
    template = load_template("base.html")
    home_attr = ' aria-current="page"' if path == "/" else ""
    about_attr = ' aria-current="page"' if path == "/about/" else ""
    social_image = ""
    if og_image:
        social_image = (
            '<meta name="twitter:image" content="{0}">'
            '<meta itemprop="image" content="{0}">'
            '<meta property="og:image" content="{0}">'
        ).format(html_attr(og_image))

    return template.safe_substitute(
        page_title=html.escape(title),
        meta_description=html_attr(description),
        site_title=html.escape(site["title"]),
        site_description=html.escape(site["description"]),
        site_lang=html_attr(site.get("lang", "en")),
        canonical_url=html_attr(canonical_url),
        twitter_card=html_attr(twitter_card),
        social_image=social_image,
        page_heading=html.escape(title),
        main_content=content_html,
        json_ld=json_ld,
        home_attr=home_attr,
        about_attr=about_attr,
        source_url=html_attr(site["source_url"]),
        author_url=html_attr(site["author_url"]),
        author_name=html.escape(site["author_name"]),
    )


def write_output(relative_path, content):
    destination = DIST / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content)


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(STATIC / "assets", DIST / "assets")

    site = load_yaml(CONTENT / "site.yml")
    tags_by_slug = load_yaml(CONTENT / "tags.yml")

    authors = {}
    for path in sorted((CONTENT / "authors").glob("*.yml")):
        author = load_yaml(path)
        author["slug"] = author.get("slug") or slugify(author["name"])
        author["url"] = "/author/%s/" % author["slug"]
        authors[author["slug"]] = author

    pages = []
    for path in sorted((CONTENT / "pages").glob("*.md")):
        page = read_markdown_doc(path)
        page["slug"] = page.get("slug") or slugify(page["title"])
        page["url"] = page.get("url") or ("/%s/" % page["slug"] if page["slug"] != "404" else "/404.html")
        page["author"] = authors.get(page.get("author", ""))
        page["published_at"] = parse_date(page.get("date"))
        page["updated_at"] = parse_date(page.get("updated")) or page["published_at"]
        page["excerpt"] = page.get("excerpt") or excerpt_from_markdown(page["body_markdown"])
        page["content_html"] = render_markdown(page["body_markdown"])
        page["kind"] = "page"
        pages.append(page)

    posts = []
    for path in sorted((CONTENT / "posts").glob("*.md")):
        post = read_markdown_doc(path)
        post["slug"] = post.get("slug") or slugify(post["title"])
        post["url"] = "/%s/" % post["slug"]
        post["author"] = authors[post["author"]]
        post["published_at"] = parse_date(post.get("date"))
        post["updated_at"] = parse_date(post.get("updated")) or post["published_at"]
        post["excerpt"] = post.get("excerpt") or excerpt_from_markdown(post["body_markdown"])
        post["reading_time"] = read_time_minutes(post["body_markdown"])
        post["content_html"] = render_markdown(post["body_markdown"])
        post["kind"] = "post"
        posts.append(post)

    posts.sort(key=lambda item: item["updated_at"], reverse=True)

    home_cards = "".join(render_card(post, tags_by_slug) for post in posts)
    home_content = load_template("home.html").safe_substitute(cards=home_cards)
    home_json_ld = '<script type="application/ld+json">%s</script>' % json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": site["title"],
            "url": site["url"],
            "description": site["description"],
        },
        indent=2,
    )
    write_output(
        "index.html",
        build_page_shell(
            site,
            title="Posts - %s" % site["title"],
            description=site["description"],
            path="/",
            content_html=home_content,
            canonical_url=absolute_url(site, "/"),
            json_ld=home_json_ld,
        ),
    )

    all_public_urls = ["/"]

    page_template = load_template("page.html")
    post_template = load_template("post.html")

    for page in pages:
        feature_image_html = ""
        if page.get("feature_image"):
            feature_image_html = '<figure class="post-feature-image"><img src="%s" alt="%s" loading="lazy"></figure>' % (
                html_attr(page["feature_image"]),
                html_attr(page["title"]),
            )
        body = page_template.safe_substitute(
            feature_image=feature_image_html,
            title=html.escape(page["title"]),
            content_html=page["content_html"],
        )
        schema_type = page.get("schema_type", "WebPage")
        json_ld = '<script type="application/ld+json">%s</script>' % json.dumps(
            {
                "@context": "https://schema.org",
                "@type": schema_type,
                "name": page["title"],
                "headline": page["title"],
                "description": page["excerpt"],
                "url": absolute_url(site, page["url"]),
                "datePublished": isoformat(page["published_at"]),
                "dateModified": isoformat(page["updated_at"]),
                "author": {
                    "@type": "Person",
                    "name": page["author"]["name"] if page.get("author") else site["author_name"],
                    "url": absolute_url(site, page["author"]["url"]) if page.get("author") else site["author_url"],
                },
            },
            indent=2,
        )
        output_path = page["url"].lstrip("/")
        if output_path.endswith("/"):
            output_path += "index.html"
        write_output(
            output_path,
            build_page_shell(
                site,
                title="%s - %s" % (page["title"], site["title"]),
                description=page["excerpt"],
                path=page["url"],
                content_html=body,
                canonical_url=absolute_url(site, page["url"]),
                json_ld=json_ld,
            ),
        )
        if not page.get("exclude_from_sitemap"):
            all_public_urls.append(page["url"])

    for post in posts:
        feature_image_html = ""
        if post.get("feature_image"):
            feature_image_html = '<figure class="post-feature-image"><img src="%s" alt="%s" loading="lazy"></figure>' % (
                html_attr(post["feature_image"]),
                html_attr(post["title"]),
            )
        body = post_template.safe_substitute(
            feature_image=feature_image_html,
            title=html.escape(post["title"]),
            content_html=post["content_html"],
        )
        json_ld = '<script type="application/ld+json">%s</script>' % json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "BlogPosting",
                "headline": post["title"],
                "description": post["excerpt"],
                "url": absolute_url(site, post["url"]),
                "mainEntityOfPage": absolute_url(site, post["url"]),
                "datePublished": isoformat(post["published_at"]),
                "dateModified": isoformat(post["updated_at"]),
                "image": [absolute_url(site, post["feature_image"])] if post.get("feature_image") else [],
                "author": {
                    "@type": "Person",
                    "name": post["author"]["name"],
                    "url": absolute_url(site, post["author"]["url"]),
                },
            },
            indent=2,
        )
        write_output(
            post["url"].lstrip("/") + "index.html",
            build_page_shell(
                site,
                title="%s - %s" % (post["title"], site["title"]),
                description=post["excerpt"],
                path=post["url"],
                content_html=body,
                canonical_url=absolute_url(site, post["url"]),
                og_image=absolute_url(site, post["feature_image"]) if post.get("feature_image") else "",
                json_ld=json_ld,
            ),
        )
        all_public_urls.append(post["url"])

    posts_by_tag = {}
    for post in posts:
        for tag_slug in post.get("tags", []):
            posts_by_tag.setdefault(tag_slug, []).append(post)

    tag_template = load_template("tag.html")
    for tag_slug, tagged_posts in posts_by_tag.items():
        tag = tags_by_slug[tag_slug]
        path = "/tag/%s/" % tag_slug
        body = tag_template.safe_substitute(
            tag_name=html.escape(tag["name"]),
            tag_description=html.escape(tag.get("description", "")),
            cards="".join(render_card(post, tags_by_slug) for post in tagged_posts),
        )
        json_ld = '<script type="application/ld+json">%s</script>' % json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": tag["name"],
                "description": tag.get("description", ""),
                "url": absolute_url(site, path),
            },
            indent=2,
        )
        write_output(
            "tag/%s/index.html" % tag_slug,
            build_page_shell(
                site,
                title="%s - %s" % (tag["name"], site["title"]),
                description=tag.get("description", site["description"]),
                path=path,
                content_html=body,
                canonical_url=absolute_url(site, path),
                json_ld=json_ld,
            ),
        )
        all_public_urls.append(path)

    author_template = load_template("author.html")
    for author_slug, author in authors.items():
        author_posts = [post for post in posts if post["author"]["slug"] == author_slug]
        body = author_template.safe_substitute(
            author_name=html.escape(author["name"]),
            author_bio=html.escape(author.get("bio", "")),
            author_image=html_attr(author.get("image", "")),
            author_image_block=(
                '<div class="author-header-image"><img src="%s" alt="%s" loading="lazy"></div>'
                % (html_attr(author["image"]), html_attr(author["name"]))
                if author.get("image")
                else ""
            ),
            cards="".join(render_card(post, tags_by_slug) for post in author_posts),
        )
        json_ld = '<script type="application/ld+json">%s</script>' % json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "ProfilePage",
                "name": author["name"],
                "description": author.get("bio", ""),
                "url": absolute_url(site, author["url"]),
                "mainEntity": {
                    "@type": "Person",
                    "name": author["name"],
                    "url": absolute_url(site, author["url"]),
                    "image": author.get("image", ""),
                },
            },
            indent=2,
        )
        write_output(
            "author/%s/index.html" % author_slug,
            build_page_shell(
                site,
                title="%s - %s" % (author["name"], site["title"]),
                description=author.get("bio", site["description"]),
                path=author["url"],
                content_html=body,
                canonical_url=absolute_url(site, author["url"]),
                og_image=author.get("image", ""),
                twitter_card="summary",
                json_ld=json_ld,
            ),
        )
        all_public_urls.append(author["url"])

    latest_updated = max(posts[0]["updated_at"], *(page["updated_at"] for page in pages if page.get("updated_at")))
    feed_entries = []
    for post in posts:
        feed_entries.append(
            "<entry><title>{title}</title><link href=\"{url}\"/><updated>{updated}</updated><id>{url}</id>"
            "<content type=\"html\">{content}</content></entry>".format(
                title=xml_escape(post["title"]),
                url=xml_escape(absolute_url(site, post["url"])),
                updated=xml_escape(atom_date(post["updated_at"])),
                content=xml_escape(post["content_html"]),
            )
        )
    feed = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        "<title>{title}</title><subtitle>{subtitle}</subtitle>"
        '<link href="{feed_url}" rel="self"/><link href="{site_url}"/>'
        "<updated>{updated}</updated><id>{site_url}/</id><author><name>{author}</name></author>{entries}</feed>"
    ).format(
        title=xml_escape(site["title"]),
        subtitle=xml_escape(site["description"]),
        feed_url=xml_escape(absolute_url(site, "/feed.xml")),
        site_url=xml_escape(site["url"]),
        updated=xml_escape(atom_date(latest_updated)),
        author=xml_escape(site["author_name"]),
        entries="".join(feed_entries),
    )
    write_output("feed.xml", feed)

    sitemap_entries = []
    for url in sorted(set(all_public_urls)):
        lastmod = latest_updated
        for page in pages:
            if page["url"] == url:
                lastmod = page["updated_at"]
        for post in posts:
            if post["url"] == url:
                lastmod = post["updated_at"]
        sitemap_entries.append(
            "<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod></url>".format(
                loc=xml_escape(absolute_url(site, url)),
                lastmod=human_date(lastmod),
            )
        )
    sitemap = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>' % "".join(sitemap_entries)
    )
    write_output("sitemap.xml", sitemap)

    write_output("robots.txt", "User-agent: *\nAllow: /\n")
    write_output(".htaccess", "ErrorDocument 404 /404.html\n")


if __name__ == "__main__":
    main()
