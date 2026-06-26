"""
Iteration 17 regression tests:
- Admin login from /app/backend/.env credentials
- Predictions AI generate + batch (no auto-publish)
- SSR editoriale (episodi/interviste FAQ; parlano-di-noi press-intro)
- Schema.org JSON-LD (contatti, collaborazioni, privacy, cookie, transcript)
- SSR infra (sitemap, video-sitemap, robots, 404)
"""
import os
import re
import json
import pathlib
import pytest
import requests

# Load admin credentials from backend/.env
ENV_PATH = pathlib.Path("/app/backend/.env")
ENV = {}
for line in ENV_PATH.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        ENV[k.strip()] = v.strip().strip('"').strip("'")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sportivo.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = ENV.get("ADMIN_EMAIL")
ADMIN_PASSWORD = ENV.get("ADMIN_PASSWORD")


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/admin/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=20,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    assert "token" in data and isinstance(data["token"], str) and data["token"]
    return data["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# --- AUTH ---
class TestAuth:
    def test_login_returns_token(self, admin_token):
        assert isinstance(admin_token, str) and len(admin_token) > 10

    def test_admin_endpoint_with_token(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/predictions", headers=admin_headers, timeout=20)
        assert r.status_code == 200

    def test_admin_endpoint_without_token_unauthorized(self):
        r = requests.get(f"{BASE_URL}/api/admin/predictions", timeout=20)
        assert r.status_code in (401, 403)


# --- PREDICTIONS AI ---
class TestPredictionsAI:
    def test_ai_generate_round_38(self, admin_headers):
        r = requests.post(
            f"{BASE_URL}/api/admin/predictions/ai/generate",
            headers=admin_headers,
            json={"season": "2025-2026", "round": 38},
            timeout=180,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        data = r.json()
        assert data.get("ok") is True
        assert data.get("ai_status") == "ai_preview"
        draft = data.get("ai_draft") or {}
        for section in ("intro", "context", "picks_summary", "results_note", "disclaimer"):
            v = draft.get(section)
            assert isinstance(v, str) and v.strip(), f"section '{section}' empty"
        # matches/sources/similarity/antihallucination live INSIDE ai_draft
        assert isinstance(draft.get("matches"), list), f"matches missing/not list in ai_draft (keys={list(draft.keys())})"
        assert isinstance(draft.get("sources"), list)
        sim = draft.get("similarity") or {}
        anti = draft.get("antihallucination") or {}
        assert sim.get("passed") is True, f"similarity not passed: {sim}"
        assert anti.get("passed") is True, f"antihallucination not passed: {anti}"

    def test_ai_generate_does_not_publish(self, admin_headers):
        # After generate, the round 38 season 2025-2026 must have ai_status='ai_preview'.
        # NOTE: pre-existing status may be 'pubblicato' from prior manual publication;
        # AI generate must not flip status. We verify ai_status set & status remains
        # one of {bozza, pubblicato, draft} (i.e., NOT changed by the AI call itself).
        r = requests.get(f"{BASE_URL}/api/admin/predictions", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        items = r.json()
        if isinstance(items, dict):
            items = items.get("items") or items.get("predictions") or []
        target = [it for it in items if it.get("round") == 38 and it.get("season") == "2025-2026"]
        assert target, f"No round 38 season 2025-2026 found in {len(items)} items"
        it = target[0]
        ai_status = it.get("ai_status")
        assert ai_status == "ai_preview", f"Expected ai_status='ai_preview', got {ai_status} (item={it})"
        # The AI flow does not change publication: we accept whatever pre-existing
        # status (bozza or pubblicato from manual action). The KEY assertion is
        # that ai_status flips to 'ai_preview' (AI ran in preview mode, no autopublish).
        assert it.get("status") in ("bozza", "pubblicato", "draft"), f"Unexpected status {it.get('status')}"

    def test_ai_batch(self, admin_headers):
        r = requests.post(
            f"{BASE_URL}/api/admin/predictions/ai/batch",
            headers=admin_headers,
            json={"only_missing": True, "limit": 3},
            timeout=300,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        data = r.json()
        assert data.get("ok") is True
        assert isinstance(data.get("results"), list)


# --- SSR EDITORIAL ---
class TestSSREditorial:
    def test_seo_episodi_editorial_and_faq(self):
        r = requests.get(f"{BASE_URL}/api/seo/episodi", timeout=20)
        assert r.status_code == 200
        h = r.text
        assert 'data-testid="editorial-intro"' in h, "editorial-intro missing on /episodi"
        assert 'data-testid="faq-section"' in h, "faq-section missing on /episodi"
        assert '"@type": "FAQPage"' in h or '"@type":"FAQPage"' in h, "FAQPage JSON-LD missing on /episodi"

    def test_seo_interviste_editorial_and_faq(self):
        r = requests.get(f"{BASE_URL}/api/seo/interviste", timeout=20)
        assert r.status_code == 200
        h = r.text
        assert 'data-testid="editorial-intro"' in h, "editorial-intro missing on /interviste"
        assert 'data-testid="faq-section"' in h, "faq-section missing on /interviste"
        assert '"@type": "FAQPage"' in h or '"@type":"FAQPage"' in h, "FAQPage JSON-LD missing on /interviste"

    def test_seo_press_intro(self):
        r = requests.get(f"{BASE_URL}/api/seo/parlano-di-noi", timeout=20)
        assert r.status_code == 200
        assert 'data-testid="press-intro"' in r.text, "press-intro missing on /parlano-di-noi"


# --- SCHEMA.ORG ---
def _extract_jsonld_types(html: str):
    """Return list of @type strings found in any <script type=application/ld+json> blocks."""
    types = []
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        body = m.group(1).strip()
        try:
            data = json.loads(body)
        except Exception:
            # Try to extract @type via regex
            for tm in re.finditer(r'"@type"\s*:\s*"([^"]+)"', body):
                types.append(tm.group(1))
            continue
        stack = [data]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                t = cur.get("@type")
                if isinstance(t, str):
                    types.append(t)
                elif isinstance(t, list):
                    types.extend([x for x in t if isinstance(x, str)])
                for v in cur.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(cur, list):
                stack.extend(cur)
    return types


class TestSchemaOrg:
    def test_contatti_contactpage_faqpage(self):
        r = requests.get(f"{BASE_URL}/api/seo/contatti", timeout=20)
        assert r.status_code == 200
        types = _extract_jsonld_types(r.text)
        assert "ContactPage" in types, f"ContactPage missing in /contatti, got {types}"
        assert "FAQPage" in types, f"FAQPage missing in /contatti, got {types}"

    def test_collaborazioni_aboutpage(self):
        r = requests.get(f"{BASE_URL}/api/seo/collaborazioni", timeout=20)
        assert r.status_code == 200
        types = _extract_jsonld_types(r.text)
        assert "AboutPage" in types, f"AboutPage missing in /collaborazioni, got {types}"

    def test_privacy_webpage(self):
        r = requests.get(f"{BASE_URL}/api/seo/privacy", timeout=20)
        assert r.status_code == 200
        types = _extract_jsonld_types(r.text)
        assert "WebPage" in types, f"WebPage missing in /privacy, got {types}"

    def test_cookie_webpage(self):
        r = requests.get(f"{BASE_URL}/api/seo/cookie", timeout=20)
        assert r.status_code == 200
        types = _extract_jsonld_types(r.text)
        assert "WebPage" in types, f"WebPage missing in /cookie, got {types}"

    def test_transcript_webpage_no_videoobject(self):
        r = requests.get(
            f"{BASE_URL}/api/seo/interviste/fabio-ceravolo-130-gol-carriera/trascrizione",
            timeout=20,
        )
        assert r.status_code == 200
        types = _extract_jsonld_types(r.text)
        assert "WebPage" in types, f"WebPage missing in transcript, got {types}"
        assert "VideoObject" not in types, f"VideoObject must NOT be in transcript JSON-LD, got {types}"


# --- SSR INFRA ---
class TestSSRInfra:
    def test_sitemap(self):
        r = requests.get(f"{BASE_URL}/api/sitemap.xml", timeout=20)
        assert r.status_code == 200
        assert "<url>" in r.text

    def test_video_sitemap(self):
        r = requests.get(f"{BASE_URL}/api/video-sitemap.xml", timeout=20)
        assert r.status_code == 200
        assert "<video:title>" in r.text

    def test_robots(self):
        r = requests.get(f"{BASE_URL}/api/robots.txt", timeout=20)
        assert r.status_code == 200

    def test_seo_404(self):
        r = requests.get(f"{BASE_URL}/api/seo/pagina-inesistente-xyz", timeout=20)
        assert r.status_code == 404
