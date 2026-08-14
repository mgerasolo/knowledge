"""Configuration for KnowledgeStack Transcript Service."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Transcript service configuration."""

    # Directories
    TRANSCRIPT_DIR = os.getenv('TRANSCRIPT_DIR', '/data/transcripts')
    STATE_DIR = os.getenv('STATE_DIR', '/data/state')

    # Flask
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('SERVICE_PORT', '5025'))

    # Embedding service (optional - call after fetching)
    EMBEDDING_SERVICE_URL = os.getenv(
        'EMBEDDING_SERVICE_URL', 'http://knowledge-embedding:5030'
    )

    # Outbound proxy for YouTube calls only (transcript API + yt-dlp).
    # Set when YouTube rate-limits our own address; leave empty to go direct.
    # Vendor-neutral: any http(s) proxy URL works, including a Webshare
    # rotating-residential endpoint. Format: http://user:pass@host:port
    # Deliberately NOT the standard HTTP_PROXY/HTTPS_PROXY vars, which would
    # also send our internal SurrealDB and embedding-service traffic through a
    # paid, metered, third-party hop.
    YOUTUBE_PROXY_URL = os.getenv('YOUTUBE_PROXY_URL', '').strip()

    # Webshare residential is the supported vendor path: give it the "Proxy
    # Username"/"Proxy Password" from the dashboard and the library handles the
    # rotating endpoint and per-request IP rotation itself. Takes precedence
    # over YOUTUBE_PROXY_URL when both are set.
    WEBSHARE_PROXY_USERNAME = os.getenv('WEBSHARE_PROXY_USERNAME', '').strip()
    WEBSHARE_PROXY_PASSWORD = os.getenv('WEBSHARE_PROXY_PASSWORD', '').strip()

    # Optional country filter for the rotating pool, e.g. "US" or "US,CA".
    # Closer IPs mean lower latency; empty means the whole pool.
    WEBSHARE_PROXY_LOCATIONS = os.getenv('WEBSHARE_PROXY_LOCATIONS', 'US').strip()

    # What goes through the proxy: 'transcript' (default) or 'all'.
    #
    # Residential proxies bill per gigabyte, and the two kinds of traffic here
    # are wildly different sizes: a transcript is a few tens of KB of text,
    # while each yt-dlp metadata call pulls a full watch page measured in MB.
    # Only the caption endpoint is rate-limited, so paying to tunnel the page
    # fetches would multiply the bill for no benefit. Set 'all' only if YouTube
    # starts blocking metadata calls too.
    YOUTUBE_PROXY_SCOPE = os.getenv('YOUTUBE_PROXY_SCOPE', 'transcript').strip().lower()

    # Rate limiting (backfill worker)
    MIN_DELAY_SECONDS = int(os.getenv('MIN_DELAY_SECONDS', '30'))
    MAX_DELAY_SECONDS = int(os.getenv('MAX_DELAY_SECONDS', '600'))
    BACKFILL_BATCH_SIZE = int(os.getenv('BACKFILL_BATCH_SIZE', '8'))

    # Monitored YouTube channels
    # Tiers: supreme (6mo), leader (6mo), mid (3mo), occasional (2mo)
    # Myron channels: 36mo (full archive)
    # "tabs": channels that publish livestreams need ["videos", "streams"] —
    # YouTube files livestreams under /streams, which /videos does NOT include.
    CHANNELS = [
        # ── Supreme ──────────────────────────────────────────
        {"handle": "MyronGolden", "name": "Myron Golden", "domain": "business", "tier": "supreme", "lookback_months": 36, "tabs": ["videos", "streams"]},
        {"handle": "BibleStudyWithMyronGolden", "name": "Bible Study with Myron Golden", "domain": "faith", "tier": "supreme", "lookback_months": 36, "tabs": ["videos", "streams"]},
        # Sermons are published as livestreams, which YouTube files under
        # /streams and NOT /videos — without the explicit tabs list, standing
        # discovery would see only the handful of uploaded clips and miss the
        # ~430 sermons that are the actual reason this channel is monitored.
        {"handle": "PastorChrisDurkin", "name": "Pastor Chris Durkin", "domain": "faith", "tier": "supreme", "lookback_months": 36, "tabs": ["videos", "streams"]},
        {"handle": "hubermanlab", "name": "Huberman Lab", "domain": "health", "tier": "supreme", "lookback_months": 6},
        {"handle": "ChrisWillx", "name": "Chris Williamson", "domain": "mindset", "tier": "supreme", "lookback_months": 6},
        {"handle": "TheDiaryOfACEO", "name": "The Diary of a CEO", "domain": "business", "tier": "supreme", "lookback_months": 6},
        {"handle": "RealCoffeewithScottAdams", "name": "Scott Adams", "domain": "political", "tier": "supreme", "lookback_months": 6, "tabs": ["videos", "streams"]},
        {"handle": "AILABS-393", "name": "AI Labs", "domain": "ai", "tier": "supreme", "lookback_months": 6},
        {"handle": "JREClips", "name": "JRE Clips", "domain": "general", "tier": "supreme", "lookback_months": 6},
        {"handle": "mindsetmentorpodcast", "name": "Mindset Mentor", "domain": "mindset", "tier": "supreme", "lookback_months": 6},
        # ── AI Leaders ───────────────────────────────────────
        {"handle": "mreflow", "name": "MreFlow", "domain": "ai", "tier": "leader", "lookback_months": 6},
        {"handle": "GregIsenberg", "name": "Greg Isenberg", "domain": "ai", "tier": "leader", "lookback_months": 6},
        {"handle": "unsupervised-learning", "name": "Unsupervised Learning", "domain": "ai", "tier": "leader", "lookback_months": 6},
        {"handle": "raroque", "name": "Raroque", "domain": "ai", "tier": "leader", "lookback_months": 6},
        {"handle": "replit", "name": "Replit", "domain": "ai", "tier": "leader", "lookback_months": 6, "tabs": ["videos", "streams"]},
        {"handle": "BMadCode", "name": "BMad Code", "domain": "ai", "tier": "leader", "lookback_months": 6},
        {"handle": "AndrejKarpathy", "name": "Andrej Karpathy", "domain": "ai", "tier": "leader", "lookback_months": 12},
        # ── Business Leaders ─────────────────────────────────
        {"handle": "TheIcedCoffeeHour", "name": "The Iced Coffee Hour", "domain": "business", "tier": "leader", "lookback_months": 6},
        # ── Political Leaders ────────────────────────────────
        {"handle": "VALUETAINMENT", "name": "Valuetainment", "domain": "political", "tier": "leader", "lookback_months": 6, "tabs": ["videos", "streams"]},
        # ── Mindset & Health Leaders ─────────────────────────
        {"handle": "NapoleonHill_Wisdom", "name": "Napoleon Hill Wisdom", "domain": "mindset", "tier": "leader", "lookback_months": 6},
        {"handle": "JordanBPeterson", "name": "Jordan B Peterson", "domain": "mindset", "tier": "leader", "lookback_months": 6, "tabs": ["videos", "streams"]},
        {"handle": "pradipjamnadasmd", "name": "Dr. Pradip Jamnadas", "domain": "health", "tier": "leader", "lookback_months": 6},
        {"handle": "AfterSkool", "name": "After Skool", "domain": "mindset", "tier": "leader", "lookback_months": 6},
        {"handle": "ultimatehumanpodcast", "name": "Ultimate Human Podcast", "domain": "health", "tier": "leader", "lookback_months": 6, "tabs": ["videos", "streams"]},
        {"handle": "askvinh", "name": "Ask Vinh", "domain": "mindset", "tier": "leader", "lookback_months": 6},
        {"handle": "melrobbins", "name": "Mel Robbins", "domain": "mindset", "tier": "leader", "lookback_months": 6, "tabs": ["videos", "streams"]},
        # ── General Mid-tier ─────────────────────────────────
        {"handle": "joerogan", "name": "Joe Rogan", "domain": "general", "tier": "mid", "lookback_months": 3, "tabs": ["videos", "streams"]},
        {"handle": "lexfridman", "name": "Lex Fridman", "domain": "general", "tier": "mid", "lookback_months": 3},
        # ── AI Mid-tier ──────────────────────────────────────
        {"handle": "AZisk", "name": "AZisk", "domain": "ai", "tier": "mid", "lookback_months": 3, "tabs": ["videos", "streams"]},
        {"handle": "Mark_Kashef", "name": "Mark Kashef", "domain": "ai", "tier": "mid", "lookback_months": 3},
        {"handle": "NetworkChuck", "name": "NetworkChuck", "domain": "ai", "tier": "mid", "lookback_months": 3, "tabs": ["videos", "streams"]},
        {"handle": "sabrina_ramonov", "name": "Sabrina Ramonov", "domain": "ai", "tier": "mid", "lookback_months": 3},
        # ── Business Mid-tier ────────────────────────────────
        {"handle": "allin", "name": "All-In Podcast", "domain": "business", "tier": "mid", "lookback_months": 3},
        {"handle": "PodcastBigDeal", "name": "Big Deal Podcast", "domain": "business", "tier": "mid", "lookback_months": 3},
        {"handle": "MyFirstMillionPod", "name": "My First Million", "domain": "business", "tier": "mid", "lookback_months": 3},
        # ── Political Mid-tier ───────────────────────────────
        {"handle": "RubinReport", "name": "The Rubin Report", "domain": "political", "tier": "mid", "lookback_months": 3, "tabs": ["videos", "streams"]},
        {"handle": "TuckerCarlson", "name": "Tucker Carlson", "domain": "political", "tier": "mid", "lookback_months": 3},
        {"handle": "Thebasedconservative", "name": "The Based Conservative", "domain": "political", "tier": "mid", "lookback_months": 3},
        {"handle": "ShawnRyanShow", "name": "Shawn Ryan Show", "domain": "political", "tier": "mid", "lookback_months": 3},
        {"handle": "NickShirley", "name": "Nick Shirley", "domain": "political", "tier": "mid", "lookback_months": 3, "tabs": ["videos", "streams"]},
        # ── Mindset & Health Mid-tier ────────────────────────
        {"handle": "ChampionsMentality365", "name": "Champions Mentality", "domain": "mindset", "tier": "mid", "lookback_months": 3},
        {"handle": "Charismaoncommand", "name": "Charisma on Command", "domain": "mindset", "tier": "mid", "lookback_months": 3},
        {"handle": "JimRohnMotivationVideos", "name": "Jim Rohn", "domain": "mindset", "tier": "mid", "lookback_months": 3},
        # ── AI Occasionally Helpful ──────────────────────────
        {"handle": "DavidOndrej", "name": "David Ondrej", "domain": "ai", "tier": "occasional", "lookback_months": 2},
        {"handle": "BartSlodyczka", "name": "Bart Slodyczka", "domain": "ai", "tier": "occasional", "lookback_months": 2},
        {"handle": "futurepedia_io", "name": "Futurepedia", "domain": "ai", "tier": "occasional", "lookback_months": 2},
        {"handle": "AI.Tooltip", "name": "AI Tooltip", "domain": "ai", "tier": "occasional", "lookback_months": 2},
        {"handle": "johnnynelofficial", "name": "Johnny Nel", "domain": "ai", "tier": "occasional", "lookback_months": 2},
        {"handle": "AlexFinnOfficial", "name": "Alex Finn", "domain": "ai", "tier": "occasional", "lookback_months": 2, "tabs": ["videos", "streams"]},
        # ── Business Occasionally Helpful ────────────────────
        {"handle": "danmartell", "name": "Dan Martell", "domain": "business", "tier": "occasional", "lookback_months": 2},
        # ── Political Occasionally Helpful ───────────────────
        {"handle": "RussellBrand", "name": "Russell Brand", "domain": "political", "tier": "occasional", "lookback_months": 2, "tabs": ["videos", "streams"]},
        {"handle": "TheOfficialCartierFamily", "name": "The Cartier Family", "domain": "political", "tier": "occasional", "lookback_months": 2, "tabs": ["videos", "streams"]},
    ]
