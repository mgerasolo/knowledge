#!/usr/bin/env bash
# Backfill the livestream archives of every channel that publishes to /streams,
# one channel at a time, slowest where it matters least.
#
# Run detached inside the transcript-service container:
#   docker cp scripts/ingest_livestream_queue.sh knowledge-transcript-service:/app/
#   docker exec -d knowledge-transcript-service sh /app/ingest_livestream_queue.sh
#
# THIS IS STAGE 1: newest-first, capped per channel. Deep archives come later
# as their own deliberate runs.
#
# Why capped: Scott Adams livestreamed daily for years — on the order of 3,000
# hour-long episodes. Uncapped, one channel would monopolise the queue for days
# and every other channel would wait behind it. Newest-N-first gets recent
# material from ALL sixteen channels within a day, which is worth far more than
# one exhaustive archive.
#
# Order is deliberate and was set by Matt:
#   1. CNCC (Colts Neck Community Church — the Pastor Chris Durkin channel).
#      Full archive, all tabs, NO cap. It is the original request and only ~600
#      items. This is the run already in flight; re-entering it here is free
#      because anything already fetched is skipped.
#   2. Myron Golden, both channels. Streams only, generous cap — priority
#      content. Their /videos back catalogue is already covered by standing
#      discovery, so pulling it again would be a scope expansion nobody asked for.
#   3. The remaining 13, streams only, tighter cap and four times the spacing.
#      No deadline on these, and the whole point is to not look like a scraper.
#
# Safe to re-run. Every channel skips what is already held, so an interrupted
# queue picks up where it stopped rather than starting over. Only one queue may
# run at a time — a second invocation refuses and exits rather than doubling the
# request rate arriving at YouTube.

set -u

SCRIPT=/app/priority_ingest_channel.py
LOGDIR=/data/state
QUEUE_LOG="$LOGDIR/livestream_queue.log"
LOCK="$LOGDIR/.livestream_queue.lock"

# Seconds between videos. Priority channels move at the pace we have already
# been running safely all night; the tail is deliberately four times slower.
PRIORITY_DELAY="${PRIORITY_DELAY:-8}"
TAIL_DELAY="${TAIL_DELAY:-32}"
# Quiet gap between channels, so the traffic arrives in separated bursts rather
# than as one unbroken multi-day stream of requests.
BETWEEN_CHANNELS="${BETWEEN_CHANNELS:-900}"

# Stage-1 caps: newest N unheld items per channel. 0 means no cap.
# Raise these (or run a single channel by hand) for a stage-2 deep archive.
MYRON_LIMIT="${MYRON_LIMIT:-150}"
TAIL_LIMIT="${TAIL_LIMIT:-100}"

say() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$QUEUE_LOG"; }

# ── One queue at a time ──────────────────────────────────────────────
# Two queues were once started within minutes of each other, and nothing
# stopped them: both ran the same channel, doubling the request rate arriving
# at YouTube from a single address, which is precisely the thing this whole
# script is paced to avoid. It very nearly went unnoticed, because both wrote
# to the same log and the interleaved output still looked like one healthy run.
#
# mkdir is the lock because it is atomic — exactly one caller can create a
# directory that does not yet exist, and the loser gets a non-zero exit rather
# than a race. The container has neither flock nor pkill, so the usual tools
# are not available. The pid is written inside purely so a human can tell a
# live holder from a corpse.
#
# The trap covers a normal exit and a caught signal, but it cannot cover a
# kill -9 or a container restart, so those leave the directory behind. Confirm
# nothing is actually running before clearing a lock you believe is stale —
# /proc is the only process list here, since there is no ps:
#   docker exec knowledge-transcript-service sh -c \
#     'grep -l ingest_livestream /proc/[0-9]*/cmdline 2>/dev/null'
#   docker exec knowledge-transcript-service rm -rf /data/state/.livestream_queue.lock
if ! mkdir "$LOCK" 2>/dev/null; then
  say "REFUSING TO START — another queue already holds the lock (pid $(cat "$LOCK/pid" 2>/dev/null || echo unknown)). Nothing was launched."
  exit 1
fi
echo "$$" > "$LOCK/pid"
# Only reached if WE took the lock, so this can never release someone else's.
trap 'rm -rf "$LOCK"' EXIT INT TERM

run_channel() {
  handle="$1"; name="$2"; domain="$3"; tabs="$4"; delay="$5"; limit="${6:-0}"
  say "START $handle (tabs=$tabs, ~${delay}s between videos, cap=${limit:-none})"
  python3 "$SCRIPT" \
    --handle "$handle" --name "$name" --domain "$domain" \
    --tabs "$tabs" --delay "$delay" --limit "$limit" \
    >> "$LOGDIR/priority_ingest_$(echo "$handle" | tr '[:upper:]' '[:lower:]').log" 2>&1
  say "DONE  $handle (exit $?)"
}

say "=== livestream backfill queue starting ==="

# ── 1. CNCC first ────────────────────────────────────────────────────
run_channel PastorChrisDurkin "Pastor Chris Durkin" faith "videos,streams" "$PRIORITY_DELAY"
sleep "$BETWEEN_CHANNELS"

# ── 2. Myron next ────────────────────────────────────────────────────
run_channel MyronGolden "Myron Golden" business "streams" "$PRIORITY_DELAY" "$MYRON_LIMIT"
sleep "$BETWEEN_CHANNELS"
run_channel BibleStudyWithMyronGolden "Bible Study with Myron Golden" faith "streams" "$PRIORITY_DELAY" "$MYRON_LIMIT"
sleep "$BETWEEN_CHANNELS"

# ── 3. Everyone else, generously paced ───────────────────────────────
say "--- stage-1 tail: newest ${TAIL_LIMIT} per channel, ~${TAIL_DELAY}s apart ---"
run_channel RealCoffeewithScottAdams "Scott Adams"            political "streams" "$TAIL_DELAY" "$TAIL_LIMIT"; sleep "$BETWEEN_CHANNELS"
run_channel VALUETAINMENT            "Valuetainment"          political "streams" "$TAIL_DELAY" "$TAIL_LIMIT"; sleep "$BETWEEN_CHANNELS"
run_channel RubinReport              "The Rubin Report"       political "streams" "$TAIL_DELAY" "$TAIL_LIMIT"; sleep "$BETWEEN_CHANNELS"
run_channel melrobbins               "Mel Robbins"            mindset   "streams" "$TAIL_DELAY" "$TAIL_LIMIT"; sleep "$BETWEEN_CHANNELS"
run_channel ultimatehumanpodcast     "Ultimate Human Podcast" health    "streams" "$TAIL_DELAY" "$TAIL_LIMIT"; sleep "$BETWEEN_CHANNELS"
run_channel joerogan                 "Joe Rogan"              general   "streams" "$TAIL_DELAY" "$TAIL_LIMIT"; sleep "$BETWEEN_CHANNELS"
run_channel NetworkChuck             "NetworkChuck"           ai        "streams" "$TAIL_DELAY" "$TAIL_LIMIT"; sleep "$BETWEEN_CHANNELS"
run_channel AZisk                    "AZisk"                  ai        "streams" "$TAIL_DELAY" "$TAIL_LIMIT"; sleep "$BETWEEN_CHANNELS"
run_channel replit                   "Replit"                 ai        "streams" "$TAIL_DELAY" "$TAIL_LIMIT"; sleep "$BETWEEN_CHANNELS"
run_channel AlexFinnOfficial         "Alex Finn"              ai        "streams" "$TAIL_DELAY" "$TAIL_LIMIT"; sleep "$BETWEEN_CHANNELS"
run_channel NickShirley              "Nick Shirley"           political "streams" "$TAIL_DELAY" "$TAIL_LIMIT"; sleep "$BETWEEN_CHANNELS"
run_channel RussellBrand             "Russell Brand"          political "streams" "$TAIL_DELAY" "$TAIL_LIMIT"; sleep "$BETWEEN_CHANNELS"
run_channel TheOfficialCartierFamily "The Cartier Family"     political "streams" "$TAIL_DELAY" "$TAIL_LIMIT"

say "=== stage 1 finished — deep archives remain, as their own runs ==="
