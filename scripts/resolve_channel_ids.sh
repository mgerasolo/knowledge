#!/bin/bash
# Resolve YouTube channel IDs from handles using yt-dlp
# Usage: ./resolve_channel_ids.sh

set -e

# Channels to resolve (handles without IDs)
HANDLES=(
    "AI.Tooltip"
    "AILABS-393"
    "AZisk"
    "AfterSkool"
    "AlexFinnOfficial"
    "BMadCode"
    "BartSlodyczka"
    "BibleStudyWithMyronGolden"
    "ChampionsMentality365"
    "Charismaoncommand"
    "ChrisWillx"
    "DavidOndrej"
    "GregIsenberg"
    "JREClips"
    "JimRohnMotivationVideos"
    "JordanBPeterson"
    "Mark_Kashef"
    "MyFirstMillionPod"
    "NapoleonHill_Wisdom"
    "NetworkChuck"
    "NickShirley"
    "PodcastBigDeal"
    "RealCoffeewithScottAdams"
    "RubinReport"
    "RussellBrand"
    "ShawnRyanShow"
    "TheIcedCoffeeHour"
    "TheOfficialCartierFamily"
    "Thebasedconservative"
    "TuckerCarlson"
    "VALUETAINMENT"
    "allin"
    "askvinh"
    "danmartell"
    "futurepedia_io"
    "joerogan"
    "johnnynelofficial"
    "melrobbins"
    "mindsetmentorpodcast"
    "mreflow"
    "pradipjamnadasmd"
    "raroque"
    "replit"
    "sabrina_ramonov"
    "ultimatehumanpodcast"
    "unsupervised-learning"
)

OUTPUT_FILE="/tmp/channel_ids.sql"
echo "-- Channel ID updates" > "$OUTPUT_FILE"

resolve_channel() {
    local handle="$1"
    local url="https://www.youtube.com/@${handle}"
    local channel_id

    channel_id=$(yt-dlp --print channel_id "$url" 2>/dev/null | head -1)

    if [[ -n "$channel_id" && "$channel_id" =~ ^UC ]]; then
        echo "UPDATE channels SET youtube_channel_id = '$channel_id' WHERE youtube_handle = '$handle';" >> "$OUTPUT_FILE"
        echo "$handle -> $channel_id"
    else
        echo "$handle -> FAILED" >&2
    fi
}

export -f resolve_channel
export OUTPUT_FILE

echo "Resolving ${#HANDLES[@]} channel IDs..."

# Process in parallel (8 at a time)
printf '%s\n' "${HANDLES[@]}" | xargs -P 8 -I {} bash -c 'resolve_channel "$@"' _ {}

echo ""
echo "SQL file written to: $OUTPUT_FILE"
echo "To apply: cat $OUTPUT_FILE"
