"""Map a URL to a knowledge category, and decide whether to skip it."""

from urllib.parse import urlparse

import config


def categorise(url):
    """Return the category label for a URL using the ordered CATEGORY_MAP."""
    path = urlparse(url).path
    for prefix, label in config.CATEGORY_MAP:
        if path.startswith(prefix):
            return label
    return config.DEFAULT_CATEGORY


def categorise_pdf(url, fallback_category):
    """Category for a PDF: an explicit override if matched, else the page's category."""
    for needle, label in config.PDF_CATEGORY_OVERRIDES:
        if needle in url:
            return label
    return fallback_category


def is_skipped(url):
    """True if the URL is in the configured skip-list."""
    path = urlparse(url).path
    return any(path.startswith(prefix) for prefix in config.SKIP_PATHS)
