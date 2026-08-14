"""Thin Flask shell for the Professor service (multi-personality)."""
import hmac

from flask import Flask, jsonify, request

try:
    from .composition import Composer
    from .config import Config
    from .corpus import CorpusError, load_corpus
    from .retrieval import LiteLLMClient, Retriever
    from .service import AskValidationError, ProfessorService
    from .surreal_client import SurrealClient
except ImportError:
    from composition import Composer
    from config import Config
    from corpus import CorpusError, load_corpus
    from retrieval import LiteLLMClient, Retriever
    from service import AskValidationError, ProfessorService
    from surreal_client import SurrealClient


if Config.REQUIRE_SECRETS:
    Config.validate_secrets()

app = Flask(__name__)
db = SurrealClient()
llm = LiteLLMClient()
_retriever = Retriever(db, llm)
_composer = Composer(llm)

# Every *.json in the personalities directory is one professor. CORPUS_PATH
# stays supported (its parent is the directory) so existing env keeps working.
_corpus_errors: dict[str, str] = {}
services: dict[str, ProfessorService] = {}
_personalities_dir = (
    Config.CORPUS_PATH.parent if Config.CORPUS_PATH.suffix == ".json" else Config.CORPUS_PATH
)
for _path in sorted(_personalities_dir.glob("*.json")):
    try:
        _corpus = load_corpus(_path)
        services[_corpus.personality_id] = ProfessorService(
            _corpus, db, _retriever, _composer
        )
    except CorpusError as exc:
        _corpus_errors[_path.name] = str(exc)


def _authorized() -> bool:
    """Bearer-key check for mutating endpoints; open only when no key is set."""
    key = Config.PROFESSOR_API_KEY
    if not key:
        return True  # unit tests / local dev; deployment always sets the key
    supplied = request.headers.get("Authorization", "")
    if supplied.startswith("Bearer "):
        supplied = supplied[len("Bearer ") :]
    return hmac.compare_digest(supplied, key)


@app.post("/api/ask")
def ask():
    if not _authorized():
        return jsonify({"error": "unauthorized"}), 401
    if not services:
        return jsonify({"error": "personality corpus unavailable"}), 503
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = {}
    personality_id = payload.get("personality_id")
    service = services.get(personality_id)
    if service is None:
        return jsonify({"error": "unknown personality_id"}), 400
    try:
        response = service.ask(
            personality_id,
            payload.get("question"),
            payload.get("history"),
        )
        return jsonify(response)
    except AskValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        app.logger.exception("Professor ask failed")
        return jsonify({"error": "answer generation failed"}), 502


@app.get("/api/personalities")
def personalities():
    return jsonify(
        [
            {
                "personality_id": service.corpus.personality_id,
                "display_name": service.corpus.display_name,
                "description": service.corpus.description,
                "videos": len(service.corpus.videos),
            }
            for service in services.values()
        ]
    )


@app.get("/health")
def health():
    corpus_loaded = bool(services)
    database_reachable = db.reachable()
    healthy = corpus_loaded and database_reachable
    body = {
        "status": "healthy" if healthy else "unhealthy",
        "surrealdb": "reachable" if database_reachable else "unreachable",
        "corpus_loaded": corpus_loaded,
        "corpus_videos": sum(len(s.corpus.videos) for s in services.values()),
        "personalities": {
            pid: len(s.corpus.videos) for pid, s in services.items()
        },
    }
    if _corpus_errors:
        body["corpus_errors"] = _corpus_errors
    return jsonify(body), 200 if healthy else 503


if __name__ == "__main__":
    print(f"Starting Professor API on port {Config.PORT}")
    print(f"Personalities loaded: {', '.join(services) or 'none'}")
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
