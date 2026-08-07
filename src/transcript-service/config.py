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

    # Rate limiting (backfill worker)
    MIN_DELAY_SECONDS = int(os.getenv('MIN_DELAY_SECONDS', '30'))
    MAX_DELAY_SECONDS = int(os.getenv('MAX_DELAY_SECONDS', '600'))
    BACKFILL_BATCH_SIZE = int(os.getenv('BACKFILL_BATCH_SIZE', '8'))

    # Monitored YouTube channels
    # Tiers: supreme (6mo), leader (6mo), mid (3mo), occasional (2mo)
    # Myron channels: 36mo (full archive)
    CHANNELS = [
        # ── Supreme ──────────────────────────────────────────
        {"handle": "MyronGolden", "name": "Myron Golden", "domain": "business", "tier": "supreme", "lookback_months": 36},
        {"handle": "BibleStudyWithMyronGolden", "name": "Bible Study with Myron Golden", "domain": "faith", "tier": "supreme", "lookback_months": 36},
        {"handle": "hubermanlab", "name": "Huberman Lab", "domain": "health", "tier": "supreme", "lookback_months": 6},
        {"handle": "ChrisWillx", "name": "Chris Williamson", "domain": "mindset", "tier": "supreme", "lookback_months": 6},
        {"handle": "TheDiaryOfACEO", "name": "The Diary of a CEO", "domain": "business", "tier": "supreme", "lookback_months": 6},
        {"handle": "RealCoffeewithScottAdams", "name": "Scott Adams", "domain": "political", "tier": "supreme", "lookback_months": 6},
        {"handle": "AILABS-393", "name": "AI Labs", "domain": "ai", "tier": "supreme", "lookback_months": 6},
        {"handle": "JREClips", "name": "JRE Clips", "domain": "general", "tier": "supreme", "lookback_months": 6},
        {"handle": "mindsetmentorpodcast", "name": "Mindset Mentor", "domain": "mindset", "tier": "supreme", "lookback_months": 6},
        # ── AI Leaders ───────────────────────────────────────
        {"handle": "mreflow", "name": "MreFlow", "domain": "ai", "tier": "leader", "lookback_months": 6},
        {"handle": "GregIsenberg", "name": "Greg Isenberg", "domain": "ai", "tier": "leader", "lookback_months": 6},
        {"handle": "unsupervised-learning", "name": "Unsupervised Learning", "domain": "ai", "tier": "leader", "lookback_months": 6},
        {"handle": "raroque", "name": "Raroque", "domain": "ai", "tier": "leader", "lookback_months": 6},
        {"handle": "replit", "name": "Replit", "domain": "ai", "tier": "leader", "lookback_months": 6},
        {"handle": "BMadCode", "name": "BMad Code", "domain": "ai", "tier": "leader", "lookback_months": 6},
        {"handle": "AndrejKarpathy", "name": "Andrej Karpathy", "domain": "ai", "tier": "leader", "lookback_months": 12},
        # ── Business Leaders ─────────────────────────────────
        {"handle": "TheIcedCoffeeHour", "name": "The Iced Coffee Hour", "domain": "business", "tier": "leader", "lookback_months": 6},
        # ── Political Leaders ────────────────────────────────
        {"handle": "VALUETAINMENT", "name": "Valuetainment", "domain": "political", "tier": "leader", "lookback_months": 6},
        # ── Mindset & Health Leaders ─────────────────────────
        {"handle": "NapoleonHill_Wisdom", "name": "Napoleon Hill Wisdom", "domain": "mindset", "tier": "leader", "lookback_months": 6},
        {"handle": "JordanBPeterson", "name": "Jordan B Peterson", "domain": "mindset", "tier": "leader", "lookback_months": 6},
        {"handle": "pradipjamnadasmd", "name": "Dr. Pradip Jamnadas", "domain": "health", "tier": "leader", "lookback_months": 6},
        {"handle": "AfterSkool", "name": "After Skool", "domain": "mindset", "tier": "leader", "lookback_months": 6},
        {"handle": "ultimatehumanpodcast", "name": "Ultimate Human Podcast", "domain": "health", "tier": "leader", "lookback_months": 6},
        {"handle": "askvinh", "name": "Ask Vinh", "domain": "mindset", "tier": "leader", "lookback_months": 6},
        {"handle": "melrobbins", "name": "Mel Robbins", "domain": "mindset", "tier": "leader", "lookback_months": 6},
        # ── General Mid-tier ─────────────────────────────────
        {"handle": "joerogan", "name": "Joe Rogan", "domain": "general", "tier": "mid", "lookback_months": 3},
        {"handle": "lexfridman", "name": "Lex Fridman", "domain": "general", "tier": "mid", "lookback_months": 3},
        # ── AI Mid-tier ──────────────────────────────────────
        {"handle": "AZisk", "name": "AZisk", "domain": "ai", "tier": "mid", "lookback_months": 3},
        {"handle": "Mark_Kashef", "name": "Mark Kashef", "domain": "ai", "tier": "mid", "lookback_months": 3},
        {"handle": "NetworkChuck", "name": "NetworkChuck", "domain": "ai", "tier": "mid", "lookback_months": 3},
        {"handle": "sabrina_ramonov", "name": "Sabrina Ramonov", "domain": "ai", "tier": "mid", "lookback_months": 3},
        # ── Business Mid-tier ────────────────────────────────
        {"handle": "allin", "name": "All-In Podcast", "domain": "business", "tier": "mid", "lookback_months": 3},
        {"handle": "PodcastBigDeal", "name": "Big Deal Podcast", "domain": "business", "tier": "mid", "lookback_months": 3},
        {"handle": "MyFirstMillionPod", "name": "My First Million", "domain": "business", "tier": "mid", "lookback_months": 3},
        # ── Political Mid-tier ───────────────────────────────
        {"handle": "RubinReport", "name": "The Rubin Report", "domain": "political", "tier": "mid", "lookback_months": 3},
        {"handle": "TuckerCarlson", "name": "Tucker Carlson", "domain": "political", "tier": "mid", "lookback_months": 3},
        {"handle": "Thebasedconservative", "name": "The Based Conservative", "domain": "political", "tier": "mid", "lookback_months": 3},
        {"handle": "ShawnRyanShow", "name": "Shawn Ryan Show", "domain": "political", "tier": "mid", "lookback_months": 3},
        {"handle": "NickShirley", "name": "Nick Shirley", "domain": "political", "tier": "mid", "lookback_months": 3},
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
        {"handle": "AlexFinnOfficial", "name": "Alex Finn", "domain": "ai", "tier": "occasional", "lookback_months": 2},
        # ── Business Occasionally Helpful ────────────────────
        {"handle": "danmartell", "name": "Dan Martell", "domain": "business", "tier": "occasional", "lookback_months": 2},
        # ── Political Occasionally Helpful ───────────────────
        {"handle": "RussellBrand", "name": "Russell Brand", "domain": "political", "tier": "occasional", "lookback_months": 2},
        {"handle": "TheOfficialCartierFamily", "name": "The Cartier Family", "domain": "political", "tier": "occasional", "lookback_months": 2},
    ]
