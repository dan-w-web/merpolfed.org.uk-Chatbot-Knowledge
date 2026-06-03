"""Discover page URLs from the sitemap and find linked assets on a page."""

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

import config
from src import fetch


def _title_from_url(url):
    """Humanise the final path segment of a URL into a readable title."""
    segment = url.rstrip("/").rsplit("/", 1)[-1]
    segment = segment.rsplit(".", 1)[0]            # drop any extension
    segment = re.sub(r"[-_]+", " ", segment).strip()
    return segment.title() if segment else url


def _clean_title(title, url):
    """Use the anchor text unless it is missing or unhelpfully generic."""
    title = (title or "").strip()
    if title.lower() in config.GENERIC_LINK_TITLES or title.lower().startswith("http"):
        return _title_from_url(url)
    return title


def discover_pages():
    """Return an ordered, de-duplicated list of page URLs from the sitemap.

    Handles both a sitemap index (which points at child sitemaps) and a plain
    urlset.
    """
    index_xml = fetch.fetch_text(config.SITEMAP_URL)
    soup = BeautifulSoup(index_xml, "xml")

    child_sitemaps = [loc.get_text(strip=True) for loc in soup.select("sitemap > loc")]
    if not child_sitemaps:
        # Not an index, treat the document itself as a urlset.
        child_sitemaps = [config.SITEMAP_URL]

    urls = []
    for sitemap_url in child_sitemaps:
        xml = fetch.fetch_text(sitemap_url)
        child = BeautifulSoup(xml, "xml")
        for loc in child.select("url > loc"):
            urls.append(loc.get_text(strip=True))

    seen = set()
    ordered = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def _is_allowed_external(netloc):
    return any(
        netloc == domain or netloc.endswith("." + domain)
        for domain in config.GOV_ALLOWED_DOMAINS
    )


def find_assets(html, page_url):
    """Return (pdf_links, external_links) found on a page.

    Scans the whole page so that documents linked only from the site-wide
    footer (e.g. the Travel Policy) are still discovered. A few such footer
    documents are placed via config.PDF_CATEGORY_OVERRIDES at categorisation
    time, since their linking page does not indicate the right section. PDFs
    are any link whose path ends in .pdf; external links are only returned when
    their host is on the government/federation allowlist.
    """
    soup = BeautifulSoup(html, "html.parser")
    base_host = urlparse(config.BASE_URL).netloc

    pdfs = []
    externals = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(page_url, anchor["href"].strip())
        parsed = urlparse(href)
        path_no_query = parsed.path.lower()
        title = anchor.get_text(strip=True)

        if path_no_query.endswith(".pdf"):
            pdfs.append({"url": href, "title": _clean_title(title, href)})
        elif parsed.netloc and parsed.netloc != base_host and _is_allowed_external(parsed.netloc):
            externals.append({"url": href, "title": _clean_title(title, href)})

    return pdfs, externals
