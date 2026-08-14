#!/usr/bin/env bash
# Handoff 2.0 — session-start inbox surface (the wake bus's safety net).
#
# Drop this into a participant project's .claude/hooks/ (SessionStart). When
# the project's H2 inbox is non-empty it prints an "UNREAD HANDOFF MAIL (N)"
# block so waiting mail surfaces the moment a session opens; when the inbox is
# empty it prints NOTHING. It NEVER fails the session — every exit path is 0,
# including no token, no network, and a down broker. Mail waits in the
# registry either way; this script is a surface, not the delivery.
#
# Dependencies: curl + python3 (prefers `handoff2-dispatch inbox --json` when
# that CLI is on PATH — same JSON either way).
#
# Configuration, from the environment (the onboarding-issued env file):
#   H2_TOKEN       required — without it this is a silent no-op
#   H2_SERVER_URL  default http://10.0.0.35:3542

[ -z "${H2_TOKEN:-}" ] && exit 0

if command -v handoff2-dispatch >/dev/null 2>&1; then
    RESP="$(handoff2-dispatch inbox --json 2>/dev/null)" || exit 0
else
    BASE="${H2_SERVER_URL:-http://10.0.0.35:3542}"
    RESP="$(curl -sf -m 8 -H "Authorization: Bearer ${H2_TOKEN}" "${BASE}/inbox" 2>/dev/null)" || exit 0
fi
[ -z "${RESP}" ] && exit 0

# The response travels via the environment, NOT a pipe: the heredoc below IS
# python's stdin (it carries the program), so piped input would be lost.
H2_INBOX_RESP="${RESP}" python3 - <<'PY' 2>/dev/null || true
import json, os, sys
try:
    data = json.loads(os.environ.get("H2_INBOX_RESP") or "{}")
except Exception:
    sys.exit(0)
ds = data.get("dispatches") or []
if not ds:
    sys.exit(0)
print(f"UNREAD HANDOFF MAIL ({len(ds)}):")
for d in ds:
    print("  {hid}  [{st}]  from {who}  {typ}  {intent}".format(
        hid=d.get("hid", "?"),
        st=d.get("dispatch_status") or d.get("status") or "?",
        who=d.get("requester") or "?",
        typ=d.get("request_type") or "?",
        intent=(d.get("intent") or "")[:70]))
print("  -> triage with `handoff2-dispatch show/claim/complete <hid>` "
      "(or the h2_my_inbox MCP tool). The registry is the truth; "
      "this block is only the surface.")
PY
exit 0
