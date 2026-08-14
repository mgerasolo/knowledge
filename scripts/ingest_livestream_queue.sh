#!/usr/bin/env bash
# Backfill the livestream archives of every channel that publishes to /streams,
# one channel at a time, slowest where it matters least.
#
# Run detached inside the transcript-service container:
#   docker cp scripts/ingest_livestream_queue.sh knowledge-transcript-service:/app/
#   docker exec -d knowledge-transcript-service sh /app/ingest_livestream_queue.sh
#
# Order is deliberate and was set by Matt:
#   1. CNCC (Colts Neck Community Church — the Pastor Chris Durkin channel).
#      Full archive, all tabs. This is the run already in flight; re-entering it
#      here is free because anything already fetched is skipped.
#   2. Myron Golden, both channels. Streams only — their /videos back catalogue
#      is already covered by standing discovery.
#   3. The remaining 13, streams only, paced far more slowly. There is no
#      deadline on these, and the whole point is to not look like a scraper.
#
# Safe to re-run. Every channel skips what is already held, so an interrupted
# queue picks up where it stopped rather than starting over.

set -u

SCRIPT=/app/priority_ingest_channel.py
LOGDIR=/data/state
QUEUE_LOG="$LOGDIR/livestream_queue.log"

# Seconds between videos. Priority channels move at the pace we have already
# been running safely all night; the tail is deliberately four times slower.
PRIORITY_DELAY="${PRIORITY_DELAY:-8}"
TAIL_DELAY="${TAIL_DELAY:-32}"
# Quiet gap between channels, so the traffic arrives in separated bursts rather
# than as one unbroken multi-day stream of requests.
BETWEEN_CHANNELS="${BETWEEN_CHANNELS:-900}"

say() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$QUEUE_LOG"; }

run_channel() {
  handle="$1"; name="$2"; domain="$3"; tabs="$4"; delay="$5"
  say "START $handle (tabs=$tabs, ~${delay}s between videos)"
  python3 "$SCRIPT" \
    --handle "$handle" --name "$name" --domain "$domain" \
    --tabs "$tabs" --delay "$delay" \
    >> "$LOGDIR/priority_ingest_$(echo "$handle" | tr '[:upper:]' '[:lower:]').log" 2>&1
  say "DONE  $handle (exit $?)"
}

say "=== livestream backfill queue starting ==="

# ── 1. CNCC first ────────────────────────────────────────────────────
run_channel PastorChrisDurkin "Pastor Chris Durkin" faith "videos,streams" "$PRIORITY_DELAY"
sleep "$BETWEEN_CHANNELS"

# ── 2. Myron next ────────────────────────────────────────────────────
run_channel MyronGolden "Myron Golden" business "streams" "$PRIORITY_DELAY"
sleep "$BETWEEN_CHANNELS"
run_channel BibleStudyWithMyronGolden "Bible Study with Myron Golden" faith "streams" "$PRIORITY_DELAY"
sleep "$BETWEEN_CHANNELS"

# ── 3. Everyone else, generously paced ───────────────────────────────
say "--- switching to the slow tail (~${TAIL_DELAY}s between videos) ---"
run_channel RealCoffeewithScottAdams "Scott Adams"            political "streams" "$TAIL_DELAY"; sleep "$BETWEEN_CHANNELS"
run_channel VALUETAINMENT            "Valuetainment"          political "streams" "$TAIL_DELAY"; sleep "$BETWEEN_CHANNELS"
run_channel RubinReport              "The Rubin Report"       political "streams" "$TAIL_DELAY"; sleep "$BETWEEN_CHANNELS"
run_channel melrobbins               "Mel Robbins"            mindset   "streams" "$TAIL_DELAY"; sleep "$BETWEEN_CHANNELS"
run_channel ultimatehumanpodcast     "Ultimate Human Podcast" health    "streams" "$TAIL_DELAY"; sleep "$BETWEEN_CHANNELS"
run_channel joerogan                 "Joe Rogan"              general   "streams" "$TAIL_DELAY"; sleep "$BETWEEN_CHANNELS"
run_channel NetworkChuck             "NetworkChuck"           ai        "streams" "$TAIL_DELAY"; sleep "$BETWEEN_CHANNELS"
run_channel AZisk                    "AZisk"                  ai        "streams" "$TAIL_DELAY"; sleep "$BETWEEN_CHANNELS"
run_channel replit                   "Replit"                 ai        "streams" "$TAIL_DELAY"; sleep "$BETWEEN_CHANNELS"
run_channel AlexFinnOfficial         "Alex Finn"              ai        "streams" "$TAIL_DELAY"; sleep "$BETWEEN_CHANNELS"
run_channel NickShirley              "Nick Shirley"           political "streams" "$TAIL_DELAY"; sleep "$BETWEEN_CHANNELS"
run_channel RussellBrand             "Russell Brand"          political "streams" "$TAIL_DELAY"; sleep "$BETWEEN_CHANNELS"
run_channel TheOfficialCartierFamily "The Cartier Family"     political "streams" "$TAIL_DELAY"

say "=== livestream backfill queue finished ==="
