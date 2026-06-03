"""Render the collected content into a single knowledge.md and index.html."""

import re
from urllib.parse import urlparse

import markdown

import config


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def demote_headings(md_text, by=3):
    """Push any markdown headings in scraped content below the structural levels.

    Category headings are ## and item headings are ###, so content headings are
    demoted (capped at ######) to keep the document hierarchy intact and the
    table of contents clean.
    """
    def _shift(match):
        level = min(len(match.group(1)) + by, 6)
        # Normalise to a single space so it renders predictably (the markdown
        # renderer treats "#Text" without a space as a heading too).
        return "#" * level + " " + match.group(2)

    return re.sub(r"^(#{1,6})[ \t]*(\S.*)$", _shift, md_text, flags=re.MULTILINE)


def _keep_full_text(item, category):
    """Federation pages and the federation's own policy documents are kept whole."""
    if category in config.FULL_TEXT_CATEGORIES:
        return True
    if item.get("kind") == "page":
        return urlparse(item["url"]).netloc == urlparse(config.BASE_URL).netloc
    return False


def _excerpt(content, url):
    """Trim long reference content to a leading excerpt plus a link to the source."""
    cut = content[: config.EXCERPT_CHARS]
    boundary = cut.rfind("\n\n")
    if boundary > config.EXCERPT_CHARS * 0.6:
        cut = cut[:boundary]
    return (
        cut.rstrip()
        + "\n\n_[Excerpt only. This is a large reference document; "
        + "read the full version at {}]_".format(url)
    )


def prepare_content(item, category):
    """Return the content to render for an item, excerpting large reference docs."""
    content = (item.get("content") or "").strip()
    if not content:
        return ""
    if not _keep_full_text(item, category) and len(content) > config.EXCERPT_THRESHOLD:
        content = _excerpt(content, item["url"])
    return demote_headings(content)


def ordered_categories(categories):
    """Yield category labels in the configured order, with any extras last."""
    ordered = [c for c in config.CATEGORY_ORDER if c in categories]
    extras = [c for c in categories if c not in config.CATEGORY_ORDER]
    return ordered + sorted(extras)


def build_markdown(categories, generated_date):
    """Assemble the single combined knowledge document as markdown text."""
    lines = []
    lines.append("# {} - Chatbot Knowledge Base".format(config.SITE_NAME))
    lines.append("")
    lines.append("_Last updated: {}_".format(generated_date))
    lines.append("")
    lines.append("_Source: {}_".format(config.BASE_URL))
    lines.append("")
    lines.append(
        "This document is generated automatically from the live website and "
        "its policy documents. It is the single source of knowledge for the "
        "member chatbot. Each entry is labelled with the page or document it "
        "came from."
    )
    lines.append("")

    cats = list(ordered_categories(categories))

    lines.append("## Contents")
    lines.append("")
    for cat in cats:
        lines.append("- [{}](#{})".format(cat, slugify(cat)))
    lines.append("")

    for cat in cats:
        lines.append("## {}".format(cat))
        lines.append("")
        for item in categories[cat]:
            label = item["title"]
            if item.get("kind") == "pdf":
                label = "{} (PDF)".format(label)
            lines.append("### {}".format(label))
            lines.append("")
            lines.append("Source: {}".format(item["url"]))
            lines.append("")
            content = prepare_content(item, cat)
            if content:
                lines.append(content)
            else:
                lines.append("_(No extractable text. Refer to the source link above.)_")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6; max-width: 820px; margin: 0 auto; padding: 2rem 1.25rem;
    color: #1a1a1a; background: #fff;
  }}
  h1 {{ font-size: 1.9rem; border-bottom: 3px solid #0b3d91; padding-bottom: .4rem; }}
  h2 {{ font-size: 1.4rem; margin-top: 2.5rem; border-bottom: 1px solid #ddd; padding-bottom: .3rem; color: #0b3d91; }}
  h3 {{ font-size: 1.1rem; margin-top: 1.6rem; }}
  a {{ color: #0b3d91; }}
  code, pre {{ background: #f4f4f4; border-radius: 4px; }}
  pre {{ padding: .75rem; overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: .4rem .6rem; text-align: left; }}
  em {{ color: #555; }}
  .meta {{ color: #666; font-size: .9rem; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def build_html(md_text):
    """Render the markdown document into a styled, self-contained HTML page."""
    body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    return _HTML_TEMPLATE.format(
        title="{} - Chatbot Knowledge".format(config.SITE_NAME),
        body=body,
    )
