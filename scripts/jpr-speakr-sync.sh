#!/bin/bash
# jpr-speakr-sync.sh  (v5 — LIVE, verified working 2026-07-13)
# Watches the iCloud "Just Press Record" folder on a Mac and uploads any NEW
# recordings to Speakr — DIRECT to Banner's LAN address (http://10.0.0.33:5000),
# bypassing the public reverse proxy (which caps uploads at ~2 MB).
#
# Runs one pass and exits; scheduled every 60s via a launchd LaunchAgent
# (com.nlf.jpr-speakr-sync.plist). Requires Full Disk Access granted to the
# interpreter (/bin/bash) so launchd can read iCloud Drive on macOS Sequoia.
#
# v5 notes:
#  - Explicit SUCCESS logging + per-run heartbeat ("scan complete: ...").
#  - Handles iCloud "dataless" files: detects via `find -flags +dataless`,
#    forces `brctl download`, WAITS until fully local, then uploads the original
#    directly (no cp — avoids the fcopyfile "Resource deadlock avoided" error).
#  - Dedups via a state file; never deletes/moves the originals; self-heals
#    across cycles (a still-downloading file is retried next run).
set -u

SPEAKR_URL="http://10.0.0.33:5000/api/v1/recordings/upload"
CFG="$HOME/.config/jpr-speakr"
TOKEN_FILE="$CFG/token"
STATE_FILE="$CFG/uploaded.log"
LOG_FILE="$CFG/watcher.log"
LOG_KEEP=1000

# JPR folder: prefer $JPR_DIR (set via the LaunchAgent env), else auto-locate.
JPR_DIR="${JPR_DIR:-}"
if [ -z "$JPR_DIR" ]; then
  JPR_DIR="$(ls -d "$HOME/Library/Mobile Documents/"iCloud~*just-press-record*/Documents 2>/dev/null | head -1)"
fi

log(){ echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG_FILE"; }
mkdir -p "$CFG"; touch "$STATE_FILE"

[ -f "$TOKEN_FILE" ] || { log "ERROR: token file missing: $TOKEN_FILE"; exit 1; }
TOKEN="$(tr -d '\r\n' < "$TOKEN_FILE")"
[ -n "$TOKEN" ] || { log "ERROR: token file empty"; exit 1; }
{ [ -n "$JPR_DIR" ] && [ -d "$JPR_DIR" ]; } || { log "ERROR: JPR folder not found ('$JPR_DIR')"; exit 1; }

found=0; new=0; uploaded=0; waiting=0; failed=0
while IFS= read -r -d '' f; do
  found=$((found+1))
  size=$(stat -f '%z' "$f" 2>/dev/null || echo 0)
  id="$(printf '%s|%s' "$f" "$size")"
  grep -qxF "$id" "$STATE_FILE" && continue
  new=$((new+1)); base="$(basename "$f")"

  # iCloud dataless? force download and wait until fully local.
  if [ -n "$(find "$f" -flags +dataless 2>/dev/null)" ]; then
    /usr/bin/brctl download "$f" 2>/dev/null || true
    t=0
    while [ $t -lt 20 ] && [ -n "$(find "$f" -flags +dataless 2>/dev/null)" ]; do
      sleep 3; t=$((t+1))
    done
  fi
  if [ -n "$(find "$f" -flags +dataless 2>/dev/null)" ]; then
    log "waiting (iCloud still downloading): $base"; waiting=$((waiting+1)); continue
  fi

  code=$(curl -sS -m 600 -o /dev/null -w '%{http_code}' \
      -X POST "$SPEAKR_URL" \
      -H "Authorization: Bearer $TOKEN" \
      -F "file=@${f}" \
      -F "notes=source:jpr stage:raw" \
      -F "language=en" 2>>"$LOG_FILE")
  case "$code" in
    202)     echo "$id" >> "$STATE_FILE"; uploaded=$((uploaded+1)); log "SUCCESS ✅ uploaded: $base ($size bytes)";;
    302|401) failed=$((failed+1)); log "AUTH FAIL $code (bad/missing token) — will retry: $base";;
    400)     echo "$id" >> "$STATE_FILE"; failed=$((failed+1)); log "SKIP 400 (Speakr rejected): $base";;
    413)     failed=$((failed+1)); log "TOO LARGE 413: $base";;
    "")      failed=$((failed+1)); log "NO RESPONSE (network to 10.0.0.33:5000?) — will retry: $base";;
    *)       failed=$((failed+1)); log "HTTP $code — will retry: $base";;
  esac
done < <(find "$JPR_DIR" -type f -iname '*.m4a' -print0 2>/dev/null)

log "scan complete: found=$found new=$new uploaded=$uploaded waiting=$waiting failed=$failed"
tail -n "$LOG_KEEP" "$LOG_FILE" > "$LOG_FILE.tmp" 2>/dev/null && mv "$LOG_FILE.tmp" "$LOG_FILE"
