#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  UnoXdue — podcast Serie A. Backend FastAPI + MongoDB + Jinja2 SSR. Stack confermato
  (React + FastAPI + Jinja2 + Mongo), deploy esterno. Implementati: SSR pagine pubbliche,
  CMS /admin (JWT), sync YouTube via feed RSS, OCR schedine con OpenAI Vision (Emergent key),
  connettori quote/stampa in demo, sitemap/video-sitemap/robots dinamici, log automazioni.

backend:
  - task: "Health checks (/api/health, /api/health/db)"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Endpoint health + ping Mongo."
        -working: true
        -agent: "testing"
        -comment: "✅ PASSED. GET /api/health returns 200 with status=ok. GET /api/health/db returns 200 with status=ok and db=connected. MongoDB connection verified."

  - task: "Admin auth JWT (login, me, protezione endpoint)"
    implemented: true
    working: true
    file: "backend/auth.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /api/admin/login (admin@unoxdue.net / unoxdue2026). Bearer token su tutti gli endpoint /api/admin/*. Verificare 401 senza token e 200 con token."
        -working: true
        -agent: "testing"
        -comment: "✅ PASSED. All auth flows working correctly: (1) Login with correct credentials returns 200 + JWT token, (2) Login with wrong password returns 401, (3) GET /admin/me without token returns 403, (4) GET /admin/me with Bearer token returns 200 with email and role=admin, (5) Protected endpoint /admin/episodes without token returns 403. JWT authentication fully functional."

  - task: "SSR pagine pubbliche (episodio/intervista/pronostici/team/archivi/home/il-podcast/parlano-di-noi)"
    implemented: true
    working: true
    file: "backend/seo.py, backend/server.py, backend/templates/*"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Verificare via GET (no JS) che l'HTML contenga H1, canonical, JSON-LD. Route: /api/seo/home, /api/seo/episodi, /api/seo/interviste, /api/seo/pronostici, /api/seo/pronostici/serie-a/2025-2026/giornata-38, /api/seo/team, /api/seo/team/antonello-santopaolo, /api/seo/episodi/{slug}, /api/seo/interviste/{slug}."
        -working: true
        -agent: "testing"
        -comment: "✅ PASSED. All 13 SSR pages tested successfully. Each page returns 200 and contains required elements: <h1>, <link rel='canonical'>, and <script type='application/ld+json'>. Specific validations: (1) /seo/pronostici/serie-a/2025-2026/giornata-38 contains 'Quota totale' and tipster names, (2) /seo/team/antonello-santopaolo contains Person JSON-LD, (3) /seo/interviste/fabio-ceravolo-130-gol-carriera renders correctly, (4) Non-existent slug returns 404 as expected. All SSR routes functional with proper SEO metadata."

  - task: "YouTube sync via feed RSS (creazione/aggiornamento contenuti)"
    implemented: true
    working: true
    file: "backend/automations.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /api/admin/sync/youtube (auth). Legge il feed del canale reale (UCN85Yle0zaIKue4ymUj1OCQ), classifica intervista/episodio/short, upsert in 'episodes'. Verificare ok=true e contatori."
        -working: true
        -agent: "testing"
        -comment: "✅ PASSED. POST /api/admin/sync/youtube returns 200 with ok=true. Real YouTube RSS feed successfully fetched and processed: Found 15 videos, Created 0 new, Updated 15 existing. GET /api/episodes returns 16 total episodes (including seeded content). YouTube sync automation working correctly with real feed from channel UCN85Yle0zaIKue4ymUj1OCQ."

  - task: "OCR schedine OpenAI Vision (Emergent key)"
    implemented: true
    working: true
    file: "backend/automations.py, backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /api/admin/predictions/ocr (multipart 'image', auth). USARE IMMAGINE JPEG/PNG REALE (vedi /app/image_testing.md). Deve restituire ok=true con data.selections e total_odds, SENZA importi/bonus/vincite. Model gpt-5.4 via EMERGENT_LLM_KEY."
        -working: true
        -agent: "testing"
        -comment: "✅ PASSED. POST /api/admin/predictions/ocr with real JPEG image returns 200 with ok=true. OpenAI Vision (gpt-5.4) via Emergent key successfully extracted 6 selections with total_odds=17.63. Each selection contains required fields: competition, date, match, market, pick, odds. VERIFIED: NO sensitive data (importo, bonus, vincita, stake, saldo) in output. OCR automation fully functional with proper data sanitization."

  - task: "Predictions CRUD + add-pick (vincolo competizione+stagione+giornata)"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /api/admin/predictions e /api/admin/predictions/add-pick (auth). Verificare merge per tipster e creazione pagina SSR pronostici. Test collisione: 2025-2026/38 e 2026-2027/38 devono essere due record diversi."
        -working: true
        -agent: "testing"
        -comment: "✅ PASSED. POST /api/admin/predictions/add-pick successfully creates prediction for Serie A 2026-2027 round 38 with tipster 'Il Marziano'. Returns 200 with ok=true and public_url. SSR page /seo/pronostici/serie-a/2026-2027/giornata-38 created and accessible. COLLISION TEST PASSED: Pages for 2025-2026/38 and 2026-2027/38 have different content, confirming unique constraint on (competition, season, round) works correctly."

  - task: "Connettori demo (quote, perplexity) + settings/integrations + logs"
    implemented: true
    working: true
    file: "backend/automations.py, backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "GET /api/admin/settings (integrazioni), GET /api/admin/odds, /api/admin/press/search (demo). GET /api/admin/logs. Verificare demo=true quando manca la chiave."
        -working: true
        -agent: "testing"
        -comment: "✅ PASSED. GET /api/admin/settings returns 200 with integrations object showing odds_api=false and perplexity=false (demo mode confirmed). GET /api/admin/odds returns 200 with demo=true. GET /api/admin/press/search returns 200 with demo=true. GET /api/admin/logs returns 200 with list of 5 logs including youtube_sync and ocr_slip entries. All connector demo modes and logging working correctly."

  - task: "Sitemap, video-sitemap, robots dinamici"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "GET /api/sitemap.xml, /api/video-sitemap.xml, /api/robots.txt. Devono includere le URL pulite (con dominio SITE_URL)."
        -working: true
        -agent: "testing"
        -comment: "✅ PASSED. GET /api/sitemap.xml returns 200 with valid XML containing clean public URLs (sportivo.preview.emergentagent.com). GET /api/video-sitemap.xml returns 200 with valid video sitemap XML including video:video tags and clean URLs. GET /api/robots.txt returns 200 with valid robots.txt containing User-agent and Sitemap directives. All SEO files dynamically generated correctly."

frontend:
  - task: "Pannello admin React /admin (login, dashboard, contenuti, schedine, log, integrazioni)"
    implemented: true
    working: "NA"
    file: "frontend/src/admin/*, frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "NON testare frontend senza permesso utente. Sito pubblico React resta su '/'. Admin su '/admin'."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: |
      Backend UnoXdue pronto per il test. Credenziali admin: admin@unoxdue.net / unoxdue2026 (env).
      Per l'OCR usare un'immagine REALE JPEG/PNG (regole in /app/image_testing.md) sull'endpoint
      POST /api/admin/predictions/ocr (campo multipart 'image'). Le pagine SSR sono sotto /api/seo/...
      (limite ambiente Emergent: in produzione saranno su URL pulite via nginx). Connettori quote e
      Perplexity sono in DEMO (nessuna chiave) e devono rispondere demo=true. Testare prima high_first.
    -agent: "testing"
    -message: |
      ✅ BACKEND TESTING COMPLETE - ALL TESTS PASSED (36/36)
      
      Comprehensive backend testing completed successfully. All 8 backend tasks tested and verified working:
      
      HIGH PRIORITY (5 tasks):
      1. Admin auth JWT - All flows working (login, token validation, protected endpoints)
      2. SSR public pages - All 13 pages rendering with proper SEO (H1, canonical, JSON-LD)
      3. YouTube sync - Real RSS feed integration working (15 videos found/updated)
      4. OCR schedina - OpenAI Vision via Emergent key working (6 selections extracted, no sensitive data)
      5. Predictions CRUD - add-pick working, collision test passed (different seasons properly separated)
      
      MEDIUM PRIORITY (3 tasks):
      6. Health checks - Both /health and /health/db returning 200
      7. Connectors demo - All demo modes working (odds_api, perplexity, logs)
      8. Sitemaps - All SEO files (sitemap.xml, video-sitemap.xml, robots.txt) generating correctly
      
      No critical issues found. No warnings. Backend MVP fully functional.
      Test file: /app/backend_test.py (can be re-run anytime)

