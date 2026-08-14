#!/usr/bin/env bash
# Daily Codex triage of NEW MISTAKES.md / GAPS.md entries (KnowledgeStack beta).
#
# Design (Matt directive 2026-08-14):
#   - One-time mistakes are NOT worth burning tokens on. Only repeating patterns
#     and cheaply-actionable items deserve action.
#   - Codex (independent OpenAI model, zero Claude tokens, zero session context)
#     reviews once a day, and ONLY the entries added since the last review.
#   - Actionable verdicts become GitHub issues (normal work queue). Nothing pings
#     Matt unless an issue was actually filed, and then only at default priority.
#
# State: .claude/state/mistakes-gaps-review.watermark holds per-file line counts
# from the last run; the diff between watermark and now is "new since last review".
set -euo pipefail
cd "$(dirname "$0")/../.."   # repo root

STATE_DIR=".claude/state"; REVIEW_DIR=".claude/reviews"
WATERMARK="$STATE_DIR/mistakes-gaps-review.watermark"
mkdir -p "$STATE_DIR" "$REVIEW_DIR"
TODAY=$(date +%F)
OUT="$REVIEW_DIR/$TODAY-codex-triage.md"

# --- collect new lines since watermark -------------------------------------
declare -A prev
if [[ -f "$WATERMARK" ]]; then
  while read -r f n; do prev[$f]=$n; done < "$WATERMARK"
fi
NEW_CONTENT=""
for f in .claude/MISTAKES.md .claude/GAPS.md; do
  [[ -f "$f" ]] || continue
  total=$(wc -l < "$f")
  from=${prev[$f]:-0}
  if (( total > from )); then
    NEW_CONTENT+=$'\n'"### New lines in $f (lines $((from+1))-$total):"$'\n'
    NEW_CONTENT+=$(sed -n "$((from+1)),${total}p" "$f")$'\n'
  fi
done

if [[ -z "$NEW_CONTENT" ]]; then
  echo "$TODAY: no new entries since last review — no Codex call, zero cost." > "$OUT"
  { for f in .claude/MISTAKES.md .claude/GAPS.md; do [[ -f "$f" ]] && echo "$f $(wc -l < "$f")"; done; } > "$WATERMARK"
  exit 0
fi

# --- Codex triage (full files as context, NEW lines as the subject) ---------
PROMPT="You are an independent reviewer triaging an AI coding agent's self-reported
mistakes and gaps for the KnowledgeStack project. Read .claude/MISTAKES.md and
.claude/GAPS.md for full history. The NEW entries since the last daily review are:

$NEW_CONTENT

For EACH new entry, output a verdict line:
- ONE-TIME: plausibly a one-off; no action justified; say why in <=15 words.
- PATTERN: it repeats an earlier entry's category or root-cause family — name the
  matching earlier entries, and propose the cheapest structural fix (a hook, a
  lint, a config change), sized in one line.
- ACTIONABLE-NOW: a concrete, cheap, well-scoped fix exists regardless of repetition
  (e.g. a one-line config, a missing check). Describe the fix in <=3 lines with
  file paths if identifiable from the entry.

Then a final section 'FILE ISSUES' listing zero or more issues worth creating,
each as: TITLE: <title> | LABELS: type:bug|type:enhancement,priority:high|medium|low | BODY: <5-line body citing the entry>.
Only include an issue if the fix is genuinely worth an agent's time — bias strongly
toward filing NOTHING for one-time items. Be terse."

CODEX_OUT=$(codex exec --skip-git-repo-check "$PROMPT" 2>/dev/null) || { echo "$TODAY: codex exec failed" > "$OUT"; exit 1; }
{ echo "# Codex daily triage — $TODAY"; echo; echo "$CODEX_OUT"; } > "$OUT"

# --- file issues Codex proposed ---------------------------------------------
FILED=0
while IFS= read -r line; do
  title=$(sed -E 's/^TITLE:\s*//; s/\s*\|\s*LABELS:.*$//' <<< "$line")
  labels=$(grep -oP 'LABELS:\s*\K[^|]+' <<< "$line" | tr -d ' ')
  body=$(grep -oP 'BODY:\s*\K.*' <<< "$line")
  [[ -n "$title" && -n "$body" ]] || continue
  gh issue create --title "$title" --body "$body

_Filed automatically by the daily Codex mistakes/gaps triage ($TODAY). Verdict log: .claude/reviews/$TODAY-codex-triage.md_" ${labels:+--label "$labels"} >/dev/null 2>&1 \
    && FILED=$((FILED+1)) || true
done < <(grep -E '^TITLE:' "$OUT" || true)

# --- advance watermark, notify ONLY if something was filed -------------------
{ for f in .claude/MISTAKES.md .claude/GAPS.md; do [[ -f "$f" ]] && echo "$f $(wc -l < "$f")"; done; } > "$WATERMARK"
if (( FILED > 0 )); then
  curl -sS -m 15 https://ntfy.nextlevelfoundry.com/matt-alerts \
    -H "Title: KnowledgeStack triage: $FILED issue(s) filed from mistakes/gaps" \
    -H "Tags: mag" \
    -d "Codex's daily review of new MISTAKES/GAPS entries judged $FILED item(s) actionable and filed GitHub issue(s). One-time items were skipped by design. Verdicts: .claude/reviews/$TODAY-codex-triage.md" >/dev/null || true
fi
