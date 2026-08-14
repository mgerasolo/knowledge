# Professor Phase 1 API

The service exposes `POST /api/ask` and `GET /health`. Retrieval, composition,
and orchestration are Flask-free so the live integration test can execute them
inside the credentialed embedding container.

Create the local test environment without installing anything globally:

```bash
python3 -m venv .venv
.venv/bin/pip install -r api/requirements.txt
.venv/bin/python -m pytest api/tests -q
```

Runtime configuration is read from `SURREAL_URL`, `SURREAL_USER`,
`SURREAL_PASS`, `SURREAL_NS`, `SURREAL_DB`, `LITELLM_URL`,
`LITELLM_CHAT_URL`, and `LITELLM_API_KEY`. Model and retrieval knobs include
`EMBEDDING_MODEL`, `EMBEDDING_DIM`, `CHAT_MODEL`, `EXTENSION_MODEL`,
`REC_BOOST`, `REC_HORIZON_DAYS`, and `PROFESSOR_MIN_COSINE`. Never place
credentials in this directory.

Run the credentialed integration check from `api/` with:

```bash
python live_test.py
```
