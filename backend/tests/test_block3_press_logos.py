"""Block 3 backend tests: admin auth, press logo endpoints, SSR /team and press public pages."""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sportivo.preview.emergentagent.com").rstrip("/")


def _load_admin_creds():
    """Leggi le credenziali admin SOLO da backend/.env (nessun segreto hardcoded)."""
    email = os.environ.get("ADMIN_EMAIL")
    pw = os.environ.get("ADMIN_PASSWORD")
    if email and pw:
        return email, pw
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    try:
        with open(env_path) as f:
            for line in f:
                if line.startswith("ADMIN_EMAIL=") and not email:
                    email = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("ADMIN_PASSWORD=") and not pw:
                    pw = line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return email or "admin@unoxdue.net", pw


ADMIN_EMAIL, ADMIN_PASSWORD = _load_admin_creds()


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/admin/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and isinstance(data["token"], str) and len(data["token"]) > 10
    return data["token"]


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# --- Admin auth ---
class TestAdminAuth:
    def test_login_returns_token(self, token):
        assert token

    def test_admin_endpoint_with_token(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/press/list", headers=auth_headers, timeout=15)
        assert r.status_code == 200, r.text


# --- Press list / logos ---
class TestPressList:
    def test_press_list_5_records_with_logo_field(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/admin/press/list", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        items = d.get("items") or []
        assert len(items) == 5, f"expected 5 press records, got {len(items)}"
        for it in items:
            assert "logo" in it, f"missing logo field on {it.get('id')}"
            lg = it["logo"] or {}
            for k in ("method", "url", "approved", "initials"):
                assert k in lg, f"logo missing key '{k}' on {it.get('id')}"
            assert it.get("status") != "published", f"item {it.get('id')} is published"


class TestPressLogoExtract:
    def test_extract_returns_ok(self, auth_headers):
        lst = requests.get(f"{BASE_URL}/api/admin/press/list", headers=auth_headers, timeout=15).json()
        item_id = lst["items"][0]["id"]
        r = requests.post(f"{BASE_URL}/api/admin/press/logo/extract",
                          headers=auth_headers, json={"id": item_id}, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ok") is True
        assert "logo" in d
        # Either url present (success) or initials fallback (acceptable)
        lg = d["logo"]
        assert lg.get("initials") or lg.get("url")


class TestPressLogoApprove:
    def test_approve_sets_approved_true(self, auth_headers):
        # find an item that has logo.url (extract one first to be deterministic)
        lst = requests.get(f"{BASE_URL}/api/admin/press/list", headers=auth_headers, timeout=15).json()
        target = None
        for it in lst["items"]:
            if (it.get("logo") or {}).get("url"):
                target = it
                break
        if target is None:
            # try extracting for each until one has a URL
            for it in lst["items"]:
                er = requests.post(f"{BASE_URL}/api/admin/press/logo/extract",
                                   headers=auth_headers, json={"id": it["id"]}, timeout=90)
                if er.ok and (er.json().get("logo") or {}).get("url"):
                    target = it
                    break
        if target is None:
            pytest.skip("No press item has a logo.url (network/extraction failed); approve cannot be tested")
        r = requests.post(f"{BASE_URL}/api/admin/press/logo/approve",
                          headers=auth_headers, json={"id": target["id"]}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True
        # verify list reflects approved=true
        lst2 = requests.get(f"{BASE_URL}/api/admin/press/list", headers=auth_headers, timeout=15).json()
        it2 = next(x for x in lst2["items"] if x["id"] == target["id"])
        assert it2["logo"]["approved"] is True
        # critical: approving the logo MUST NOT publish the mention
        assert it2.get("status") != "published"


class TestPressLogoInitials:
    def test_initials_sets_method_and_approved(self, auth_headers):
        lst = requests.get(f"{BASE_URL}/api/admin/press/list", headers=auth_headers, timeout=15).json()
        # use the last item to avoid clobbering approve test target
        item_id = lst["items"][-1]["id"]
        r = requests.post(f"{BASE_URL}/api/admin/press/logo/initials",
                          headers=auth_headers, json={"id": item_id}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True
        lst2 = requests.get(f"{BASE_URL}/api/admin/press/list", headers=auth_headers, timeout=15).json()
        it2 = next(x for x in lst2["items"] if x["id"] == item_id)
        assert it2["logo"]["method"] == "initials"
        assert it2["logo"]["approved"] is True


class TestPressLogoServed:
    def test_logo_webp_served(self, auth_headers):
        lst = requests.get(f"{BASE_URL}/api/admin/press/list", headers=auth_headers, timeout=15).json()
        url = None
        for it in lst["items"]:
            u = (it.get("logo") or {}).get("url")
            if u and u.endswith(".webp"):
                url = u
                break
        if not url:
            pytest.skip("No press item with a saved .webp logo to test static serving")
        # The url is absolute (SITE_URL/api/static/...). Use it directly.
        r = requests.get(url, timeout=15)
        assert r.status_code == 200, f"{url} returned {r.status_code}"
        assert "image/webp" in r.headers.get("Content-Type", ""), r.headers.get("Content-Type")


# --- SSR pages ---
class TestSSRTeam:
    def test_team_page_ssr(self):
        r = requests.get(f"{BASE_URL}/api/seo/team", timeout=15)
        assert r.status_code == 200
        html = r.text
        # must be SSR, not SPA shell
        assert 'id="root"' not in html, "team page returned SPA shell instead of SSR"
        # tipster cards present and in correct order: marziano, micuccio, ninja
        slugs = ["il-marziano", "sono-micuccio", "il-ninja"]
        positions = []
        for s in slugs:
            tag = f'data-testid="tipster-card-{s}"'
            assert tag in html, f"missing tipster card {s}"
            positions.append(html.find(tag))
        assert positions == sorted(positions), f"tipster cards out of order: {positions}"
        # collab card visible on /team/
        assert 'data-testid="collab-card-sono-gianmarco"' in html, "missing collab card sono-gianmarco on /team/"


class TestSSRHomeIlPodcast:
    @pytest.mark.parametrize("path", ["/api/seo/home", "/api/seo/il-podcast"])
    def test_no_collab_on_home_and_podcast(self, path):
        r = requests.get(f"{BASE_URL}{path}", timeout=15)
        assert r.status_code == 200, f"{path} -> {r.status_code}"
        html = r.text
        assert 'id="root"' not in html
        assert 'collab-card-sono-gianmarco' not in html, \
            f"collab Gianmarco MUST NOT appear on {path}"
        assert 'Sono Gianmarco' not in html, \
            f"'Sono Gianmarco' text MUST NOT appear on {path}"
        # but 3 tipster cards must still appear
        for s in ["il-marziano", "sono-micuccio", "il-ninja"]:
            assert f'tipster-card-{s}' in html, f"missing tipster {s} on {path}"


class TestSSRParlanoDiNoi:
    def test_parlano_di_noi_renders_empty(self):
        r = requests.get(f"{BASE_URL}/api/seo/parlano-di-noi", timeout=15)
        assert r.status_code == 200
        html = r.text
        assert 'id="root"' not in html
        # 0 published expected => empty-state, but no Python tracebacks / errors
        assert "Traceback" not in html
        assert "Internal Server Error" not in html
