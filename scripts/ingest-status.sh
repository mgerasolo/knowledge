#!/usr/bin/env bash
# Where the whole transcript-ingestion effort stands, on one screen.
#
#   bash scripts/ingest-status.sh
#
# Written because answering "how is the backfill going?" otherwise means tailing
# a log per channel and reading JSON by eye, and the interesting facts — which
# channel is live, what it has actually saved, whether YouTube is pushing back —
# are scattered across all of them.
#
# STRICTLY READ-ONLY. It reads two HTTP endpoints and some log files, and calls
# nothing at YouTube. Safe to run on a loop and safe to run while a queue is
# mid-flight; it will not start, stop, restart or touch anything.
#
# The channel list is read from ingest_livestream_queue.sh rather than repeated
# here, so adding a channel there is enough — this stays correct on its own.

set -uo pipefail

CONTAINER="${CONTAINER:-knowledge-transcript-service}"
HEALTH_URL="${HEALTH_URL:-http://10.0.0.33:5025/health}"
CORPUS_URL="${CORPUS_URL:-https://knowledge.nextlevelfoundry.com/enroll/api/v1/status}"
QUEUE_SCRIPT="${QUEUE_SCRIPT:-$(dirname "$0")/ingest_livestream_queue.sh}"

hr() { printf '%s\n' "----------------------------------------------------------------------"; }

# ── Channel roster: handle + display name, in queue order ────────────
HANDLES=""
declare -A CHANNEL_NAME
if [ -r "$QUEUE_SCRIPT" ]; then
  while IFS='|' read -r h n; do
    [ -n "$h" ] || continue
    HANDLES="$HANDLES $h"
    CHANNEL_NAME["$h"]="$n"
  done < <(sed -n 's/^run_channel[[:space:]]\{1,\}\([A-Za-z0-9_-]\{1,\}\)[[:space:]]\{1,\}"\([^"]*\)".*/\1|\2/p' "$QUEUE_SCRIPT")
fi
if [ -z "$HANDLES" ]; then
  echo "WARNING: no channels found in $QUEUE_SCRIPT — the per-channel table will be empty." >&2
fi

# ── One trip into the container for every per-channel fact ───────────
# Sixteen separate `docker exec` calls would be sixteen round trips; this is one.
REMOTE=$(docker exec -e HANDLES="$HANDLES" -i "$CONTAINER" sh -s <<'REMOTE_SH' 2>/dev/null
[ -d /data/state/.livestream_queue.lock ] && echo "LOCK|held" || echo "LOCK|free"
for p in /proc/[0-9]*/cmdline; do
  c=$(tr '\0' ' ' < "$p" 2>/dev/null) || continue
  case "$c" in
    *priority_ingest_channel.py*) echo "PROC|$c" ;;
    *ingest_livestream_queue*)    echo "QUEUE|running" ;;
  esac
done
for h in $HANDLES; do
  f="/data/state/priority_ingest_$(echo "$h" | tr '[:upper:]' '[:lower:]').log"
  if [ ! -f "$f" ]; then echo "CH|$h|nolog|0|0|0|0|0|0|0|0|0"; continue; fi
  # Counters reset at every run header, so what survives describes the LAST run.
  # The log is appended to across runs; without the reset these are lifetime totals.
  awk -v h="$h" '
    /=== Priority ingest:/ { saved=0; none=0; live=0; cur=0; tot=0; fin=0 }
    match($0, /· [0-9]+ to fetch/) { s=substr($0,RSTART,RLENGTH); gsub(/[^0-9]/,"",s); if(tot==0) tot=s+0 }
    $2 ~ /^\[[0-9]+\/[0-9]+\]$/ { split(substr($2,2,length($2)-2), a, "/"); cur=a[1]+0; tot=a[2]+0 }
    / segments -> /            { saved++ }
    /no transcript available/  { none++ }
    /still live \(/            { live++ }
    /=== DONE in /             { fin=1 }
    END { printf "CH|%s|log|%d|%d|%d|%d|%d|%d", h, saved, none, live, cur, tot, fin }
  ' "$f"
  # Trouble is scoped to the last 200 lines: recent, not historical.
  tail -200 "$f" | awk '
    /BLOCKED/     { b++ }
    /NOT INDEXED/ { n++ }
    /ERROR/       { e++ }
    END { printf "|%d|%d|%d\n", b, n, e }'
done
REMOTE_SH
)
DOCKER_OK=$?

echo
echo "KNOWLEDGESTACK INGESTION  ·  $(date '+%a %d %b %H:%M %Z')"
hr

# ── Service + proxy ──────────────────────────────────────────────────
# The JSON goes in through the environment, not through a quoted -c string:
# shell-escaping quotes inside an f-string is a Python syntax error, and it
# fails as "UNREACHABLE", which reads like an outage rather than a typo.
HEALTH_JSON=$(curl -s --max-time 15 "$HEALTH_URL" 2>/dev/null)
HEALTH_JSON="$HEALTH_JSON" python3 - <<'PY'
import json, os
raw = os.environ.get("HEALTH_JSON", "")
try:
    d = json.loads(raw)
except Exception:
    print("SERVICE   UNREACHABLE — no answer from the transcript service")
    raise SystemExit
b, p = d.get("backfill", {}), d.get("proxy", {})
act, age = "idle", b.get("seconds_since_heartbeat")
if b.get("alive"):
    act = "STALLED" if b.get("stalled") else "working"
    if isinstance(age, (int, float)):
        act += f", last activity {int(age)}s ago"
print(f'SERVICE   {str(d.get("status","?")).upper()} · fetcher {act}')
mode = (p.get("mode") or "none").lower()
if mode in ("none", "off", "direct", ""):
    print("PROXY     OFF — requests leave from our own address")
else:
    scope = {"transcript": "captions only", "all": "all traffic"}.get(p.get("scope"), p.get("scope") or "?")
    print(f'PROXY     ON via {mode} · {p.get("locations") or "any"} exits · {scope}')
PY

# ── What is running right now ────────────────────────────────────────
if [ $DOCKER_OK -ne 0 ] || [ -z "$REMOTE" ]; then
  echo "QUEUE     CANNOT READ — no answer from container '$CONTAINER'"
else
  RUN_HANDLE=$(printf '%s\n' "$REMOTE" | sed -n 's/.*--handle \([A-Za-z0-9_-]*\).*/\1/p' | head -1)
  QUEUE_UP=$(printf '%s\n' "$REMOTE" | grep -c '^QUEUE|running')
  LOCK=$(printf '%s\n' "$REMOTE" | sed -n 's/^LOCK|//p' | head -1)
  if [ -n "$RUN_HANDLE" ]; then
    LINE=$(printf '%s\n' "$REMOTE" | grep "^CH|$RUN_HANDLE|")
    CUR=$(echo "$LINE" | cut -d'|' -f7); TOT=$(echo "$LINE" | cut -d'|' -f8)
    PCT=""; [ "${TOT:-0}" -gt 0 ] 2>/dev/null && PCT=" ($(( CUR * 100 / TOT ))%)"
    echo "RUNNING   ${CHANNEL_NAME[$RUN_HANDLE]:-$RUN_HANDLE} — item ${CUR:-?} of ${TOT:-?}${PCT}"
  else
    echo "RUNNING   nothing is fetching right now"
  fi
  [ "$QUEUE_UP" -eq 0 ] && [ -n "$RUN_HANDLE" ] && \
    echo "          (single channel only — the queue driver is not running)"
  [ "$LOCK" = "free" ] && [ -n "$RUN_HANDLE" ] && \
    echo "          (no queue lock held — a second queue could start on top of this)"
fi

# ── Per-channel scoreboard ───────────────────────────────────────────
if [ -n "$REMOTE" ]; then
  hr
  printf '%-26s %6s %6s %6s  %s\n' "CHANNEL" "SAVED" "NOCAP" "LIVE" "PROGRESS"
  PENDING=""; NPEND=0
  for h in $HANDLES; do
    L=$(printf '%s\n' "$REMOTE" | grep "^CH|$h|")
    [ -n "$L" ] || continue
    if [ "$(echo "$L" | cut -d'|' -f3)" = "nolog" ]; then
      NPEND=$((NPEND+1))
      [ $NPEND -le 3 ] && PENDING="$PENDING, ${CHANNEL_NAME[$h]:-$h}"
      continue
    fi
    SAVED=$(echo "$L" | cut -d'|' -f4); NOCAP=$(echo "$L" | cut -d'|' -f5)
    LIVE=$(echo "$L" | cut -d'|' -f6);  CUR=$(echo "$L" | cut -d'|' -f7)
    TOT=$(echo "$L" | cut -d'|' -f8);   FIN=$(echo "$L" | cut -d'|' -f9)
    if [ "$FIN" = "1" ]; then P="finished"
    elif [ "$h" = "${RUN_HANDLE:-}" ]; then P="$CUR/$TOT running"
    else P="$CUR/$TOT stopped"; fi
    printf '%-26s %6s %6s %6s  %s\n' "${CHANNEL_NAME[$h]:-$h}" "$SAVED" "$NOCAP" "$LIVE" "$P"
  done
  if [ $NPEND -gt 0 ]; then
    MORE=""; [ $NPEND -gt 3 ] && MORE=" +$((NPEND-3)) more"
    echo "not started yet ($NPEND):${PENDING#,}$MORE"
  fi
  echo "SAVED = transcripts written · NOCAP = no captions published · LIVE = still broadcasting, deferred"
fi

# ── Corpus totals ────────────────────────────────────────────────────
hr
CORPUS_JSON=$(curl -s --max-time 25 "$CORPUS_URL" 2>/dev/null)
CORPUS_JSON="$CORPUS_JSON" python3 - <<'PY'
import json, os
raw = os.environ.get("CORPUS_JSON", "")
try:
    d = json.loads(raw)
except Exception:
    print("CORPUS    UNREACHABLE — no answer from the search index")
    raise SystemExit
c = d.get("components", {})
s, f = c.get("surrealdb", {}), c.get("transcript_files", {})
print(f'CORPUS    {s.get("videos",0):,} videos · {s.get("segments",0):,} passages searchable · '
      f'{f.get("files",0):,} files on disk')
print(f'          newest arrived {s.get("hours_since_newest",0):.1f}h ago · '
      f'overall {str(d.get("status","?")).upper()}')
probs = d.get("problems") or []
if probs:
    print("          PROBLEMS: " + "; ".join(str(x) for x in probs))
PY

# ── Trouble ──────────────────────────────────────────────────────────
if [ -n "$REMOTE" ]; then
  TB=0; TN=0; TE=0; WHO=""
  for h in $HANDLES; do
    L=$(printf '%s\n' "$REMOTE" | grep "^CH|$h|"); [ -n "$L" ] || continue
    b=$(echo "$L" | cut -d'|' -f10); n=$(echo "$L" | cut -d'|' -f11); e=$(echo "$L" | cut -d'|' -f12)
    b=${b:-0}; n=${n:-0}; e=${e:-0}
    if [ $((b+n+e)) -gt 0 ]; then
      TB=$((TB+b)); TN=$((TN+n)); TE=$((TE+e)); WHO="$WHO ${CHANNEL_NAME[$h]:-$h}($((b+n+e)))"
    fi
  done
  if [ $((TB+TN+TE)) -eq 0 ]; then
    echo "TROUBLE   none in the recent history of any channel"
  else
    echo "TROUBLE   $TB blocked by YouTube · $TN failed to index · $TE errors (recent lines only)"
    echo "          affecting:$WHO"
  fi
fi
hr
