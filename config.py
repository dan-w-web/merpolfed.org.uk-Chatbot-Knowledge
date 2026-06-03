"""Central configuration for the Merseyside Police Federation knowledge scraper.

Everything tunable lives here so the pipeline can be adjusted without touching
the scraping logic: which site to scrape, how pages map to categories, which
pages to skip, and which external (government) resources to fold in.
"""

SITE_NAME = "Merseyside Police Federation"
BASE_URL = "https://merpolfed.org.uk"
SITEMAP_URL = BASE_URL + "/sitemap.xml"

# Polite fetching
USER_AGENT = (
    "MerPolFed-KnowledgeBot/1.0 "
    "(+https://merpolfed.org.uk; automated chatbot knowledge sync)"
)
REQUEST_TIMEOUT = 20      # seconds
REQUEST_DELAY = 0.5       # seconds to wait between requests

# Category mapping: ordered list of (path_prefix, category_label).
# The first prefix that a URL path starts with wins, so put the more specific
# paths (e.g. the pensions page) above the more general ones (the resource centre).
CATEGORY_MAP = [
    ("/charitable-trust/", "Charitable Trust"),
    ("/resource-centre/pensions-injury-awards/", "Pensions and Injury Awards"),
    ("/resource-centre/health-safety/", "Health and Safety"),
    ("/resource-centre/", "Resources"),
    ("/offers-discounts/", "Offers and Discounts"),
    ("/services/", "Service Providers"),
    ("/group-insurance/", "Group Insurance"),
    ("/holiday-lets/", "Holiday Lets"),
    ("/forms/", "Forms"),
    ("/merseyside-police-federation/", "About the Federation"),
    ("/policies/", "Federation Policies"),
]
DEFAULT_CATEGORY = "About the Federation"

# A handful of PDFs are linked from the site-wide footer rather than a single
# section, so the page that links them does not reveal the right category. Map
# a URL substring to the category they belong in. (The federation's own policy
# documents go to "Group Insurance", which is kept in full; reference guides go
# to their topic, where they are excerpted like other large reference docs.)
PDF_CATEGORY_OVERRIDES = [
    ("Malvern-House-Travel-Policy", "Group Insurance"),
    ("Malvern-House-Scheme-benefits", "Group Insurance"),
    ("maternityguide", "Resources"),
    ("quickref", "Health and Safety"),
]

# The order categories appear in the generated document.
CATEGORY_ORDER = [
    "About the Federation",
    "Group Insurance",
    "Charitable Trust",
    "Pensions and Injury Awards",
    "Health and Safety",
    "Resources",
    "Offers and Discounts",
    "Service Providers",
    "Holiday Lets",
    "Forms",
    "Federation Policies",
    "Government Guidance",
]

# Pages that add no value to the chatbot and should be excluded entirely.
# Matched as a path prefix.
SKIP_PATHS = [
    "/policies/cookie-policy/",
    "/policies/privacy-policy/",
    "/website-disclaimer/",
    # Superseded Group Insurance documents page. It still links the old (now
    # 404) /group/*.pdf files and a stale Scheme Benefits booklet. The current
    # documents live at /group-insurance/group-insurance-policy-documents/.
    "/group-insurance/policy-documents/",
]

# DPI used when an image-only PDF has to be rasterised for OCR.
OCR_DPI = 200

# Keeping the knowledge focused and within the chatbot platform's limits.
# Federation pages (HTML on this site) and the federation's own policy
# documents are always kept in full. Large *external* reference documents
# (legislation, Home Office guidance, regulator PDFs) are capped to an excerpt
# plus a link to the full source.
FULL_TEXT_CATEGORIES = ["Group Insurance"]   # the federation's own policy documents
EXCERPT_THRESHOLD = 12000   # chars; content longer than this (and not "full text") is excerpted
EXCERPT_CHARS = 7000        # chars to keep in an excerpt

# Anchor text that tells us nothing useful; fall back to a title derived from
# the document URL instead.
GENERIC_LINK_TITLES = {
    "",
    "view full pdf",
    "click here",
    "click here to access link",
    "read more",
    "download",
    "more",
    "link",
    "here",
}

# External domains we are happy to fold into the knowledge automatically when
# the live site links out to them. Keeps relevant government / federation
# guidance in, marketing pages out.
GOV_ALLOWED_DOMAINS = [
    "gov.uk",
    "polfed.org",
]

# Explicitly curated external resources to always include, even if not linked
# from a scraped page. Extend this list as new guidance becomes relevant.
EXTERNAL_RESOURCES = [
    {
        "title": "Criminal Injuries Compensation Authority (CICA)",
        "url": "https://www.gov.uk/government/organisations/"
               "criminal-injuries-compensation-authority",
    },
]

# Where to write the published knowledge (the GitHub Pages directory).
OUTPUT_DIR = "docs"
