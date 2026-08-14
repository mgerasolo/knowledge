"""Thin Flask shell for the Professor Phase 1 service."""
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


app = Flask(__name__)
_corpus_error = None
try:
    corpus = load_corpus(Config.CORPUS_PATH)
except CorpusError as exc:
    corpus = None
    _corpus_error = str(exc)

db = SurrealClient()
llm = LiteLLMClient()
service = (
    ProfessorService(corpus, db, Retriever(db, llm), Composer(llm)) if corpus else None
)


@app.post("/api/ask")
def ask():
    if service is None:
        return jsonify({"error": "personality corpus unavailable"}), 503
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = {}
    try:
        response = service.ask(
            payload.get("personality_id"),
            payload.get("question"),
            payload.get("history"),
        )
        return jsonify(response)
    except AskValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        app.logger.exception("Professor ask failed")
        return jsonify({"error": "answer generation failed"}), 502


@app.get("/health")
def health():
    corpus_loaded = corpus is not None and bool(corpus.videos)
    database_reachable = db.reachable()
    healthy = corpus_loaded and database_reachable
    body = {
        "status": "healthy" if healthy else "unhealthy",
        "surrealdb": "reachable" if database_reachable else "unreachable",
        "corpus_loaded": corpus_loaded,
        "corpus_videos": len(corpus.videos) if corpus else 0,
    }
    if _corpus_error:
        body["corpus_error"] = _corpus_error
    return jsonify(body), 200 if healthy else 503


if __name__ == "__main__":
    print(f"Starting Professor API on port {Config.PORT}")
    print(f"Corpus loaded: {len(corpus.videos) if corpus else 0} videos")
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
