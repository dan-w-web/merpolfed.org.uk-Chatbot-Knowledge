# Merseyside Police Federation - Chatbot Knowledge Pipeline

Automatically scrapes [merpolfed.org.uk](https://merpolfed.org.uk), its policy
PDFs, and relevant government guidance, then publishes everything as a single
knowledge page that the Zapier chatbot reads. It refreshes monthly so the bot
stays in step with the live site with no manual editing.

## What it produces

- `docs/knowledge.md` - the combined knowledge as plain markdown (best for the bot to ingest).
- `docs/index.html` - the same content rendered as a readable web page.

Both are published via GitHub Pages, giving a stable public URL to point Zapier at.

## How it works

1. Reads the site's `sitemap.xml` to find every page (~59).
2. Fetches each page and strips it back to clean body text (navigation, footers
   and cookie banners removed) using `trafilatura`.
3. Finds every linked PDF (e.g. the 1st May 2026 insurance policies on the Group
   Insurance "Policy Documents" page), downloads it, and extracts the text.
4. Folds in allowlisted government guidance (gov.uk, PFEW, etc.).
5. Groups everything by category (mirroring the original chatbot files, plus the
   newer Group Insurance and Holiday Lets sections) and renders the outputs.

## Running it locally

```bash
pip install -r requirements.txt
python scrape.py
```

Then open `docs/index.html` in a browser, or read `docs/knowledge.md`.

## Configuration

Everything tunable is in [`config.py`](config.py):

- `CATEGORY_MAP` / `CATEGORY_ORDER` - how URLs map to categories and their order.
- `SKIP_PATHS` - pages to exclude (cookie / privacy / disclaimer by default).
- `GOV_ALLOWED_DOMAINS` / `EXTERNAL_RESOURCES` - which external guidance to include.
- `REQUEST_DELAY` / `USER_AGENT` - politeness settings for the scraper.

## Automatic refresh

[`.github/workflows/refresh.yml`](.github/workflows/refresh.yml) runs the scraper
on the **1st of every month** (and can be triggered manually from the Actions
tab via *Run workflow*). It commits any changes to `docs/`, which GitHub Pages
serves.

### One-time GitHub setup

1. Push this repository to GitHub.
2. **Settings -> Pages**: set the source to "Deploy from a branch", branch
   `main`, folder `/docs`. The page goes live at
   `https://<user>.github.io/<repo>/`.
3. **Settings -> Actions -> General**: under "Workflow permissions" enable
   "Read and write permissions" so the scheduled job can commit refreshes.

## Connecting Zapier

Point the chatbot's knowledge source at the published URL:

- `https://<user>.github.io/<repo>/` for the web page, or
- `https://<user>.github.io/<repo>/knowledge.md` for the raw text.

Once Zapier reads from that URL, the monthly refresh keeps the bot current with
no re-upload. The six legacy `.txt` files can then be retired in favour of this
single source.
