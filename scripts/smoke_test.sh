#!/usr/bin/env bash
# UnoXdue — smoke test post-deploy. Verifica routing pubblico SSR + /admin SPA + API + 404.
# Uso: bash scripts/smoke_test.sh https://unoxdue.net [slug-episodio] [slug-team]
set -uo pipefail
BASE="${1:-http://localhost}"
EP_SLUG="${2:-}"
TEAM_SLUG="${3:-}"

pass=0; fail=0
check() { # check <descr> <url> <atteso_status> <atteso: SSR|SPA|ANY> <not_contains_div_root: yes|no>
  local d="$1" u="$2" exp="$3" mode="$4"
  local body status ren
  body="$(curl -s "$u")"
  status="$(curl -s -o /dev/null -w '%{http_code}' "$u")"
  if echo "$body" | grep -qE '<div id="?root"?>'; then ren="SPA"; else ren="SSR"; fi
  local oks="OK"
  [ "$status" = "$exp" ] || oks="FAIL(status=$status exp=$exp)"
  if [ "$mode" = "SSR" ] && [ "$ren" = "SPA" ]; then oks="FAIL(SPA su route pubblica)"; fi
  if [ "$mode" = "SPA" ] && [ "$ren" = "SSR" ]; then oks="FAIL(atteso SPA)"; fi
  if [ "$oks" = "OK" ]; then pass=$((pass+1)); else fail=$((fail+1)); fi
  printf "  [%-4s] %-44s status=%-3s render=%-3s %s\n" "$oks" "$d" "$status" "$ren" "$u"
}

echo "== UnoXdue smoke test su $BASE =="
check "home /"                 "$BASE/"                       200 SSR
check "/il-podcast/"           "$BASE/il-podcast/"            200 SSR
check "/episodi/"              "$BASE/episodi/"               200 SSR
check "/interviste/"           "$BASE/interviste/"            200 SSR
check "/pronostici/"           "$BASE/pronostici/"            200 SSR
check "/team/"                 "$BASE/team/"                  200 SSR
check "/parlano-di-noi/"       "$BASE/parlano-di-noi/"        200 SSR
[ -n "$EP_SLUG" ] && check "episodio"      "$BASE/episodi/$EP_SLUG/"               200 SSR
[ -n "$EP_SLUG" ] && check "trascrizione"  "$BASE/episodi/$EP_SLUG/trascrizione/"  200 SSR
[ -n "$TEAM_SLUG" ] && check "profilo team" "$BASE/team/$TEAM_SLUG/"               200 SSR
check "route inesistente (404 HTML SSR)" "$BASE/pagina-inesistente-xyz/" 404 SSR
check "/admin/ (SPA)"          "$BASE/admin/"                 200 SPA
check "/api/health"            "$BASE/api/health"             200 ANY
check "/sitemap.xml"           "$BASE/sitemap.xml"            200 ANY
check "/video-sitemap.xml"     "$BASE/video-sitemap.xml"      200 ANY
check "/robots.txt"            "$BASE/robots.txt"             200 ANY

echo "== Risultato: $pass OK / $fail FAIL =="
[ "$fail" = 0 ] || exit 1
