#!/usr/bin/env python3
import html
import json
import re
import shutil
import struct
import subprocess
import sys
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

IMAGE_PRESETS = {
    "feature": {"max_width": 1400, "quality": 70},
    "inline": {"max_width": 1200, "quality": 72},
    "tile": {"max_width": 220, "quality": 45},
}
FEATURE_VARIANT_WIDTHS = (480, 800, 1200, 1400)
CARD_IMAGE_SIZES = "(max-width: 680px) 92vw, (max-width: 980px) 44vw, 30vw"
HERO_IMAGE_SIZES = "(max-width: 760px) 92vw, 680px"
IMAGE_DERIVATIVE_CACHE = {}
DERIVATIVE_SOURCE_URLS = set()


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


def local_asset_path(url_path):
    if not url_path or not url_path.startswith("/assets/"):
        return None
    return STATIC / url_path.lstrip("/")


def built_asset_path(url_path):
    if not url_path or not url_path.startswith("/assets/"):
        return None
    return DIST / url_path.lstrip("/")


def site_asset_path(url_path):
    built_path = built_asset_path(url_path)
    if built_path and built_path.exists():
        return built_path

    static_path = local_asset_path(url_path)
    if static_path and static_path.exists():
        return static_path

    return None


def image_size_for_site_path(url_path):
    file_path = site_asset_path(url_path)
    if not file_path or not file_path.exists():
        return None

    with file_path.open("rb") as handle:
        header = handle.read(32)
        if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
            return struct.unpack(">II", header[16:24])

        if header[:2] == b"\xff\xd8":
            handle.seek(2)
            while True:
                marker_prefix = handle.read(1)
                if not marker_prefix:
                    return None
                if marker_prefix != b"\xff":
                    continue
                marker = handle.read(1)
                while marker == b"\xff":
                    marker = handle.read(1)
                if marker in {b"\xc0", b"\xc1", b"\xc2", b"\xc3", b"\xc5", b"\xc6", b"\xc7", b"\xc9", b"\xca", b"\xcb", b"\xcd", b"\xce", b"\xcf"}:
                    segment_length = struct.unpack(">H", handle.read(2))[0]
                    segment = handle.read(segment_length - 2)
                    height, width = struct.unpack(">HH", segment[1:5])
                    return width, height
                if marker in {b"\xd8", b"\xd9"}:
                    continue
                segment_length_bytes = handle.read(2)
                if len(segment_length_bytes) != 2:
                    return None
                segment_length = struct.unpack(">H", segment_length_bytes)[0]
                handle.seek(segment_length - 2, 1)

    return None


def image_dimension_attrs(url_path):
    size = image_size_for_site_path(url_path)
    if not size:
        return ""
    width, height = size
    return ' width="%s" height="%s"' % (width, height)


def derivative_url(url_path, preset, *, width=None):
    source = Path(url_path)
    config = IMAGE_PRESETS[preset]
    ext = ".jpg"
    return "/assets/images/%s.%s-%sw%s" % (
        source.stem,
        preset,
        width or config["max_width"],
        ext,
    )


def ensure_image_derivative(url_path, preset, *, width=None):
    if not url_path or not url_path.startswith("/assets/"):
        return url_path
    if ".%s." % preset in url_path:
        return url_path

    cache_key = (url_path, preset, width)
    if cache_key in IMAGE_DERIVATIVE_CACHE:
        return IMAGE_DERIVATIVE_CACHE[cache_key]

    source_path = local_asset_path(url_path)
    if not source_path or not source_path.exists():
        IMAGE_DERIVATIVE_CACHE[cache_key] = url_path
        return url_path

    target_url = derivative_url(url_path, preset, width=width)
    target_path = built_asset_path(target_url)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if not target_path.exists() or source_path.stat().st_mtime > target_path.stat().st_mtime:
        config = IMAGE_PRESETS[preset]
        command = ["sips", "-Z", str(width or config["max_width"])]
        if target_path.suffix.lower() in {".jpg", ".jpeg"}:
            command.extend(["-s", "format", "jpeg", "-s", "formatOptions", str(config["quality"])])
        else:
            command.extend(["-s", "format", "png"])
        command.extend([str(source_path), "--out", str(target_path)])
        subprocess.run(command, check=True, capture_output=True)

    DERIVATIVE_SOURCE_URLS.add(url_path)
    IMAGE_DERIVATIVE_CACHE[cache_key] = target_url
    return target_url


def ensure_image_variant_set(url_path, preset, widths):
    variants = []
    for width in widths:
        variants.append(
            {
                "width": width,
                "url": ensure_image_derivative(url_path, preset, width=width),
            }
        )
    return variants


def srcset_attr(variants):
    return ", ".join("%s %sw" % (variant["url"], variant["width"]) for variant in variants)


def optimize_html_img_tag(match):
    tag = match.group(0)
    source_url = match.group(1)
    optimized_url = ensure_image_derivative(source_url, "inline")
    updated = tag.replace(source_url, optimized_url, 1)
    dims = image_dimension_attrs(optimized_url)
    if dims and " width=" not in updated and " height=" not in updated:
        updated = updated[:-1] + dims + ">"
    if "loading=" not in updated:
        updated = updated[:-1] + ' loading="lazy">'
    if "decoding=" not in updated:
        updated = updated[:-1] + ' decoding="async">'
    return updated


def preprocess_markdown(markdown_text):
    return re.sub(r'<img\b[^>]*\bsrc="([^"]+)"[^>]*>', optimize_html_img_tag, markdown_text)


def image_tag(url_path, alt, *, class_name="", loading="lazy", fetchpriority=None, decoding="async", srcset=None, sizes=None):
    attrs = [
        'src="%s"' % html_attr(url_path),
        'alt="%s"' % html_attr(alt),
    ]
    if class_name:
        attrs.append('class="%s"' % html_attr(class_name))
    attrs.append('loading="%s"' % html_attr(loading))
    if fetchpriority:
        attrs.append('fetchpriority="%s"' % html_attr(fetchpriority))
    if decoding:
        attrs.append('decoding="%s"' % html_attr(decoding))
    if srcset:
        attrs.append('srcset="%s"' % html_attr(srcset))
    if sizes:
        attrs.append('sizes="%s"' % html_attr(sizes))
    dims = image_dimension_attrs(url_path)
    if dims:
        attrs.append(dims.strip())
    return "<img %s>" % " ".join(attrs)


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

    def replace_image(match):
        alt, src = match.groups()
        optimized_url = ensure_image_derivative(src, "inline")
        return image_tag(optimized_url, alt, loading="lazy")

    def replace_link(match):
        label, href = match.groups()
        return '<a href="%s">%s</a>' % (href, label)

    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_image, text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<em>\1</em>", text)
    for index, code_html in enumerate(code_spans):
        text = text.replace("@@CODE%s@@" % index, code_html)
    return text


def render_markdown(markdown_text):
    markdown_text = preprocess_markdown(markdown_text)
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
            rendered.append('<figure class="kg-card kg-image-card">%s</figure>' % image_tag(ensure_image_derivative(src, "inline"), alt, class_name="kg-image", loading="lazy"))
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


def render_card(post, tags_by_slug, *, is_priority=False):
    tag_names = [tags_by_slug[tag]["name"] for tag in post.get("tags", []) if tag in tags_by_slug]
    tag_html = html.escape(", ".join(tag_names))
    image_html = ""
    if post.get("feature_image"):
        feature_srcset = srcset_attr(post["feature_image_variants"])
        image_html = image_tag(
            post["feature_image_optimized"],
            post["title"],
            class_name="post-card-image",
            loading="eager" if is_priority else "lazy",
            fetchpriority="high" if is_priority else None,
            srcset=feature_srcset,
            sizes=CARD_IMAGE_SIZES,
        )
    draft_label = '<span class="post-card-draft">Draft</span> ' if post.get("draft") else ""
    return (
        '<a class="post-card" href="{url}"><header class="post-card-header">{image}'
        '<div class="post-card-tags">{tags}</div><h2 class="post-card-title">{draft}{title}</h2>'
        '</header><div class="post-card-excerpt"><p>{excerpt}</p></div><footer class="post-card-footer">'
        '<div class="post-card-footer-left"><span>Updated {updated}</span></div>'
        '<div class="post-card-footer-right"><div>{minutes} min read</div></div></footer></a>'
    ).format(
        url=post["url"],
        image=image_html,
        tags=tag_html,
        draft=draft_label,
        title=html.escape(post["title"]),
        excerpt=html.escape(post["excerpt"]),
        updated=human_date(post["updated_at"]),
        minutes=post["reading_time"],
    )


def build_page_shell(
    site,
    *,
    title,
    description,
    path,
    content_html,
    canonical_url,
    og_image="",
    twitter_card="summary_large_image",
    json_ld="",
    og_type="website",
    robots_content="index,follow",
):
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
        og_type=html_attr(og_type),
        robots_content=html_attr(robots_content),
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
    include_drafts = "--drafts" in sys.argv

    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(STATIC / "assets", DIST / "assets")
    ensure_image_derivative("/assets/images/confused_small.png", "tile")

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
        if page.get("draft") and not include_drafts:
            print("[build] skipping draft: %s" % path.name)
            continue
        page["slug"] = page.get("slug") or slugify(page["title"])
        page["url"] = page.get("url") or ("/%s/" % page["slug"] if page["slug"] != "404" else "/404.html")
        page["author"] = authors.get(page.get("author", ""))
        page["published_at"] = parse_date(page.get("date"))
        page["updated_at"] = parse_date(page.get("updated")) or page["published_at"]
        page["excerpt"] = page.get("excerpt") or excerpt_from_markdown(page["body_markdown"])
        page["content_html"] = render_markdown(page["body_markdown"])
        page["feature_image_variants"] = ensure_image_variant_set(page.get("feature_image"), "feature", FEATURE_VARIANT_WIDTHS) if page.get("feature_image") else []
        page["feature_image_optimized"] = page["feature_image_variants"][-1]["url"] if page["feature_image_variants"] else ""
        page["kind"] = "page"
        pages.append(page)

    posts = []
    for path in sorted((CONTENT / "posts").glob("*.md")):
        post = read_markdown_doc(path)
        if post.get("draft") and not include_drafts:
            print("[build] skipping draft: %s" % path.name)
            continue
        post["slug"] = post.get("slug") or slugify(post["title"])
        post["url"] = "/%s/" % post["slug"]
        post["author"] = authors[post["author"]]
        post["published_at"] = parse_date(post.get("date"))
        post["updated_at"] = parse_date(post.get("updated")) or post["published_at"]
        post["excerpt"] = post.get("excerpt") or excerpt_from_markdown(post["body_markdown"])
        post["reading_time"] = read_time_minutes(post["body_markdown"])
        post["content_html"] = render_markdown(post["body_markdown"])
        post["feature_image_variants"] = ensure_image_variant_set(post.get("feature_image"), "feature", FEATURE_VARIANT_WIDTHS) if post.get("feature_image") else []
        post["feature_image_optimized"] = post["feature_image_variants"][-1]["url"] if post["feature_image_variants"] else ""
        post["kind"] = "post"
        posts.append(post)

    posts.sort(key=lambda item: item["updated_at"], reverse=True)

    home_cards = "".join(render_card(post, tags_by_slug, is_priority=(index == 0)) for index, post in enumerate(posts))
    home_content = load_template("home.html").safe_substitute(cards=home_cards)
    home_json_ld = '<script type="application/ld+json">%s</script>' % json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "@id": absolute_url(site, "/#website"),
            "name": site["title"],
            "url": site["url"],
            "description": site["description"],
            "publisher": {
                "@type": "Person",
                "@id": absolute_url(site, "/#publisher"),
                "name": site["author_name"],
                "url": site["author_url"],
            },
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
            feature_image_html = '<figure class="post-feature-image">%s</figure>' % image_tag(
                page["feature_image_optimized"],
                page["title"],
                loading="eager",
                fetchpriority="high",
                srcset=srcset_attr(page["feature_image_variants"]),
                sizes=HERO_IMAGE_SIZES,
            )
        draft_banner = '<div class="draft-banner">DRAFT &mdash; not published</div>\n' if page.get("draft") else ""
        body = page_template.safe_substitute(
            feature_image=feature_image_html,
            title=html.escape(page["title"]),
            content_html=draft_banner + page["content_html"],
        )
        schema_type = page.get("schema_type", "WebPage")
        json_ld = '<script type="application/ld+json">%s</script>' % json.dumps(
            {
                "@context": "https://schema.org",
                "@type": schema_type,
                "@id": absolute_url(site, page["url"]) + "#webpage",
                "name": page["title"],
                "headline": page["title"],
                "description": page["excerpt"],
                "url": absolute_url(site, page["url"]),
                "isPartOf": {"@id": absolute_url(site, "/#website")},
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
                robots_content="noindex,follow" if page["url"] == "/404.html" else "index,follow",
            ),
        )
        if not page.get("exclude_from_sitemap"):
            all_public_urls.append(page["url"])

    for post in posts:
        feature_image_html = ""
        if post.get("feature_image"):
            feature_image_html = '<figure class="post-feature-image">%s</figure>' % image_tag(
                post["feature_image_optimized"],
                post["title"],
                loading="eager",
                fetchpriority="high",
                srcset=srcset_attr(post["feature_image_variants"]),
                sizes=HERO_IMAGE_SIZES,
            )
        draft_banner = '<div class="draft-banner">DRAFT &mdash; not published</div>\n' if post.get("draft") else ""
        body = post_template.safe_substitute(
            feature_image=feature_image_html,
            title=html.escape(post["title"]),
            content_html=draft_banner + post["content_html"],
        )
        json_ld = '<script type="application/ld+json">%s</script>' % json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "BlogPosting",
                "@id": absolute_url(site, post["url"]) + "#article",
                "headline": post["title"],
                "description": post["excerpt"],
                "url": absolute_url(site, post["url"]),
                "mainEntityOfPage": absolute_url(site, post["url"]),
                "isPartOf": {"@id": absolute_url(site, "/#website")},
                "datePublished": isoformat(post["published_at"]),
                "dateModified": isoformat(post["updated_at"]),
                "image": [absolute_url(site, post["feature_image_optimized"])] if post.get("feature_image") else [],
                "author": {
                    "@type": "Person",
                    "name": post["author"]["name"],
                    "url": absolute_url(site, post["author"]["url"]),
                },
                "publisher": {
                    "@type": "Person",
                    "@id": absolute_url(site, "/#publisher"),
                    "name": site["author_name"],
                    "url": site["author_url"],
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
                og_image=absolute_url(site, post["feature_image_optimized"]) if post.get("feature_image") else "",
                json_ld=json_ld,
                og_type="article",
            ),
        )
        if not post.get("draft"):
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
                "@id": absolute_url(site, path) + "#collection",
                "name": tag["name"],
                "description": tag.get("description", ""),
                "url": absolute_url(site, path),
                "isPartOf": {"@id": absolute_url(site, "/#website")},
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
                "@id": absolute_url(site, author["url"]) + "#profile",
                "name": author["name"],
                "description": author.get("bio", ""),
                "url": absolute_url(site, author["url"]),
                "isPartOf": {"@id": absolute_url(site, "/#website")},
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
        if post.get("draft"):
            continue
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

    for special_file in ("_headers", "_redirects"):
        special_file_path = CONTENT / special_file
        if special_file_path.exists():
            write_output(special_file, special_file_path.read_text())

    for source_url in sorted(DERIVATIVE_SOURCE_URLS):
        copied_source = built_asset_path(source_url)
        if copied_source and copied_source.exists():
            copied_source.unlink()

    write_output("robots.txt", "User-agent: *\nAllow: /\nSitemap: %s\n" % absolute_url(site, "/sitemap.xml"))
    llms_lines = [
        "# %s" % site["title"],
        "",
        "> %s" % site["description"],
        "",
        "Site: %s" % site["url"],
        "Author: %s" % site["author_name"],
        "Author URL: %s" % site["author_url"],
        "Source: %s" % site["source_url"],
        "Sitemap: %s" % absolute_url(site, "/sitemap.xml"),
        "Feed: %s" % absolute_url(site, "/feed.xml"),
        "",
        "## Key Pages",
        "- Home: %s" % absolute_url(site, "/"),
    ]
    for page in pages:
        if page["url"] != "/404.html" and not page.get("draft"):
            llms_lines.append("- %s: %s" % (page["title"], absolute_url(site, page["url"])))
    llms_lines.extend(["", "## Posts"])
    for post in posts:
        if not post.get("draft"):
            llms_lines.append("- %s: %s" % (post["title"], absolute_url(site, post["url"])))
    write_output("llms.txt", "\n".join(llms_lines) + "\n")
    write_output(
        ".htaccess",
        """ErrorDocument 404 /404.html
<IfModule mod_headers.c>
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header always set Strict-Transport-Security "max-age=31536000"
  Header always set X-Content-Type-Options "nosniff"
  Header always set X-Frame-Options "SAMEORIGIN"
  Header always set Cross-Origin-Opener-Policy "same-origin"
  Header always set Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; img-src 'self' https: data:; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'"
  <FilesMatch "\\.(css|jpg|jpeg|png|gif|svg|webp|woff|woff2)$">
    Header set Cache-Control "public, max-age=31536000, immutable"
  </FilesMatch>
  <FilesMatch "\\.(html|xml|txt)$">
    Header set Cache-Control "public, max-age=300"
  </FilesMatch>
</IfModule>
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/plain text/css text/xml application/xml application/rss+xml application/javascript application/json image/svg+xml
</IfModule>
<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresByType text/html "access plus 5 minutes"
  ExpiresByType text/plain "access plus 5 minutes"
  ExpiresByType text/xml "access plus 5 minutes"
  ExpiresByType application/xml "access plus 5 minutes"
  ExpiresByType application/rss+xml "access plus 5 minutes"
  ExpiresByType text/css "access plus 1 year"
  ExpiresByType image/jpeg "access plus 1 year"
  ExpiresByType image/png "access plus 1 year"
  ExpiresByType image/webp "access plus 1 year"
  ExpiresByType image/svg+xml "access plus 1 year"
  ExpiresByType font/woff2 "access plus 1 year"
</IfModule>
""",
    )


if __name__ == "__main__":
    main()
