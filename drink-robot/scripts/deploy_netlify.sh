#!/usr/bin/env bash
# Rebuild the static demo site from config.yaml and push it to Netlify.
#   NETLIFY_AUTH_TOKEN=xxxx bash scripts/deploy_netlify.sh
# Get a token at app.netlify.com -> User settings -> Applications -> Personal access tokens.
set -euo pipefail
cd "$(dirname "$0")/.."
SITE_ID="${NETLIFY_SITE_ID:-1d808cf4-d70f-495e-8dc7-19f40a5bcd6b}"   # garage-drinkbot-baf257.netlify.app
python3 scripts/build_site.py
ZIP="$(mktemp -d)/site.zip"
(cd site/dist && python3 -c "import zipfile,os; z=zipfile.ZipFile('$ZIP','w',zipfile.ZIP_DEFLATED); [z.write(f) for f in os.listdir('.')]; z.close()")
AUTH=()
[ -n "${NETLIFY_AUTH_TOKEN:-}" ] && AUTH=(-H "Authorization: Bearer ${NETLIFY_AUTH_TOKEN}")
curl -sS -X POST "https://api.netlify.com/api/v1/sites/${SITE_ID}/deploys" "${AUTH[@]}" \
  -H "Content-Type: application/zip" --data-binary @"$ZIP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('state'), d.get('ssl_url') or d)"
