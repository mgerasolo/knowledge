#!/usr/bin/env bash
# Store the YouTube proxy credential and prove it works, without the value ever
# passing through a chat transcript, a shell history entry, or a command line.
#
#   bash scripts/set-youtube-proxy.sh
#
# Prompts for the proxy username and password, writes YOUTUBE_PROXY_URL into
# this repo's gitignored .env (which docker compose reads), restarts the
# transcript service, and then verifies by fetching one real transcript through
# the proxy. It reports the proxy's exit IP so you can confirm the traffic is
# actually leaving somewhere other than here.
#
# Nothing is stored until the verification passes.

set -euo pipefail

cd "$(dirname "$0")/.."

HOST_DEFAULT="p.webshare.io"
PORT_DEFAULT="80"
# Any video with English captions; used only as a liveness probe.
PROBE_VIDEO="${PROBE_VIDEO:-7x0SeJ2s2ps}"

read -r -p "Proxy host [${HOST_DEFAULT}]: " HOST
HOST="${HOST:-$HOST_DEFAULT}"
read -r -p "Proxy port [${PORT_DEFAULT}]: " PORT
PORT="${PORT:-$PORT_DEFAULT}"
read -r -p "Proxy username: " USER_
# Silent, but confirm something landed — a hidden prompt with no feedback is
# how a mistyped or empty paste gets stored and discovered days later.
read -r -s -p "Proxy password (hidden): " PASS_
echo
echo "  captured: ${#PASS_} characters, ending '${PASS_: -2}'"

if [ -z "$USER_" ] || [ -z "$PASS_" ]; then
  echo "ERROR: username and password are both required. Nothing stored." >&2
  exit 1
fi

URL="http://${USER_}:${PASS_}@${HOST}:${PORT}"

echo
echo "Verifying through the proxy before storing anything..."
if ! docker exec -e PROBE_URL="$URL" -e PROBE_VIDEO="$PROBE_VIDEO" \
      knowledge-transcript-service python3 - <<'PY'
import os, sys
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
import requests

url = os.environ["PROBE_URL"]
proxies = {"http": url, "https": url}

try:
    ip = requests.get("https://api.ipify.org", proxies=proxies, timeout=30).text.strip()
    print(f"  proxy exit IP: {ip}")
except Exception as e:
    print(f"  FAILED: cannot reach the internet through the proxy — {e}")
    sys.exit(1)

try:
    t = YouTubeTranscriptApi(
        proxy_config=GenericProxyConfig(http_url=url, https_url=url)
    ).fetch(os.environ["PROBE_VIDEO"])
    print(f"  transcript fetched through the proxy: {len(t.snippets)} segments")
except Exception as e:
    print(f"  FAILED: proxy works but YouTube still refused — {type(e).__name__}")
    sys.exit(1)
PY
then
  echo
  echo "Verification failed. Nothing was stored — fix the credential and re-run." >&2
  exit 1
fi

# Store only after it is proven. .env is gitignored (checked in .gitignore).
touch .env
if grep -q '^YOUTUBE_PROXY_URL=' .env 2>/dev/null; then
  # Delimiter is | because the URL contains / and : and possibly @.
  sed -i "s|^YOUTUBE_PROXY_URL=.*|YOUTUBE_PROXY_URL=${URL}|" .env
else
  printf '\n# YouTube egress proxy — see scripts/set-youtube-proxy.sh\nYOUTUBE_PROXY_URL=%s\n' "$URL" >> .env
fi
chmod 600 .env
unset PASS_ URL

echo
echo "Stored in .env (gitignored, mode 600). Restarting the transcript service..."
docker compose up -d transcript-service >/dev/null
sleep 10
docker exec knowledge-transcript-service python3 -c "
from config import Config
print('service sees a proxy:', bool(Config.YOUTUBE_PROXY_URL))
"
echo
echo "Done. Re-launch a stalled channel run with:"
echo "  docker exec -d knowledge-transcript-service sh -c 'python3 /app/priority_ingest_channel.py --handle PastorChrisDurkin --name \"Pastor Chris Durkin\" --domain faith --delay 5 --deadline-minutes 660 >> /data/state/priority_ingest_pastorchrisdurkin.log 2>&1'"
