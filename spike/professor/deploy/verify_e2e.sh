#!/usr/bin/env bash
# Professor spike — end-to-end verification through OpenWebUI's API (run as root on Banner).
# Prints structure summaries and status codes only; never credentials or full answer text.
set -euo pipefail

BASE="${OPENWEBUI_URL:-http://localhost:5060}"
CRED_FILE=/root/professor-openwebui-admin.env
# shellcheck disable=SC1090
. "$CRED_FILE"

TOKEN=$(curl -s -X POST "$BASE/api/v1/auths/signin" -H 'Content-Type: application/json' \
  -d "$(jq -n --arg e "$OPENWEBUI_ADMIN_EMAIL" --arg p "$OPENWEBUI_ADMIN_PASSWORD" '{email:$e,password:$p}')" \
  | jq -r '.token')
[ -n "$TOKEN" ] && [ "$TOKEN" != null ] || { echo "signin failed"; exit 1; }

echo "== 1. model list =="
curl -s "$BASE/api/models" -H "Authorization: Bearer $TOKEN" \
  | jq -r '.data[] | "\(.id)  →  \(.name)"'

echo
echo "== 2. non-stream chat completion (multi-turn) =="
REQ='{"model":"professor_myron","stream":false,"messages":[
  {"role":"user","content":"How do I make my offer irresistible?"},
  {"role":"assistant","content":"You make an offer irresistible by increasing its value until saying no feels like losing money."},
  {"role":"user","content":"What did he say about pricing it?"}]}'
start=$(date +%s)
code=$(curl -s -o /tmp/.owui-e2e.json -w '%{http_code}' -m 300 \
  -X POST "$BASE/api/chat/completions" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d "$REQ")
elapsed=$(( $(date +%s) - start ))
echo "HTTP $code in ${elapsed}s"
python3 - <<'EOF'
import json, re
d = json.load(open('/tmp/.owui-e2e.json'))
print("top-level keys:", sorted(d.keys()))
content = d["choices"][0]["message"]["content"]
print("content length:", len(content))
for header in ("📖 What Myron has said", "💭 What Myron might say", "🤖 Beyond Myron — AI extension"):
    print(f"tier section {header!r}:", "PRESENT" if header in content else "MISSING")
print("disclaimer line:", "PRESENT" if "AI recreation from public videos" in content else "MISSING")
m = re.search(r"```html\n(.*?)\n```", content, re.S)
print("html artifact block:", "PRESENT" if m else "MISSING")
if m:
    html_doc = m.group(1)
    embed = re.search(r'youtube\.com/embed/([\w-]+)\?start=(\d+)', html_doc)
    print("  youtube embed iframe:", f"video {embed.group(1)} @ {embed.group(2)}s" if embed else "MISSING")
    print("  citation links:", len(re.findall(r'<li><a href="https://youtube\.com/watch', html_doc)))
if "sources" in d:
    print("sources in response:", len(d["sources"]))
EOF
rm -f /tmp/.owui-e2e.json

echo
echo "== 3. streamed completion — citation/source events =="
REQ2='{"model":"professor_myron","stream":true,"messages":[{"role":"user","content":"What does the Bible say about wealth according to Myron?"}]}'
curl -s -N -m 300 -X POST "$BASE/api/chat/completions" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d "$REQ2" \
  > /tmp/.owui-stream.txt
python3 - <<'EOF'
import json
events, chunks, other = [], 0, {}
for line in open('/tmp/.owui-stream.txt'):
    line = line.strip()
    if not line.startswith("data: ") or line == "data: [DONE]":
        continue
    try:
        obj = json.loads(line[6:])
    except ValueError:
        continue
    if "choices" in obj:
        chunks += 1
    elif obj.get("event"):
        events.append(obj["event"])
    else:
        for key in obj:
            other[key] = other.get(key, 0) + 1
types = {}
for event in events:
    types[event.get("type")] = types.get(event.get("type"), 0) + 1
print("content chunks:", chunks, "| event frames by type:", types, "| other frames:", other)
cites = [e for e in events if e.get("type") in ("citation", "source")]
print("citation/source events:", len(cites))
if cites:
    d = cites[0].get("data", {})
    print("first event source.name:", d.get("source", {}).get("name"))
    md = (d.get("metadata") or [{}])[0]
    print("first event metadata (all values str?):",
          all(isinstance(v, str) for v in md.values()), "| keys:", sorted(md.keys()))
EOF
rm -f /tmp/.owui-stream.txt
