#!/usr/bin/env python3
"""
UnoXdue Backend Security Testing Suite
Tests admin auth security refactor + regression tests
"""
import requests
import json
import sys
import time
from pathlib import Path

# Configuration from env
BASE_URL = "https://sportivo.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@unoxdue.net"
OLD_PASSWORD = "unoxdue2026"
NEW_PASSWORD = "Sportivo#UxD-2026!"

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

def check_no_password_in_response(data: dict, test_name: str):
    """Verify no password or password_hash in response"""
    # Check for actual password fields, not the must_change_password flag
    if "password_hash" in data or "password" in data:
        log_test(f"{test_name} - No password/password_hash field in response", False, 
                f"Found password field in response: {data}")
        return False
    else:
        log_test(f"{test_name} - No password/password_hash field in response", True)
        return True

# ============================================================================
# SECURITY TESTS (HIGH PRIORITY)
# ============================================================================

def test_1_old_password_fails():
    """Test 1: OLD password must fail with 401"""
    print("\n" + "="*70)
    print("SECURITY TEST 1: Old password must fail")
    print("="*70)
    
    try:
        resp = requests.post(f"{BASE_URL}/admin/login", 
                            json={"email": ADMIN_EMAIL, "password": OLD_PASSWORD},
                            timeout=10)
        if resp.status_code == 401:
            log_test("Login with OLD password returns 401", True, 
                    f"Correctly rejected old password")
        else:
            log_test("Login with OLD password returns 401", False,
                    f"Expected 401, got {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("Login with OLD password returns 401", False, str(e))

def test_2_new_password_works():
    """Test 2: NEW password must work and return must_change_password"""
    print("\n" + "="*70)
    print("SECURITY TEST 2: New password works with must_change_password flag")
    print("="*70)
    
    try:
        resp = requests.post(f"{BASE_URL}/admin/login", 
                            json={"email": ADMIN_EMAIL, "password": NEW_PASSWORD},
                            timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            
            # Check for token
            if "token" not in data:
                log_test("Login with NEW password returns token", False, 
                        "No token in response")
                return None
            
            token = data["token"]
            log_test("Login with NEW password returns token", True)
            
            # Check for email
            if data.get("email") == ADMIN_EMAIL:
                log_test("Login response contains correct email", True)
            else:
                log_test("Login response contains correct email", False,
                        f"Expected {ADMIN_EMAIL}, got {data.get('email')}")
            
            # Check for must_change_password flag
            if "must_change_password" in data:
                log_test("Login response contains must_change_password flag", True,
                        f"must_change_password={data['must_change_password']}")
            else:
                log_test("Login response contains must_change_password flag", False,
                        "Flag not present in response")
            
            # Verify no password in response
            check_no_password_in_response(data, "Login")
            
            return token
        else:
            log_test("Login with NEW password", False,
                    f"Status {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        log_test("Login with NEW password", False, str(e))
        return None

def test_3_admin_me_with_token(token: str):
    """Test 3: GET /admin/me with token shows must_change_password"""
    print("\n" + "="*70)
    print("SECURITY TEST 3: GET /admin/me with token")
    print("="*70)
    
    if not token:
        log_test("GET /admin/me with token", False, "No token available")
        return
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/admin/me", headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            log_test("GET /admin/me returns 200", True)
            
            # Check for must_change_password
            if "must_change_password" in data:
                log_test("GET /admin/me contains must_change_password", True,
                        f"must_change_password={data['must_change_password']}")
            else:
                log_test("GET /admin/me contains must_change_password", False,
                        "Flag not present")
            
            # Check for email and role
            if data.get("email") and data.get("role"):
                log_test("GET /admin/me contains email and role", True,
                        f"email={data['email']}, role={data['role']}")
            else:
                log_test("GET /admin/me contains email and role", False,
                        f"Missing fields: {data}")
            
            # Verify no password in response
            check_no_password_in_response(data, "GET /admin/me")
        else:
            log_test("GET /admin/me with token", False,
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("GET /admin/me with token", False, str(e))

def test_4_protected_endpoints_without_token():
    """Test 4: Protected endpoints without token return 401/403"""
    print("\n" + "="*70)
    print("SECURITY TEST 4: Protected endpoints without token")
    print("="*70)
    
    # Test /admin/me without token
    try:
        resp = requests.get(f"{BASE_URL}/admin/me", timeout=10)
        if resp.status_code in [401, 403]:
            log_test("GET /admin/me without token returns 401/403", True,
                    f"Status: {resp.status_code}")
        else:
            log_test("GET /admin/me without token returns 401/403", False,
                    f"Expected 401/403, got {resp.status_code}")
    except Exception as e:
        log_test("GET /admin/me without token returns 401/403", False, str(e))
    
    # Test /admin/episodes without token
    try:
        resp = requests.get(f"{BASE_URL}/admin/episodes", timeout=10)
        if resp.status_code in [401, 403]:
            log_test("GET /admin/episodes without token returns 401/403", True,
                    f"Status: {resp.status_code}")
        else:
            log_test("GET /admin/episodes without token returns 401/403", False,
                    f"Expected 401/403, got {resp.status_code}")
    except Exception as e:
        log_test("GET /admin/episodes without token returns 401/403", False, str(e))

def test_5_token_invalidation_via_password_change(token: str):
    """Test 5: Token invalidation after password change"""
    print("\n" + "="*70)
    print("SECURITY TEST 5: Token invalidation via password change")
    print("="*70)
    
    if not token:
        log_test("Token invalidation test", False, "No token available")
        return None
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 1: Change password to temporary password
    try:
        payload = {
            "current_password": NEW_PASSWORD,
            "new_password": "TempPwd#2026!"
        }
        resp = requests.post(f"{BASE_URL}/admin/change-password",
                            headers=headers, json=payload, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            log_test("POST /admin/change-password with correct current_password", True,
                    f"Password changed successfully")
            
            # Check for new token
            if "token" not in data:
                log_test("change-password returns new token", False,
                        "No token in response")
                return None
            
            new_token = data["token"]
            log_test("change-password returns new token", True)
            
            # Verify no password in response
            check_no_password_in_response(data, "change-password")
        else:
            log_test("POST /admin/change-password", False,
                    f"Status {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        log_test("POST /admin/change-password", False, str(e))
        return None
    
    # Step 2: OLD token should now be INVALID
    try:
        resp = requests.get(f"{BASE_URL}/admin/me", headers=headers, timeout=10)
        if resp.status_code == 401:
            log_test("Old token is INVALID after password change", True,
                    "Old token correctly rejected with 401")
        else:
            log_test("Old token is INVALID after password change", False,
                    f"Expected 401, got {resp.status_code}")
    except Exception as e:
        log_test("Old token is INVALID after password change", False, str(e))
    
    # Step 3: NEW token should work
    try:
        new_headers = {"Authorization": f"Bearer {new_token}"}
        resp = requests.get(f"{BASE_URL}/admin/me", headers=new_headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            log_test("New token works after password change", True)
            
            # Check must_change_password is now false
            if data.get("must_change_password") is False:
                log_test("must_change_password is false after password change", True)
            else:
                log_test("must_change_password is false after password change", False,
                        f"Expected false, got {data.get('must_change_password')}")
        else:
            log_test("New token works after password change", False,
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("New token works after password change", False, str(e))
    
    # Step 4: Test negative cases
    # Wrong current_password
    try:
        payload = {
            "current_password": "WrongPassword123!",
            "new_password": "AnotherPwd#2026!"
        }
        resp = requests.post(f"{BASE_URL}/admin/change-password",
                            headers=new_headers, json=payload, timeout=10)
        
        if resp.status_code == 400:
            log_test("change-password with wrong current_password returns 400", True)
        else:
            log_test("change-password with wrong current_password returns 400", False,
                    f"Expected 400, got {resp.status_code}")
    except Exception as e:
        log_test("change-password with wrong current_password returns 400", False, str(e))
    
    # New password too short
    try:
        payload = {
            "current_password": "TempPwd#2026!",
            "new_password": "short"
        }
        resp = requests.post(f"{BASE_URL}/admin/change-password",
                            headers=new_headers, json=payload, timeout=10)
        
        if resp.status_code == 400:
            log_test("change-password with short new_password returns 400", True)
        else:
            log_test("change-password with short new_password returns 400", False,
                    f"Expected 400, got {resp.status_code}")
    except Exception as e:
        log_test("change-password with short new_password returns 400", False, str(e))
    
    # Step 5: Restore password back to original
    try:
        payload = {
            "current_password": "TempPwd#2026!",
            "new_password": NEW_PASSWORD
        }
        resp = requests.post(f"{BASE_URL}/admin/change-password",
                            headers=new_headers, json=payload, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            log_test("Restore password back to original", True)
            
            # Return the final token
            return data.get("token")
        else:
            log_test("Restore password back to original", False,
                    f"Status {resp.status_code}: {resp.text}")
            return new_token
    except Exception as e:
        log_test("Restore password back to original", False, str(e))
        return new_token

def test_6_rate_limiting():
    """Test 6: Rate limiting with throwaway email"""
    print("\n" + "="*70)
    print("SECURITY TEST 6: Rate limiting / lockout")
    print("="*70)
    
    throwaway_email = "tester-rl@example.com"
    
    # Try to login 6 times with wrong password
    locked = False
    for i in range(6):
        try:
            resp = requests.post(f"{BASE_URL}/admin/login",
                                json={"email": throwaway_email, "password": "wrongpassword"},
                                timeout=10)
            
            if resp.status_code == 429:
                log_test(f"Rate limiting triggered after {i+1} attempts", True,
                        f"Status 429: {resp.json().get('detail', '')}")
                locked = True
                break
            elif resp.status_code == 401:
                # Expected for wrong credentials
                pass
            else:
                log_warning(f"Attempt {i+1}", f"Unexpected status {resp.status_code}")
        except Exception as e:
            log_test(f"Rate limiting test attempt {i+1}", False, str(e))
            break
    
    if not locked:
        log_warning("Rate limiting", "Did not trigger 429 after 6 attempts")
    
    # Verify real admin can still login
    try:
        resp = requests.post(f"{BASE_URL}/admin/login",
                            json={"email": ADMIN_EMAIL, "password": NEW_PASSWORD},
                            timeout=10)
        
        if resp.status_code == 200:
            log_test("Real admin login still works after rate limit test", True)
        else:
            log_test("Real admin login still works after rate limit test", False,
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("Real admin login still works after rate limit test", False, str(e))

# ============================================================================
# REGRESSION TESTS (MUST STILL WORK)
# ============================================================================

def test_7_youtube_sync(token: str):
    """Test 8: YouTube sync still works"""
    print("\n" + "="*70)
    print("REGRESSION TEST 7: YouTube sync")
    print("="*70)
    
    if not token:
        log_test("YouTube sync", False, "No token available")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        print("  Triggering YouTube sync (may take 10-20 seconds)...")
        resp = requests.post(f"{BASE_URL}/admin/sync/youtube",
                            headers=headers, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok") is True:
                log_test("POST /admin/sync/youtube", True,
                        f"Found: {data.get('found', 0)}, Created: {data.get('created', 0)}, Updated: {data.get('updated', 0)}")
                
                # Idempotency check: second run should create ~0
                print("  Running sync again to check idempotency...")
                resp2 = requests.post(f"{BASE_URL}/admin/sync/youtube",
                                     headers=headers, timeout=30)
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    created2 = data2.get("created", 0)
                    if created2 == 0:
                        log_test("YouTube sync is idempotent (2nd run created 0)", True)
                    else:
                        log_warning("YouTube sync idempotency",
                                   f"2nd run created {created2} (expected 0)")
            else:
                log_test("POST /admin/sync/youtube", False, f"ok=false: {data}")
        else:
            log_test("POST /admin/sync/youtube", False,
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("POST /admin/sync/youtube", False, str(e))

def test_8_settings_and_logs(token: str):
    """Test 9: Settings and logs still work"""
    print("\n" + "="*70)
    print("REGRESSION TEST 8: Settings and logs")
    print("="*70)
    
    if not token:
        log_test("Settings and logs", False, "No token available")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test GET /admin/settings
    try:
        resp = requests.get(f"{BASE_URL}/admin/settings", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            integrations = data.get("integrations", {})
            log_test("GET /admin/settings", True,
                    f"odds_api={integrations.get('odds_api')}, perplexity={integrations.get('perplexity')}")
        else:
            log_test("GET /admin/settings", False,
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("GET /admin/settings", False, str(e))
    
    # Test GET /admin/logs
    try:
        resp = requests.get(f"{BASE_URL}/admin/logs", headers=headers, timeout=10)
        if resp.status_code == 200:
            logs = resp.json()
            if isinstance(logs, list):
                log_test("GET /admin/logs", True, f"Total logs: {len(logs)}")
            else:
                log_test("GET /admin/logs", False, f"Not a list: {type(logs)}")
        else:
            log_test("GET /admin/logs", False,
                    f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_test("GET /admin/logs", False, str(e))

def test_9_ssr_pages():
    """Test 10: SSR pages still work"""
    print("\n" + "="*70)
    print("REGRESSION TEST 9: SSR pages")
    print("="*70)
    
    pages = [
        "/seo/home",
        "/seo/episodi",
        "/seo/pronostici/serie-a/2025-2026/giornata-38",
        "/seo/team/antonello-santopaolo"
    ]
    
    for path in pages:
        try:
            resp = requests.get(f"{BASE_URL}{path}", timeout=15)
            if resp.status_code == 200:
                html = resp.text
                has_h1 = "<h1" in html
                has_canonical = 'rel="canonical"' in html
                has_jsonld = 'application/ld+json' in html
                
                if has_h1 and has_canonical and has_jsonld:
                    log_test(f"SSR page {path}", True, "Contains H1, canonical, JSON-LD")
                else:
                    missing = []
                    if not has_h1: missing.append("H1")
                    if not has_canonical: missing.append("canonical")
                    if not has_jsonld: missing.append("JSON-LD")
                    log_test(f"SSR page {path}", False, f"Missing: {', '.join(missing)}")
            else:
                log_test(f"SSR page {path}", False, f"Status {resp.status_code}")
        except Exception as e:
            log_test(f"SSR page {path}", False, str(e))

def test_10_sitemaps():
    """Test 11: Sitemaps still work"""
    print("\n" + "="*70)
    print("REGRESSION TEST 10: Sitemaps")
    print("="*70)
    
    # Test /sitemap.xml
    try:
        resp = requests.get(f"{BASE_URL}/sitemap.xml", timeout=10)
        if resp.status_code == 200:
            xml = resp.text
            if '<?xml version="1.0"' in xml and '<urlset' in xml:
                log_test("GET /sitemap.xml", True, "Valid XML")
            else:
                log_test("GET /sitemap.xml", False, "Not valid XML")
        else:
            log_test("GET /sitemap.xml", False, f"Status {resp.status_code}")
    except Exception as e:
        log_test("GET /sitemap.xml", False, str(e))
    
    # Test /video-sitemap.xml
    try:
        resp = requests.get(f"{BASE_URL}/video-sitemap.xml", timeout=10)
        if resp.status_code == 200:
            xml = resp.text
            if '<?xml version="1.0"' in xml and 'video:video' in xml:
                log_test("GET /video-sitemap.xml", True, "Valid video sitemap")
            else:
                log_test("GET /video-sitemap.xml", False, "Not valid video sitemap")
        else:
            log_test("GET /video-sitemap.xml", False, f"Status {resp.status_code}")
    except Exception as e:
        log_test("GET /video-sitemap.xml", False, str(e))

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    print("\n" + "="*70)
    print("UnoXdue Backend Security Testing Suite")
    print("="*70)
    print(f"Base URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print(f"Testing OLD password: {OLD_PASSWORD}")
    print(f"Testing NEW password: {NEW_PASSWORD}")
    print("="*70)
    
    # SECURITY TESTS
    test_1_old_password_fails()
    token = test_2_new_password_works()
    test_3_admin_me_with_token(token)
    test_4_protected_endpoints_without_token()
    final_token = test_5_token_invalidation_via_password_change(token)
    test_6_rate_limiting()
    
    # Use final token for regression tests
    if not final_token:
        print("\n⚠️  No valid token for regression tests, attempting fresh login...")
        try:
            resp = requests.post(f"{BASE_URL}/admin/login",
                                json={"email": ADMIN_EMAIL, "password": NEW_PASSWORD},
                                timeout=10)
            if resp.status_code == 200:
                final_token = resp.json().get("token")
        except:
            pass
    
    # REGRESSION TESTS
    test_7_youtube_sync(final_token)
    test_8_settings_and_logs(final_token)
    test_9_ssr_pages()
    test_10_sitemaps()
    
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
