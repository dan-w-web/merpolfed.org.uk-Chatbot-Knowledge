"""Polite HTTP fetching with retries and a descriptive User-Agent."""

import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config

_session = None


def get_session():
    """Return a shared requests session configured with retry/backoff."""
    global _session
    if _session is None:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({"User-Agent": config.USER_AGENT})
        _session = session
    return _session


def fetch_text(url):
    """Fetch a URL and return its decoded text body."""
    response = get_session().get(url, timeout=config.REQUEST_TIMEOUT)
    response.raise_for_status()
    time.sleep(config.REQUEST_DELAY)
    return response.text


def fetch_bytes(url):
    """Fetch a URL and return its raw bytes (used for PDFs)."""
    response = get_session().get(url, timeout=config.REQUEST_TIMEOUT)
    response.raise_for_status()
    time.sleep(config.REQUEST_DELAY)
    return response.content
