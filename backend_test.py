#!/usr/bin/env python3
"""
UnoXdue Backend API Testing Suite
Tests all backend endpoints in priority order (high_first)
"""
import requests
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://sportivo.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@unoxdue.net"
ADMIN_PASSWORD = "unoxdue2026"

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_test(name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"  Details: {details}")
    
    if passed:
        test_results["passed"].append(name)
    else:
        test_results["failed"].append({"name": name, "details": details})

def log_warning(name: str, details: str):
    """Log warning"""
    print(f"⚠️  WARNING: {name}")
    print(f"  Details: {details}")
    test_results["warnings"].append({"name": name, "details": details})

def check_html_ssr(html: str, page_name: str) -> tuple[bool, str]:
    """Verify SSR HTML contains required elements"""
    issues = []
    
    if "<h1" not in html and "<h1>" not in html:
        issues.append("Missing <h1> tag")
    
    if '<link rel="canonical"' not in html:
        issues.append("Missing canonical link")
    
    if '<script type="application/ld+json">' not in html:
        issues.append("Missing JSON-LD script")
    
    if issues:
        return False, f"{page_name}: " + ", ".join(issues)
    return True, f"{page_name}: Contains H1, canonical, and JSON-LD"

# ============================================================================
# HIGH PRIORITY TESTS
# ============================================================================

def test_admin_auth():
    """Test 1: Admin JWT authentication flow"""
    print("\n" + "="*70)
    print("HIGH PRIORITY TEST 1: Admin Auth JWT")
    print("="*70)
    
    # Test 1.1: Login with correct credentials
    try:
        resp = requests.post(f"{BASE_URL}/admin/login", 
                            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                            timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "token" in data:
                token = data["token"]
                log_test("Admin login with correct credentials", True, f"Token received")
            else:
                log_test("Admin login with correct credentials", False, "No token in response")
                return None
        else:
            log_test("Admin login with correct credentials", False, 
                    f"Status {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        log_test("Admin login with correct credentials", False, str(e))
        return None
    
    # Test 1.2: Login with wrong password
    try:
        resp = requests.post(f"{BASE_URL}/admin/login",
                            json={"email": ADMIN_EMAIL, "password": "wrongpassword"},
                            timeout=10)
        if resp.status_code == 401:
            log_test("Admin login with wrong password returns 401", True)
        else:
            log_test("Admin login with wrong password returns 401", False,
                    f"Expected 401, got {resp.status_code}")
    except Exception as e:
        log_test("Admin login with wrong password returns 401", False, str(e))
    
    # Test 1.3: GET /admin/me without token
    try:
        resp = requests.get(f"{BASE_URL}/admin/me", timeout=10)
        if resp.status_code in [401, 403]:
            log_test("GET /admin/me without token returns 401/403", True)
        else:
            log_test("GET /admin/me without token returns 401/403", False,
                    f"Expected 401/403, got {resp.status_code}")
    except Exception as e:
        log_test("GET /admin/me without token returns 401/403", False, str(e))
    
    # Test 1.4: GET /admin/me with token
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/admin/me", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("email") and data.get("role") == "admin":
                log_test("GET /admin/me with token", True, 
                        f"Email: {data['email']}, Role: {data['role']}")
            else:
                log_test("GET /admin/me with token", False, 
                        f"Missing email or role in response: {data}")
        else:
            log_test("GET /admin/me with token", False,
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("GET /admin/me with token", False, str(e))
    
    # Test 1.5: Protected endpoint without token
    try:
        resp = requests.get(f"{BASE_URL}/admin/episodes", timeout=10)
        if resp.status_code in [401, 403]:
            log_test("Protected endpoint /admin/episodes without token returns 401/403", True)
        else:
            log_test("Protected endpoint /admin/episodes without token returns 401/403", False,
                    f"Expected 401/403, got {resp.status_code}")
    except Exception as e:
        log_test("Protected endpoint /admin/episodes without token returns 401/403", False, str(e))
    
    return token

def test_ssr_pages():
    """Test 2: SSR public pages"""
    print("\n" + "="*70)
    print("HIGH PRIORITY TEST 2: SSR Public Pages")
    print("="*70)
    
    pages = [
        ("/seo/home", "Home"),
        ("/seo/il-podcast", "Il Podcast"),
        ("/seo/parlano-di-noi", "Parlano di Noi"),
        ("/seo/episodi", "Episodi Archive"),
        ("/seo/interviste", "Interviste Archive"),
        ("/seo/pronostici", "Pronostici Archive"),
        ("/seo/pronostici/serie-a/2025-2026/giornata-38", "Pronostici Detail"),
        ("/seo/team", "Team Archive"),
        ("/seo/team/antonello-santopaolo", "Team Member Detail"),
        ("/seo/interviste/fabio-ceravolo-130-gol-carriera", "Interview Detail"),
    ]
    
    for path, name in pages:
        try:
            resp = requests.get(f"{BASE_URL}{path}", timeout=15)
            if resp.status_code == 200:
                html = resp.text
                passed, details = check_html_ssr(html, name)
                log_test(f"SSR page {name}", passed, details)
                
                # Additional checks for specific pages
                if "pronostici/serie-a/2025-2026/giornata-38" in path:
                    if "Quota totale" in html or "quota totale" in html.lower():
                        log_test(f"SSR {name} contains 'Quota totale'", True)
                    else:
                        log_warning(f"SSR {name}", "Missing 'Quota totale' text")
                    
                    # Check for tipster names
                    tipsters = ["Marziano", "Ninja", "Micuccio"]
                    found_tipster = any(t in html for t in tipsters)
                    if found_tipster:
                        log_test(f"SSR {name} contains tipster name", True)
                    else:
                        log_warning(f"SSR {name}", "No tipster names found")
                
                if "team/antonello-santopaolo" in path:
                    if "Person" in html and "application/ld+json" in html:
                        log_test(f"SSR {name} contains Person JSON-LD", True)
                    else:
                        log_warning(f"SSR {name}", "Person JSON-LD not clearly identified")
                        
            elif resp.status_code == 404:
                # 404 is expected for some pages if content doesn't exist
                log_warning(f"SSR page {name}", f"404 Not Found - content may not exist yet")
            else:
                log_test(f"SSR page {name}", False, 
                        f"Status {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log_test(f"SSR page {name}", False, str(e))
    
    # Test non-existent slug returns 404
    try:
        resp = requests.get(f"{BASE_URL}/seo/episodi/non-existent-slug-12345", timeout=10)
        if resp.status_code == 404:
            log_test("SSR non-existent slug returns 404", True)
        else:
            log_test("SSR non-existent slug returns 404", False,
                    f"Expected 404, got {resp.status_code}")
    except Exception as e:
        log_test("SSR non-existent slug returns 404", False, str(e))

def test_youtube_sync(token: str):
    """Test 3: YouTube sync via RSS feed"""
    print("\n" + "="*70)
    print("HIGH PRIORITY TEST 3: YouTube Sync")
    print("="*70)
    
    if not token:
        log_test("YouTube sync", False, "No auth token available")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get episodes count before sync
    try:
        resp = requests.get(f"{BASE_URL}/episodes", timeout=10)
        episodes_before = len(resp.json()) if resp.status_code == 200 else 0
    except:
        episodes_before = 0
    
    # Trigger YouTube sync
    try:
        print("  Triggering YouTube sync (this may take 10-20 seconds)...")
        resp = requests.post(f"{BASE_URL}/admin/sync/youtube", 
                            headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok") is True:
                found = data.get("found", 0)
                created = data.get("created", 0)
                updated = data.get("updated", 0)
                log_test("YouTube sync", True, 
                        f"Found: {found}, Created: {created}, Updated: {updated}")
            else:
                log_test("YouTube sync", False, f"ok=false: {data}")
        else:
            log_test("YouTube sync", False, 
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("YouTube sync", False, str(e))
    
    # Verify episodes were created
    try:
        resp = requests.get(f"{BASE_URL}/episodes", timeout=10)
        if resp.status_code == 200:
            episodes = resp.json()
            if len(episodes) > 0:
                log_test("GET /episodes returns non-empty list after sync", True,
                        f"Total episodes: {len(episodes)}")
            else:
                log_test("GET /episodes returns non-empty list after sync", False,
                        "Episodes list is empty")
        else:
            log_test("GET /episodes returns non-empty list after sync", False,
                    f"Status {resp.status_code}")
    except Exception as e:
        log_test("GET /episodes returns non-empty list after sync", False, str(e))

def test_ocr_schedina(token: str):
    """Test 4: OCR schedina with OpenAI Vision"""
    print("\n" + "="*70)
    print("HIGH PRIORITY TEST 4: OCR Schedina (OpenAI Vision)")
    print("="*70)
    
    if not token:
        log_test("OCR schedina", False, "No auth token available")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Find a real image to use
    image_path = Path("/app/backend/uploads/slip-8ed267bf01.jpg")
    if not image_path.exists():
        log_test("OCR schedina", False, f"Test image not found at {image_path}")
        return
    
    try:
        print("  Uploading image for OCR (this may take 20-30 seconds)...")
        with open(image_path, "rb") as f:
            files = {"image": ("test_slip.jpg", f, "image/jpeg")}
            resp = requests.post(f"{BASE_URL}/admin/predictions/ocr",
                                headers=headers, files=files, timeout=45)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok") is True:
                result_data = data.get("data", {})
                selections = result_data.get("selections", [])
                total_odds = result_data.get("total_odds", "")
                
                log_test("OCR schedina returns ok=true", True,
                        f"Selections: {len(selections)}, Total odds: {total_odds}")
                
                # Verify structure
                if selections and len(selections) > 0:
                    sample = selections[0]
                    required_keys = ["match", "market", "pick", "odds"]
                    has_required = all(k in sample for k in required_keys)
                    if has_required:
                        log_test("OCR selections have required fields", True,
                                f"Sample: {sample}")
                    else:
                        log_test("OCR selections have required fields", False,
                                f"Missing keys in: {sample}")
                
                # Verify NO sensitive data
                sensitive_keys = ["importo", "bonus", "vincita", "stake", "saldo", 
                                "puntata", "payout", "winnings", "balance"]
                found_sensitive = []
                for key in sensitive_keys:
                    if key in str(data).lower():
                        found_sensitive.append(key)
                
                if not found_sensitive:
                    log_test("OCR output contains NO sensitive data", True)
                else:
                    log_test("OCR output contains NO sensitive data", False,
                            f"Found sensitive keys: {found_sensitive}")
            else:
                log_test("OCR schedina returns ok=true", False, 
                        f"ok=false: {data}")
        else:
            log_test("OCR schedina", False,
                    f"Status {resp.status_code}: {resp.text[:500]}")
    except Exception as e:
        log_test("OCR schedina", False, str(e))

def test_predictions_crud(token: str):
    """Test 5: Predictions CRUD and add-pick"""
    print("\n" + "="*70)
    print("HIGH PRIORITY TEST 5: Predictions CRUD + add-pick")
    print("="*70)
    
    if not token:
        log_test("Predictions CRUD", False, "No auth token available")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test add-pick for new season/round
    test_season = "2026-2027"
    test_round = 38
    
    try:
        payload = {
            "competition": "Serie A",
            "season": test_season,
            "round": test_round,
            "tipster": "Il Marziano",
            "type": "Multipla",
            "total_odds": "5.00",
            "selections": [
                {
                    "competition": "Serie A",
                    "date": "2027-05-30",
                    "match": "Juventus - Inter",
                    "market": "1X2",
                    "pick": "1",
                    "odds": "2.50"
                },
                {
                    "competition": "Serie A",
                    "date": "2027-05-30",
                    "match": "Milan - Roma",
                    "market": "1X2",
                    "pick": "1",
                    "odds": "2.00"
                }
            ]
        }
        
        resp = requests.post(f"{BASE_URL}/admin/predictions/add-pick",
                            headers=headers, json=payload, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok") is True:
                log_test("POST /admin/predictions/add-pick", True,
                        f"URL: {data.get('public_url', '')}")
            else:
                log_test("POST /admin/predictions/add-pick", False,
                        f"ok=false: {data}")
        else:
            log_test("POST /admin/predictions/add-pick", False,
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("POST /admin/predictions/add-pick", False, str(e))
    
    # Verify the SSR page was created
    try:
        resp = requests.get(
            f"{BASE_URL}/seo/pronostici/serie-a/{test_season}/giornata-{test_round}",
            timeout=10)
        if resp.status_code == 200:
            log_test(f"SSR page for {test_season}/round {test_round} created", True)
        else:
            log_test(f"SSR page for {test_season}/round {test_round} created", False,
                    f"Status {resp.status_code}")
    except Exception as e:
        log_test(f"SSR page for {test_season}/round {test_round} created", False, str(e))
    
    # Test collision: verify 2025-2026/38 and 2026-2027/38 are different
    try:
        resp1 = requests.get(
            f"{BASE_URL}/seo/pronostici/serie-a/2025-2026/giornata-38", timeout=10)
        resp2 = requests.get(
            f"{BASE_URL}/seo/pronostici/serie-a/2026-2027/giornata-38", timeout=10)
        
        if resp1.status_code == 200 and resp2.status_code == 200:
            html1 = resp1.text
            html2 = resp2.text
            if html1 != html2:
                log_test("Season collision check: 2025-2026/38 vs 2026-2027/38 are different", 
                        True, "Pages have different content")
            else:
                log_test("Season collision check: 2025-2026/38 vs 2026-2027/38 are different",
                        False, "Pages have identical content")
        else:
            log_warning("Season collision check", 
                       f"Status codes: {resp1.status_code}, {resp2.status_code}")
    except Exception as e:
        log_test("Season collision check", False, str(e))

# ============================================================================
# MEDIUM PRIORITY TESTS
# ============================================================================

def test_health_checks():
    """Test 6: Health check endpoints"""
    print("\n" + "="*70)
    print("MEDIUM PRIORITY TEST 6: Health Checks")
    print("="*70)
    
    # Test /health
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "ok":
                log_test("GET /health", True, f"Status: {data.get('status')}")
            else:
                log_test("GET /health", False, f"Status not ok: {data}")
        else:
            log_test("GET /health", False, f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("GET /health", False, str(e))
    
    # Test /health/db
    try:
        resp = requests.get(f"{BASE_URL}/health/db", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "ok" and data.get("db") == "connected":
                log_test("GET /health/db", True, "DB connected")
            else:
                log_test("GET /health/db", False, f"Unexpected response: {data}")
        else:
            log_test("GET /health/db", False, f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("GET /health/db", False, str(e))

def test_connectors_and_logs(token: str):
    """Test 7: Connectors demo, settings, logs"""
    print("\n" + "="*70)
    print("MEDIUM PRIORITY TEST 7: Connectors Demo + Settings + Logs")
    print("="*70)
    
    if not token:
        log_test("Connectors and logs", False, "No auth token available")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test GET /admin/settings
    try:
        resp = requests.get(f"{BASE_URL}/admin/settings", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            integrations = data.get("integrations", {})
            
            # Check that odds_api and perplexity are false (demo mode)
            odds_api = integrations.get("odds_api", True)
            perplexity = integrations.get("perplexity", True)
            
            if odds_api is False and perplexity is False:
                log_test("GET /admin/settings shows demo integrations", True,
                        f"odds_api={odds_api}, perplexity={perplexity}")
            else:
                log_warning("GET /admin/settings integrations",
                           f"Expected false for demo: odds_api={odds_api}, perplexity={perplexity}")
        else:
            log_test("GET /admin/settings", False,
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("GET /admin/settings", False, str(e))
    
    # Test GET /admin/odds (demo mode)
    try:
        resp = requests.get(f"{BASE_URL}/admin/odds",
                           params={"match": "Juventus - Inter", "market": "1X2", "pick": "1"},
                           headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("demo") is True:
                log_test("GET /admin/odds returns demo=true", True)
            else:
                log_warning("GET /admin/odds", f"demo not true: {data}")
        else:
            log_test("GET /admin/odds", False,
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("GET /admin/odds", False, str(e))
    
    # Test GET /admin/press/search (demo mode)
    try:
        resp = requests.get(f"{BASE_URL}/admin/press/search",
                           params={"q": "UnoXdue"},
                           headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("demo") is True:
                log_test("GET /admin/press/search returns demo=true", True)
            else:
                log_warning("GET /admin/press/search", f"demo not true: {data}")
        else:
            log_test("GET /admin/press/search", False,
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("GET /admin/press/search", False, str(e))
    
    # Test GET /admin/logs
    try:
        resp = requests.get(f"{BASE_URL}/admin/logs", headers=headers, timeout=10)
        if resp.status_code == 200:
            logs = resp.json()
            if isinstance(logs, list):
                # Check for youtube_sync and ocr entries
                kinds = [log.get("kind") for log in logs]
                has_youtube = "youtube_sync" in kinds
                has_ocr = "ocr_slip" in kinds or "ocr" in str(kinds)
                
                log_test("GET /admin/logs returns list", True,
                        f"Total logs: {len(logs)}, youtube_sync: {has_youtube}, ocr: {has_ocr}")
            else:
                log_test("GET /admin/logs returns list", False,
                        f"Not a list: {type(logs)}")
        else:
            log_test("GET /admin/logs", False,
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("GET /admin/logs", False, str(e))

def test_sitemaps():
    """Test 8: Sitemaps and robots.txt"""
    print("\n" + "="*70)
    print("MEDIUM PRIORITY TEST 8: Sitemaps and Robots")
    print("="*70)
    
    # Test /sitemap.xml
    try:
        resp = requests.get(f"{BASE_URL}/sitemap.xml", timeout=10)
        if resp.status_code == 200:
            xml = resp.text
            if '<?xml version="1.0"' in xml and '<urlset' in xml:
                # Check for clean public URLs
                if "sportivo.preview.emergentagent.com" in xml:
                    log_test("GET /sitemap.xml", True, "Valid XML with public URLs")
                else:
                    log_warning("GET /sitemap.xml", "XML valid but URLs may not be clean")
            else:
                log_test("GET /sitemap.xml", False, "Not valid XML")
        else:
            log_test("GET /sitemap.xml", False,
                    f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log_test("GET /sitemap.xml", False, str(e))
    
    # Test /video-sitemap.xml
    try:
        resp = requests.get(f"{BASE_URL}/video-sitemap.xml", timeout=10)
        if resp.status_code == 200:
            xml = resp.text
            if '<?xml version="1.0"' in xml and '<urlset' in xml and 'video:video' in xml:
                if "sportivo.preview.emergentagent.com" in xml:
                    log_test("GET /video-sitemap.xml", True, "Valid video sitemap with public URLs")
                else:
                    log_warning("GET /video-sitemap.xml", "XML valid but URLs may not be clean")
            else:
                log_test("GET /video-sitemap.xml", False, "Not valid video sitemap XML")
        else:
            log_test("GET /video-sitemap.xml", False,
                    f"Status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log_test("GET /video-sitemap.xml", False, str(e))
    
    # Test /robots.txt
    try:
        resp = requests.get(f"{BASE_URL}/robots.txt", timeout=10)
        if resp.status_code == 200:
            txt = resp.text
            if "User-agent:" in txt and "Sitemap:" in txt:
                log_test("GET /robots.txt", True, "Valid robots.txt")
            else:
                log_test("GET /robots.txt", False, "Missing required directives")
        else:
            log_test("GET /robots.txt", False,
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("GET /robots.txt", False, str(e))

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    print("\n" + "="*70)
    print("UnoXdue Backend API Test Suite")
    print("="*70)
    print(f"Base URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print("="*70)
    
    # Run tests in priority order
    
    # HIGH PRIORITY
    token = test_admin_auth()
    test_ssr_pages()
    test_youtube_sync(token)
    test_ocr_schedina(token)
    test_predictions_crud(token)
    
    # MEDIUM PRIORITY
    test_health_checks()
    test_connectors_and_logs(token)
    test_sitemaps()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"✅ Passed: {len(test_results['passed'])}")
    print(f"❌ Failed: {len(test_results['failed'])}")
    print(f"⚠️  Warnings: {len(test_results['warnings'])}")
    
    if test_results['failed']:
        print("\nFailed Tests:")
        for fail in test_results['failed']:
            print(f"  ❌ {fail['name']}")
            print(f"     {fail['details']}")
    
    if test_results['warnings']:
        print("\nWarnings:")
        for warn in test_results['warnings']:
            print(f"  ⚠️  {warn['name']}")
            print(f"     {warn['details']}")
    
    print("="*70)
    
    # Exit code
    sys.exit(0 if len(test_results['failed']) == 0 else 1)

if __name__ == "__main__":
    main()
