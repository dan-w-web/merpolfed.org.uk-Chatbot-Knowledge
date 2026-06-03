#!/usr/bin/env python3
"""Scrape merpolfed.org.uk into a single chatbot knowledge document.

Pipeline: discover pages from the sitemap, fetch and clean each page, download
and extract the linked policy PDFs, fold in allowlisted government guidance,
group everything by category, and render docs/knowledge.md + docs/index.html.

Run from the repository root:

    python scrape.py
"""

import datetime
import os
import sys

import config
from src import categorise, discover, extract, fetch, render


def collect_pages():
    """Fetch every (non-skipped) page and return (categories, pdf_seen, externals)."""
    pages = discover.discover_pages()
    print("Discovered {} page URLs from the sitemap.".format(len(pages)))

    categories = {}
    pdf_seen = {}        # url -> {title, category}
    external_seen = {}   # url -> {title}
    scraped = 0

    for url in pages:
        if categorise.is_skipped(url):
            print("  - skipping (configured): {}".format(url))
            continue
        try:
            html = fetch.fetch_text(url)
        except Exception as error:  # noqa: BLE001 - log and continue
            print("  ! failed to fetch {}: {}".format(url, error))
            continue

        category = categorise.categorise(url)
        item = {
            "title": extract.extract_title(html, url),
            "url": url,
            "content": extract.extract_html(html, url),
            "kind": "page",
        }
        categories.setdefault(category, []).append(item)
        scraped += 1

        pdfs, externals = discover.find_assets(html, url)
        for pdf in pdfs:
            existing = pdf_seen.get(pdf["url"])
            if existing:
                existing["count"] += 1
            else:
                pdf["category"] = categorise.categorise_pdf(pdf["url"], category)
                pdf["count"] = 1
                pdf_seen[pdf["url"]] = pdf
        for ext in externals:
            external_seen.setdefault(ext["url"], ext)

    print("Scraped {} pages.".format(scraped))
    return categories, _dedupe_pdfs(pdf_seen), external_seen, scraped


def _dedupe_pdfs(pdf_seen):
    """Collapse PDFs that share a title, keeping the most widely linked version.

    Superseded documents (e.g. an old v12 booklet linked from one stray page)
    lose out to the current version that is linked site-wide.
    """
    by_title = {}
    for url, meta in pdf_seen.items():
        by_title.setdefault(meta["title"].strip().lower(), []).append((url, meta))

    result = {}
    for entries in by_title.values():
        if len(entries) == 1:
            url, meta = entries[0]
            result[url] = meta
            continue
        entries.sort(key=lambda item: item[1].get("count", 1), reverse=True)
        keep_url, keep_meta = entries[0]
        result[keep_url] = keep_meta
        dropped = [u for u, _ in entries[1:]]
        print(
            "  dedup '{}': keeping {} ({}x linked), dropping {}".format(
                keep_meta["title"], keep_url, keep_meta.get("count", 1), dropped
            )
        )
    return result


def collect_pdfs(categories, pdf_seen):
    """Download each discovered PDF, extract its text, and file under its category.

    PDFs that cannot be fetched (dead links) are dropped entirely. PDFs that
    fetch but yield no text (after the OCR fallback) are kept as a link-only
    entry so the chatbot can still point members at the document.
    """
    print("Extracting {} PDF documents...".format(len(pdf_seen)))
    ok = link_only = dead = 0
    for url, meta in pdf_seen.items():
        try:
            content = fetch.fetch_bytes(url)
        except Exception as error:  # noqa: BLE001 - drop dead links
            print("  ! dead PDF, dropping: {} ({})".format(url, error))
            dead += 1
            continue
        try:
            text = extract.extract_pdf(content)
        except Exception as error:  # noqa: BLE001
            print("  ! could not parse PDF {}: {}".format(url, error))
            text = ""
        if text:
            ok += 1
        else:
            link_only += 1
            print("  ~ no text (kept as link-only): {}".format(url))
        categories.setdefault(meta["category"], []).append(
            {"title": meta["title"], "url": url, "content": text, "kind": "pdf"}
        )
    print(
        "PDFs: {} with text, {} link-only, {} dead/dropped.".format(ok, link_only, dead)
    )
    return ok


def collect_gov_guidance(categories, external_seen):
    """Fetch curated + discovered government guidance into its own category."""
    resources = {}
    for resource in config.EXTERNAL_RESOURCES:
        resources[resource["url"]] = dict(resource)
    for url, meta in external_seen.items():
        resources.setdefault(url, meta)

    print("Fetching {} government guidance resources...".format(len(resources)))
    items = []
    dropped = 0
    for url, meta in resources.items():
        try:
            if url.lower().split("?")[0].endswith(".pdf"):
                content = extract.extract_pdf(fetch.fetch_bytes(url))
            else:
                content = extract.extract_html(fetch.fetch_text(url), url)
        except Exception as error:  # noqa: BLE001 - drop unreachable guidance
            print("  ! dropping unreachable guidance: {} ({})".format(url, error))
            dropped += 1
            continue
        items.append(
            {"title": meta.get("title") or url, "url": url, "content": content, "kind": "gov"}
        )

    if items:
        categories["Government Guidance"] = items
    print("Guidance: {} included, {} dropped.".format(len(items), dropped))
    return len(items)


def write_outputs(categories, generated_date):
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    md_text = render.build_markdown(categories, generated_date)
    html_text = render.build_html(md_text)

    md_path = os.path.join(config.OUTPUT_DIR, "knowledge.md")
    html_path = os.path.join(config.OUTPUT_DIR, "index.html")
    nojekyll_path = os.path.join(config.OUTPUT_DIR, ".nojekyll")

    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(md_text)
    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(html_text)
    with open(nojekyll_path, "w", encoding="utf-8") as handle:
        handle.write("")

    return md_path, html_path, len(md_text)


def main():
    generated_date = datetime.datetime.now(datetime.timezone.utc).strftime("%d %B %Y")

    categories, pdf_seen, external_seen, scraped = collect_pages()
    if scraped == 0:
        print("ERROR: no pages were scraped; aborting without writing output.")
        return 1

    pdf_ok = collect_pdfs(categories, pdf_seen)
    gov_count = collect_gov_guidance(categories, external_seen)

    md_path, html_path, md_size = write_outputs(categories, generated_date)

    print("")
    print("=== Summary ===")
    print("  Pages scraped:        {}".format(scraped))
    print("  PDFs extracted:       {}/{}".format(pdf_ok, len(pdf_seen)))
    print("  Gov guidance items:   {}".format(gov_count))
    print("  Categories:           {}".format(len(categories)))
    print("  knowledge.md:         {} ({:,} chars)".format(md_path, md_size))
    print("  index.html:           {}".format(html_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
