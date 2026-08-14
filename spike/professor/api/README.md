# Professor Phase 1 API + Phase 2 deployment

The service exposes `POST /api/ask` and `GET /health`. Retrieval, composition,
and orchestration are Flask-free so the live integration test can execute them
inside the credentialed embedding container.

## Deployment (Phase 2 — live on Banner)

Stack dir on Banner: `/opt/stacks/professor` (rsync of `spike/professor/`,
compose + Dockerfile in `deploy/`). Ports from the KnowledgeStack 5000-5099
block, checked free on 2026-08-14:

| Port | Service | URL |
|------|---------|-----|
| 5050 | professor-api (gunicorn, 1 worker × 4 threads) | http://10.0.0.33:5050/health |
| 5060 | OpenWebUI (`professor-openwebui`, persistent volume) | http://10.0.0.33:5060 |

Deploy / update:

```bash
rsync -a --exclude .venv --exclude __pycache__ --exclude .pytest_cache \
  spike/professor/ banner:/opt/stacks/professor/
ssh banner "cd /opt/stacks/professor/deploy && sudo docker compose up -d --build"
ssh banner "sudo bash /opt/stacks/professor/deploy/setup_openwebui.sh"   # idempotent
```

Secrets: `/opt/stacks/professor/deploy/.env` (root-only, assembled from the
knowledge stack's `SURREAL_PASS` + the scoped spike LiteLLM key in
`/root/professor-spike.env`). OpenWebUI admin login is `matt@gerasolo.com`;
the generated password lives root-only in `/root/professor-openwebui-admin.env`
on Banner. Never commit or print any of these values.

The OpenWebUI pipe (`deploy/pipe_professor.py`, function id `professor_myron`)
renders the three tiers as markdown sections, emits one citation/source event
per citation (metadata values must stay strings), and appends an HTML artifact
embedding the first citation's YouTube player plus a timestamped link list.
Verification: `deploy/verify_e2e.sh` (model list + non-stream structure) and
`deploy/verify_citations.py` (chat-bound completion; proves citation events
persist — bare API completions have no chat context and drop emitter events).

## Local development

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
`REC_BOOST`, `REC_HORIZON_DAYS`, and `PROFESSOR_MIN_COSINE`. The embedding
trio MUST match the live ingest index: `embeddings` / 1536 / no prefix.
Never place credentials in this directory.

Run the credentialed integration check from `api/` with:

```bash
python live_test.py
```
