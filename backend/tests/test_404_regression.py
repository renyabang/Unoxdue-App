"""Regression tests for the SSR 404 fix (iteration_15).

Previously, unknown public clean URLs (e.g. /pagina-finta/) returned HTTP 200
with the React SPA shell. The fix: setupProxy.js was inverted to proxy ALL
non-asset/non-/admin/non-/api paths to the FastAPI SSR backend, and a
catch-all `GET /seo/{full_path:path}` route renders a 404 page with
status_code=404 and noindex=True.

These tests verify:
  1. Unknown top-level clean URLs return HTTP 404, with H1 'Pagina non trovata'
     and meta robots noindex in the HTML source.
  2. Unknown episode/team slugs return HTTP 404 (still routed to specific SSR).
  3. Known valid SSR pages still return 200 with real HTML (not SPA shell).
  4. /admin still loads the React SPA.
  5. Static asset /logo.jpg still served as image.
  6. /sitemap.xml and /robots.txt served by backend.
"""
import os
import re
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL",
                     "https://sportivo.preview.emergentagent.com").rstrip("/")

UNKNOWN_404_PAGES = [
    "/pagina-finta/",
    "/foo/bar/",
    "/qualsiasi-cosa-inesistente",
]

UNKNOWN_SLUG_PAGES = [
    "/episodi/non-esiste-xyz/",
    "/team/non-esiste/",
]

VALID_SSR_PAGES = [
    "/",
    "/episodi/",
    "/episodi/serie-a-2025-2026-giornata-29-puntata-1/",
    "/interviste/",
    "/pronostici/",
    "/team/",
    "/collaborazioni/",
    "/contatti/",
    "/privacy/",
    "/cookie/",
    "/il-podcast/",
    "/parlano-di-noi/",
]


# --- 404 catch-all SSR ---
@pytest.mark.parametrize("path", UNKNOWN_404_PAGES)
def test_unknown_route_returns_404_ssr(path):
    r = requests.get(BASE + path, timeout=20, allow_redirects=False)
    assert r.status_code == 404, f"{path} expected 404 got {r.status_code}"
    h1 = re.search(r"<h1[^>]*>([^<]+)</h1>", r.text)
    assert h1 is not None, f"{path} no <h1> in response"
    assert h1.group(1).strip() == "Pagina non trovata", \
        f"{path} H1 was {h1.group(1)!r}"
    assert "noindex" in r.text.lower(), f"{path} missing meta robots noindex"


# --- 404 for unknown episode/team slugs ---
@pytest.mark.parametrize("path", UNKNOWN_SLUG_PAGES)
def test_unknown_slug_returns_404(path):
    r = requests.get(BASE + path, timeout=20, allow_redirects=False)
    assert r.status_code == 404, f"{path} expected 404 got {r.status_code}"


# --- No regression on valid SSR pages ---
@pytest.mark.parametrize("path", VALID_SSR_PAGES)
def test_valid_ssr_page_returns_200_with_h1(path):
    r = requests.get(BASE + path, timeout=20, allow_redirects=False)
    assert r.status_code == 200, f"{path} expected 200 got {r.status_code}"
    assert "<h1" in r.text, f"{path} missing <h1> tag (likely SPA shell)"
    # Should NOT be the SPA shell (which is mostly <div id="root">)
    # Real SSR page bodies are > 500 chars and have <h1>...</h1>
    assert len(r.text) > 500, f"{path} body too short ({len(r.text)} bytes)"


# --- Admin still loads React SPA ---
def test_admin_loads_react_spa():
    r = requests.get(BASE + "/admin", timeout=20, allow_redirects=False)
    assert r.status_code == 200, f"/admin expected 200 got {r.status_code}"
    # React SPA shell signature
    assert 'id="root"' in r.text or "static/js" in r.text, \
        "/admin doesn't look like the React SPA shell"


# --- Static assets ---
def test_logo_jpg_image_200():
    r = requests.get(BASE + "/logo.jpg", timeout=20)
    assert r.status_code == 200, f"/logo.jpg expected 200 got {r.status_code}"
    assert r.headers.get("content-type", "").startswith("image/"), \
        f"/logo.jpg content-type was {r.headers.get('content-type')}"


# --- Sitemap and robots from backend ---
def test_sitemap_xml():
    r = requests.get(BASE + "/sitemap.xml", timeout=20)
    assert r.status_code == 200
    assert "<urlset" in r.text


def test_robots_txt():
    r = requests.get(BASE + "/robots.txt", timeout=20)
    assert r.status_code == 200
    assert "User-agent" in r.text
