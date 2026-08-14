#!/usr/bin/env bash
# Store the YouTube proxy credential and prove it works, without the value ever
# passing through a chat transcript, a shell history entry, or a command line.
#
#   bash scripts/set-youtube-proxy.sh
#
# Webshare is the default path: you need only the "Proxy Username" and "Proxy
# Password" from https://dashboard.webshare.io/proxy/settings — not a host, not
# a port, not an IP allowlist entry. Buy the **Residential** package; "Proxy
# Server" and "Static Residential" are datacenter ranges that YouTube blocks
# roughly as hard as it blocks us, so they will not fix anything.
#
# Nothing is stored until a real transcript has come back through the proxy.

set -euo pipefail

cd "$(dirname "$0")/.."

CONTAINER="knowledge-transcript-service"
# Any video with English captions; used only as a liveness probe.
PROBE_VIDEO="${PROBE_VIDEO:-7x0SeJ2s2ps}"
# Rotating-pool country filter. Closer IPs are faster; blank means the whole pool.
LOCATIONS="${WEBSHARE_PROXY_LOCATIONS:-US}"

echo "Webshare credentials — from https://dashboard.webshare.io/proxy/settings"
echo "(these are the PROXY username/password, not your account login)"
echo

read -r -p "Proxy Username: " WS_USER
# Silent, but confirm something landed. A hidden prompt with no feedback is how
# a mistyped or empty paste gets stored and then discovered days later.
read -r -s -p "Proxy Password (hidden): " WS_PASS
echo
echo "  captured: ${#WS_PASS} characters, ending '${WS_PASS: -2}'"

if [ -z "$WS_USER" ] || [ -z "$WS_PASS" ]; then
  echo "ERROR: both values are required. Nothing stored." >&2
  exit 1
fi

echo
echo "Verifying through Webshare before storing anything..."
if ! docker exec \
      -e WS_USER="$WS_USER" -e WS_PASS="$WS_PASS" \
      -e LOCATIONS="$LOCATIONS" -e PROBE_VIDEO="$PROBE_VIDEO" \
      "$CONTAINER" python3 - <<'PY'
import os, sys, requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

locations = [c.strip().upper() for c in os.environ["LOCATIONS"].split(",") if c.strip()]
cfg = WebshareProxyConfig(
    proxy_username=os.environ["WS_USER"],
    proxy_password=os.environ["WS_PASS"],
    filter_ip_locations=locations or None,
)
proxies = {"http": cfg.http_url, "https": cfg.https_url}

# 1. Does the proxy carry traffic at all, and where does it come out?
try:
    ip = requests.get("https://api.ipify.org", proxies=proxies, timeout=45).text.strip()
except Exception as e:
    print(f"  FAILED at the proxy itself — {type(e).__name__}: {str(e)[:160]}")
    print("  Check the username/password, and that the package is Residential.")
    sys.exit(1)

# 2. Is it actually a different address than ours? A proxy that resolves to our
#    own IP buys nothing, and the whole point here is a different exit.
try:
    direct = requests.get("https://api.ipify.org", timeout=20).text.strip()
except Exception:
    direct = None
print(f"  proxy exit IP: {ip}" + (f"  (ours: {direct})" if direct else ""))
if direct and ip == direct:
    print("  FAILED: the proxy exits on our own address — it changes nothing.")
    sys.exit(1)

# 3. The question that actually matters: does YouTube serve captions through it?
try:
    t = YouTubeTranscriptApi(proxy_config=cfg).fetch(os.environ["PROBE_VIDEO"])
    print(f"  transcript fetched through the proxy: {len(t.snippets)} segments")
except Exception as e:
    print(f"  FAILED: proxy works, but YouTube still refused — {type(e).__name__}")
    print("  If this says IpBlocked, the package is probably datacenter, not Residential.")
    sys.exit(1)
PY
then
  echo
  echo "Verification failed. Nothing was stored — fix it and re-run." >&2
  exit 1
fi

# Store only after it is proven. .env is gitignored (verified in .gitignore).
touch .env
chmod 600 .env
set_env() {
  local key="$1" val="$2"
  if grep -q "^${key}=" .env 2>/dev/null; then
    # | as delimiter: these values can contain / and : and @
    sed -i "s|^${key}=.*|${key}=${val}|" .env
  else
    printf '%s=%s\n' "$key" "$val" >> .env
  fi
}

grep -q '^# YouTube egress proxy' .env 2>/dev/null || \
  printf '\n# YouTube egress proxy — set by scripts/set-youtube-proxy.sh\n' >> .env
set_env WEBSHARE_PROXY_USERNAME "$WS_USER"
set_env WEBSHARE_PROXY_PASSWORD "$WS_PASS"
set_env WEBSHARE_PROXY_LOCATIONS "$LOCATIONS"
# transcript-only: captions are the blocked, tiny traffic. Metadata pages are
# megabytes each and are not blocked, so tunnelling them just inflates a
# per-gigabyte bill. Change to 'all' only if metadata starts getting blocked.
set_env YOUTUBE_PROXY_SCOPE "transcript"
unset WS_PASS

echo
echo "Stored in .env (gitignored, mode 600). Restarting the transcript service..."
docker compose up -d transcript-service >/dev/null
sleep 12
curl -s --max-time 15 "http://10.0.0.33:5025/health" | python3 -m json.tool 2>/dev/null || true

# The channel run lives inside the container, so the restart just killed it.
# Relaunching here is the difference between "configured" and "actually working".
echo
read -r -p "Relaunch the Pastor Chris Durkin ingest now? [Y/n] " RELAUNCH
if [ "${RELAUNCH:-Y}" != "n" ] && [ "${RELAUNCH:-Y}" != "N" ]; then
  docker cp scripts/priority_ingest_channel.py "$CONTAINER":/app/priority_ingest_channel.py >/dev/null
  docker exec -d "$CONTAINER" sh -c 'python3 /app/priority_ingest_channel.py \
    --handle PastorChrisDurkin --name "Pastor Chris Durkin" --domain faith \
    --delay 5 --deadline-minutes 660 \
    >> /data/state/priority_ingest_pastorchrisdurkin.log 2>&1'
  echo "Launched. Watch it with:"
  echo "  docker exec $CONTAINER tail -f /data/state/priority_ingest_pastorchrisdurkin.log"
fi
