#!/usr/bin/env bash
# Professor spike — OpenWebUI bootstrap (run as root on Banner from /opt/stacks/professor/deploy)
#
#   sudo ./setup_openwebui.sh
#
# Idempotent: creates the admin account on first run (credentials stored root-only
# at /root/professor-openwebui-admin.env), signs in on later runs, then installs
# or updates + activates the "Professor" manifold pipe function (one model per
# personality: Myron Golden, Pastor Chris Durkin).
# Prints status codes, lengths, and model ids only — never credential values.
set -euo pipefail

BASE="${OPENWEBUI_URL:-http://localhost:5060}"
# Prefer the dedicated service-admin account: Matt owns (and may change the
# password of) the original admin login, which must never break automation.
CRED_FILE=/root/professor-openwebui-admin.env
[ -f /root/professor-openwebui-service.env ] && CRED_FILE=/root/professor-openwebui-service.env
PIPE_FILE="$(dirname "$0")/pipe_professor.py"
FUNCTION_ID=professor_myron
ADMIN_EMAIL="matt@gerasolo.com"
ADMIN_NAME="Matt"

command -v jq >/dev/null || { echo "jq required"; exit 1; }
[ -f "$PIPE_FILE" ] || { echo "pipe file missing: $PIPE_FILE"; exit 1; }

echo "== waiting for OpenWebUI at $BASE =="
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health" || true)
  [ "$code" = 200 ] && break
  sleep 2
done
[ "$code" = 200 ] || { echo "OpenWebUI not healthy (last=$code)"; exit 1; }
echo "health: 200"

# ---- admin account ---------------------------------------------------------
if [ ! -f "$CRED_FILE" ]; then
  PW=$(python3 -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(20)))")
  umask 077
  printf 'OPENWEBUI_ADMIN_EMAIL=%s\nOPENWEBUI_ADMIN_PASSWORD=%s\n' "$ADMIN_EMAIL" "$PW" > "$CRED_FILE"
  echo "credentials generated and stored at $CRED_FILE (password: 20 chars, ends '…${PW: -2}')"
else
  echo "credentials file already present at $CRED_FILE"
fi
# shellcheck disable=SC1090
. "$CRED_FILE"
PW="$OPENWEBUI_ADMIN_PASSWORD"
ADMIN_EMAIL="$OPENWEBUI_ADMIN_EMAIL"   # the cred file's account, not the default

signup_code=$(curl -s -o /tmp/.owui-auth.json -w '%{http_code}' \
  -X POST "$BASE/api/v1/auths/signup" -H 'Content-Type: application/json' \
  -d "$(jq -n --arg n "$ADMIN_NAME" --arg e "$ADMIN_EMAIL" --arg p "$PW" '{name:$n,email:$e,password:$p}')")
if [ "$signup_code" = 200 ]; then
  echo "admin account created (signup: 200)"
else
  echo "signup: $signup_code (already exists) — signing in"
  signin_code=$(curl -s -o /tmp/.owui-auth.json -w '%{http_code}' \
    -X POST "$BASE/api/v1/auths/signin" -H 'Content-Type: application/json' \
    -d "$(jq -n --arg e "$ADMIN_EMAIL" --arg p "$PW" '{email:$e,password:$p}')")
  [ "$signin_code" = 200 ] || { echo "signin failed: $signin_code"; exit 1; }
  echo "signin: 200"
fi
TOKEN=$(jq -r '.token' /tmp/.owui-auth.json)
rm -f /tmp/.owui-auth.json
[ -n "$TOKEN" ] && [ "$TOKEN" != null ] || { echo "no token in auth response"; exit 1; }
echo "token acquired (length: ${#TOKEN})"
AUTH=(-H "Authorization: Bearer $TOKEN")

# ---- pipe function ---------------------------------------------------------
BODY=$(jq -n --arg id "$FUNCTION_ID" --arg name "Professor" \
  --rawfile content "$PIPE_FILE" \
  '{id:$id, name:$name, content:$content,
    meta:{description:"Three-tier personality-grounded RAG professors (Myron Golden, Pastor Chris Durkin) with timestamped YouTube citations", manifest:{}}}')

create_code=$(curl -s -o /tmp/.owui-fn.json -w '%{http_code}' \
  -X POST "$BASE/api/v1/functions/create" "${AUTH[@]}" \
  -H 'Content-Type: application/json' -d "$BODY")
if [ "$create_code" = 200 ]; then
  echo "function create: 200"
else
  echo "function create: $create_code — trying update"
  update_code=$(curl -s -o /tmp/.owui-fn.json -w '%{http_code}' \
    -X POST "$BASE/api/v1/functions/id/$FUNCTION_ID/update" "${AUTH[@]}" \
    -H 'Content-Type: application/json' -d "$BODY")
  [ "$update_code" = 200 ] || { echo "function update failed: $update_code"; cat /tmp/.owui-fn.json; exit 1; }
  echo "function update: 200"
fi
rm -f /tmp/.owui-fn.json

active=$(curl -s "$BASE/api/v1/functions/" "${AUTH[@]}" \
  | jq -r ".[] | select(.id==\"$FUNCTION_ID\") | .is_active")
if [ "$active" != "true" ]; then
  toggle_code=$(curl -s -o /dev/null -w '%{http_code}' \
    -X POST "$BASE/api/v1/functions/id/$FUNCTION_ID/toggle" "${AUTH[@]}")
  echo "function toggle → active: $toggle_code"
else
  echo "function already active"
fi

echo "== models visible to admin =="
curl -s "$BASE/api/models" "${AUTH[@]}" | jq -r '.data[].id'
