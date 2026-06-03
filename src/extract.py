"""Content extraction: clean body text from HTML pages and text from PDFs."""

import io
import os
import re
import shutil
import subprocess
import tempfile

import pdfplumber
import trafilatura
from bs4 import BeautifulSoup

import config


def extract_title(html, url):
    """Best-effort human-readable title for a page."""
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    if heading and heading.get_text(strip=True):
        return heading.get_text(strip=True)
    if soup.title and soup.title.get_text(strip=True):
        title = soup.title.get_text(strip=True)
        # WordPress titles are usually "Page Title - Site Name".
        for separator in (" - " + config.SITE_NAME, " | " + config.SITE_NAME, " | ", " - "):
            if separator in title:
                title = title.split(separator)[0].strip()
                break
        return title
    return url


def _decode_cfemail(hex_string):
    """Decode a Cloudflare-obfuscated email from its data-cfemail hex token."""
    data = bytes.fromhex(hex_string)
    key = data[0]
    return "".join(chr(byte ^ key) for byte in data[1:])


def deobfuscate_emails(html):
    """Replace Cloudflare email-protection placeholders with the real address.

    The site hides addresses as ``[email protected]`` with the real value held
    in a data-cfemail attribute; decoding restores contact details for the bot.
    """
    if "cfemail" not in html:
        return html
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("[data-cfemail]"):
        try:
            tag.replace_with(_decode_cfemail(tag["data-cfemail"]))
        except (ValueError, KeyError):
            continue
    return str(soup)


def extract_html(html, url):
    """Return clean main-body content (markdown) with boilerplate removed."""
    html = deobfuscate_emails(html)
    text = trafilatura.extract(
        html,
        output_format="markdown",
        include_links=False,
        include_images=False,
        include_comments=False,
        favor_recall=True,
        url=url,
    )
    if text and text.strip():
        return text.strip()

    # Fallback: pull the main content container directly.
    soup = BeautifulSoup(html, "html.parser")
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"role": "main"})
    )
    if main:
        return main.get_text("\n", strip=True)
    return ""


def extract_pdf(content):
    """Extract and tidy text from a PDF given as bytes.

    Falls back to OCR for image-only PDFs (some policy documents are scanned /
    rendered as vector outlines and carry no embedded text). Returns '' if even
    OCR yields nothing.
    """
    parts = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                parts.append(page_text)

    text = "\n".join(parts)
    if not text.strip():
        text = _ocr_pdf(content)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _ocr_pdf(content):
    """Rasterise each page and OCR it. Degrades to '' if OCR is unavailable.

    Uses a working-directory-local temp folder because the tesseract binary
    cannot always read images from the system temp directory.
    """
    if shutil.which("tesseract") is None:
        return ""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return ""

    tmpdir = tempfile.mkdtemp(prefix=".ocr_", dir=os.getcwd())
    parts = []
    try:
        document = fitz.open(stream=content, filetype="pdf")
        try:
            for index, page in enumerate(document):
                image_path = os.path.join(tmpdir, "page_{}.png".format(index))
                page.get_pixmap(dpi=config.OCR_DPI).save(image_path)
                result = subprocess.run(
                    ["tesseract", image_path, "stdout"],
                    capture_output=True,
                )
                if result.returncode == 0:
                    parts.append(result.stdout.decode("utf-8", "ignore"))
        finally:
            document.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return "\n".join(parts)
