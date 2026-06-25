"""SSR public pages tests for UnoXdue (frontend-only review).

Verifies all public clean URLs are server-rendered HTML with required SEO
elements (H1, canonical, JSON-LD), real <a href> menu links (no anchor #),
404 for non-existing routes, and that /admin still serves React SPA.
"""
import os
import re
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://sportivo.preview.emergentagent.com").rstrip("/")

PUBLIC_PAGES = [
    ("/", "h1"),  # home
    ("/il-podcast/", "h1"),
    ("/episodi/", "h1"),
    ("/interviste/", "h1"),
    ("/pronostici/", "h1"),
    ("/team/", "h1"),
    ("/parlano-di-noi/", "h1"),
    ("/collaborazioni/", "h1"),
    ("/contatti/", "h1"),
    ("/privacy/", "h1"),
    ("/cookie/", "h1"),
]

MENU_LINKS = [
    "/il-podcast/",
    "/episodi/",
    "/interviste/",
    "/pronostici/",
    "/team/",
    "/parlano-di-noi/",
]


@pytest.fixture(scope="module")
def home_html():
    r = requests.get(BASE + "/", timeout=20)
    assert r.status_code == 200, f"Home status {r.status_code}"
    return r.text


class TestSSRPublicPages:
    @pytest.mark.parametrize("path,_", PUBLIC_PAGES)
    def test_page_200_and_ssr(self, path, _):
        r = requests.get(BASE + path, timeout=20)
        assert r.status_code == 200, f"{path} -> {r.status_code}"
        html = r.text
        # Must NOT be a SPA empty shell
        assert "<h1" in html.lower(), f"{path} missing <h1>"
        assert "<link" in html.lower() and 'rel="canonical"' in html.lower(), f"{path} missing canonical"
        # Body content present in source
        body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
        assert body_match, f"{path} no <body>"
        body = body_match.group(1)
        assert len(body) > 500, f"{path} body too small ({len(body)})"

    def test_home_has_jsonld(self, home_html):
        assert 'application/ld+json' in home_html, "Home missing JSON-LD"
        # at least one ld+json block
        assert re.search(r'<script[^>]+application/ld\+json[^>]*>', home_html), "no JSON-LD script tag"

    def test_home_no_wrong_brand_spelling(self, home_html):
        # Must always be 'UnoXdue', not 'Unoxdue'
        assert "Unoxdue" not in home_html, "Found wrong brand spelling 'Unoxdue' in home"

    @pytest.mark.parametrize("link", MENU_LINKS)
    def test_menu_real_links_present(self, home_html, link):
        # Real <a href="/path/"> or absolute URL - not "#anchor"
        # Accept both relative '/x/' and absolute 'https://host/x/'
        pattern = re.compile(
            r'<a\b[^>]*href="(?:' + re.escape(BASE) + r')?' + re.escape(link) + r'"',
            re.IGNORECASE,
        )
        assert pattern.search(home_html), f"Home menu missing real link {link}"

    def test_menu_has_no_anchor_only_links(self, home_html):
        # Check that header navigation links to sections are not just '#xxx'
        # Find header block
        m = re.search(r"<header[^>]*>(.*?)</header>", home_html, re.DOTALL | re.IGNORECASE)
        assert m, "no <header>"
        header = m.group(1)
        # Each <a> href in header should be a real path or external, not bare '#'
        hrefs = re.findall(r'<a\b[^>]*href="([^"]+)"', header)
        assert hrefs, "header has no <a> links"
        for h in hrefs:
            assert not h.startswith("#"), f"Header link uses anchor: {h}"

    def test_footer_has_legal_links(self, home_html):
        m = re.search(r"<footer[^>]*>(.*?)</footer>", home_html, re.DOTALL | re.IGNORECASE)
        assert m, "no <footer>"
        footer = m.group(1)
        for link in ("/privacy/", "/cookie/", "/contatti/", "/collaborazioni/"):
            pattern = re.compile(
                r'href="(?:' + re.escape(BASE) + r')?' + re.escape(link) + r'"', re.IGNORECASE
            )
            assert pattern.search(footer), f"footer missing {link}"

    def test_mobile_menu_uses_details(self, home_html):
        # Native <details>/<summary> so it works without JS
        assert re.search(r"<details\b", home_html, re.IGNORECASE), "Mobile menu <details> missing"
        assert re.search(r"<summary\b", home_html, re.IGNORECASE), "Mobile menu <summary> missing"


class TestEpisodes:
    def test_archive_lists_episodes(self):
        r = requests.get(BASE + "/episodi/", timeout=20)
        assert r.status_code == 200
        html = r.text
        # at least one link into /episodi/<slug>/ (absolute or relative)
        cards = re.findall(
            r'href="(?:' + re.escape(BASE) + r')?(/episodi/[^"#?]+/)"', html
        )
        # filter out the archive itself
        cards = [c for c in cards if c.rstrip("/") != "/episodi"]
        assert cards, "No episode cards found on /episodi/"

    def test_episode_detail_page(self):
        slug = "/episodi/serie-a-2025-2026-giornata-29-puntata-1/"
        r = requests.get(BASE + slug, timeout=20)
        assert r.status_code == 200, f"{slug} -> {r.status_code}"
        html = r.text
        # Required H1
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL | re.IGNORECASE)
        assert h1_match, "Episode page missing <h1>"
        h1 = re.sub(r"<[^>]+>", "", h1_match.group(1)).strip()
        assert "Primo appuntamento UnoXdue" in h1, f"Unexpected H1: {h1!r}"
        assert "29" in h1, "H1 should reference 29ª giornata"
        # Breadcrumb short label
        assert "Primo appuntamento" in html, "breadcrumb 'Primo appuntamento' not in HTML"

    def test_episode_transcript_page(self):
        url = "/episodi/serie-a-2025-2026-giornata-29-puntata-1/trascrizione/"
        r = requests.get(BASE + url, timeout=20)
        assert r.status_code == 200, f"{url} -> {r.status_code}"
        html = r.text
        # paragraphs in source
        assert "<p" in html.lower(), "transcript page has no <p>"
        # body has multiple paragraphs
        ps = re.findall(r"<p[\s>]", html)
        assert len(ps) >= 3, f"transcript page has only {len(ps)} <p> tags"


class TestNotFound:
    @pytest.mark.parametrize("path", ["/episodi/non-esiste-xyz/", "/pagina-finta/", "/team/non-esiste/"])
    def test_404_routes(self, path):
        r = requests.get(BASE + path, timeout=20)
        assert r.status_code == 404, f"{path} expected 404, got {r.status_code}"


class TestAdmin:
    def test_admin_loads_spa(self):
        r = requests.get(BASE + "/admin", timeout=20, allow_redirects=True)
        assert r.status_code == 200
        # React SPA shell - should have a root div and JS bundle
        html = r.text
        assert 'id="root"' in html or 'id=root' in html, "admin missing React root"


class TestNoWrongBrand:
    @pytest.mark.parametrize("path,_", PUBLIC_PAGES)
    def test_no_wrong_brand_spelling(self, path, _):
        r = requests.get(BASE + path, timeout=20)
        assert r.status_code == 200
        assert "Unoxdue" not in r.text, f"Found wrong 'Unoxdue' spelling in {path}"
