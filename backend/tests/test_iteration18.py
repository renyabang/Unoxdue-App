"""
Iteration 18 — Regression tests for Predictions AI admin cruscotto + SSR public regression
Covers:
  * POST /api/admin/login (credenziali da /app/backend/.env)
  * GET  /api/admin/predictions/ai/list
  * GET  /api/admin/predictions/ai/detail
  * GET  /api/admin/predictions/ai/safety (8 checks, passed=true)
  * POST /api/admin/predictions/ai/edit (campo results_note)
  * POST /api/admin/predictions/ai/status (review/approve/reject)
  * POST /api/admin/predictions/ai/publish con confirm=false -> errore
  * Regressione SSR: /api/seo/{home,episodi,team,parlano-di-noi}
"""
import os
import pytest
import requests
from dotenv import dotenv_values

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sportivo.preview.emergentagent.com").rstrip("/")
ENV = dotenv_values("/app/backend/.env")
ADMIN_EMAIL = ENV.get("ADMIN_EMAIL")
ADMIN_PASSWORD = ENV.get("ADMIN_PASSWORD")


@pytest.fixture(scope="module")
def admin_token():
    assert ADMIN_EMAIL and ADMIN_PASSWORD, "ADMIN_EMAIL/ADMIN_PASSWORD missing in /app/backend/.env"
    r = requests.post(f"{BASE_URL}/api/admin/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:300]}"
    token = r.json().get("token") or r.json().get("access_token")
    assert token, f"no token in response: {r.json()}"
    return token


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# === LIST ===
def test_list_drafts(auth_headers):
    r = requests.get(f"{BASE_URL}/api/admin/predictions/ai/list", headers=auth_headers, timeout=30)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body.get("ok") is True
    drafts = body.get("drafts") or []
    assert isinstance(drafts, list)
    assert len(drafts) >= 1, "expected at least 1 AI draft"
    # campi attesi
    first = drafts[0]
    for k in ("season", "round", "status"):
        assert k in first, f"missing {k} in draft: {first}"


# === SAFETY ===
def test_safety_2025_2026_g38(auth_headers):
    r = requests.get(f"{BASE_URL}/api/admin/predictions/ai/safety",
                     params={"season": "2025-2026", "round": 38},
                     headers=auth_headers, timeout=30)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body.get("ok") is True
    assert body.get("passed") is True
    checks = body.get("checks") or {}
    expected = {
        "almeno_un_pronostico_reale", "fonti_raggiungibili", "nessuna_informazione_inventata",
        "similarita_sotto_soglia", "stagione_giornata_valide", "canonical_slug_corretti",
        "copertina_automatica_disponibile", "disclaimer_presente",
    }
    assert expected.issubset(set(checks.keys())), f"missing checks: {expected - set(checks.keys())}"
    assert len(checks) >= 8


# === DETAIL ===
def test_detail_2025_2026_g38(auth_headers):
    r = requests.get(f"{BASE_URL}/api/admin/predictions/ai/detail",
                     params={"season": "2025-2026", "round": 38},
                     headers=auth_headers, timeout=30)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body.get("ok") is True
    detail = body.get("detail") or body
    assert detail.get("season") == "2025-2026"
    assert int(detail.get("round")) == 38


# === EDIT (results_note) ===
def test_edit_results_note_persists(auth_headers):
    # use season 2026-2027 g38 if exists to avoid touching public; else 2025-2026
    season, rnd = "2026-2027", 38
    # check exists; otherwise fallback
    r = requests.get(f"{BASE_URL}/api/admin/predictions/ai/detail",
                     params={"season": season, "round": rnd},
                     headers=auth_headers, timeout=30)
    if r.status_code != 200 or not (r.json().get("ok")):
        season = "2025-2026"
    new_text = "TEST_iter18 results_note edited"
    r = requests.post(f"{BASE_URL}/api/admin/predictions/ai/edit",
                      json={"season": season, "round": rnd, "fields": {"results_note": new_text}},
                      headers=auth_headers, timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert r.json().get("ok") is True
    # verify persistence
    r2 = requests.get(f"{BASE_URL}/api/admin/predictions/ai/detail",
                      params={"season": season, "round": rnd},
                      headers=auth_headers, timeout=30)
    assert r2.status_code == 200
    body = r2.json()
    detail = body.get("detail") or body
    # text might be in detail.results_note or nested in ai_draft
    rn = detail.get("results_note") or (detail.get("ai_draft") or {}).get("results_note")
    assert rn == new_text, f"results_note not persisted, got: {rn!r}"


# === STATUS (review/approve/reject) — use 2026-2027 g38 to avoid touching public ===
@pytest.mark.parametrize("action", ["review", "approve", "reject", "review"])
def test_status_actions(auth_headers, action):
    season, rnd = "2026-2027", 38
    r = requests.post(f"{BASE_URL}/api/admin/predictions/ai/status",
                      json={"season": season, "round": rnd, "action": action},
                      headers=auth_headers, timeout=30)
    if r.status_code == 404:
        pytest.skip("season 2026-2027 g38 non disponibile")
    assert r.status_code == 200, f"action={action}: {r.status_code} {r.text[:300]}"
    body = r.json()
    assert body.get("ok") is True


# === PUBLISH without confirm -> must error ===
def test_publish_requires_confirm(auth_headers):
    r = requests.post(f"{BASE_URL}/api/admin/predictions/ai/publish",
                      json={"season": "2025-2026", "round": 38, "confirm": False},
                      headers=auth_headers, timeout=30)
    # must NOT succeed silently
    assert r.status_code in (400, 403, 409, 422) or (
        r.status_code == 200 and r.json().get("ok") is False
    ), f"publish w/o confirm should fail, got: {r.status_code} {r.text[:300]}"


# === Public editorial visible after promotion (round 38 2025-2026 già pubblicato) ===
def test_public_editorial_visible():
    url = f"{BASE_URL}/api/seo/pronostici/serie-a/2025-2026/giornata-38"
    r = requests.get(url, timeout=30)
    assert r.status_code == 200, r.status_code
    assert 'data-testid="prediction-editorial"' in r.text, "prediction-editorial mancante nella pagina pubblica"


# === SSR regression ===
@pytest.mark.parametrize("path", [
    "/api/seo/home",
    "/api/seo/episodi",
    "/api/seo/team",
    "/api/seo/parlano-di-noi",
])
def test_ssr_regression(path):
    r = requests.get(f"{BASE_URL}{path}", timeout=30)
    assert r.status_code == 200, f"{path}: {r.status_code}"
    assert len(r.text) > 500, f"{path}: body troppo piccolo ({len(r.text)})"
