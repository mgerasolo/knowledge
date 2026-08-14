#!/usr/bin/env python3
"""Prove citation events reach OpenWebUI's frontend data model.

Simulates the real UI flow (bare /api/chat/completions calls have no chat
context, so emitter events are dropped): create a chat, run the completion
bound to it (chat_id + message id + session_id), then read the persisted
assistant message back and show its sources. Run as root on Banner; prints
structure only — no credentials, no full answer text.
"""
import json
import time
import urllib.request
import uuid

BASE = "http://localhost:5060"
MODEL = "professor_myron.myron-golden"
QUESTION = "How do I handle price objections?"

creds = {}
with open("/root/professor-openwebui-admin.env") as fh:
    for line in fh:
        key, _, value = line.strip().partition("=")
        creds[key] = value


def call(path, payload=None, token=None, timeout=300):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method="POST" if data else "GET"
    )
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


token = call(
    "/api/v1/auths/signin",
    {
        "email": creds["OPENWEBUI_ADMIN_EMAIL"],
        "password": creds["OPENWEBUI_ADMIN_PASSWORD"],
    },
)["token"]

user_id, assistant_id = str(uuid.uuid4()), str(uuid.uuid4())
now = int(time.time())
user_msg = {
    "id": user_id,
    "parentId": None,
    "childrenIds": [assistant_id],
    "role": "user",
    "content": QUESTION,
    "models": [MODEL],
    "timestamp": now,
}
assistant_msg = {
    "id": assistant_id,
    "parentId": user_id,
    "childrenIds": [],
    "role": "assistant",
    "content": "",
    "model": MODEL,
    "modelName": "Professor: Myron Golden",
    "timestamp": now,
}
chat = call(
    "/api/v1/chats/new",
    {
        "chat": {
            "title": "e2e citation verification",
            "models": [MODEL],
            "messages": [user_msg, assistant_msg],
            "history": {
                "messages": {user_id: user_msg, assistant_id: assistant_msg},
                "currentId": assistant_id,
            },
        }
    },
    token,
)
chat_id = chat["id"]
print("chat created:", chat_id)

started = time.time()
completion = call(
    "/api/chat/completions",
    {
        "model": MODEL,
        "messages": [{"role": "user", "content": QUESTION}],
        "stream": False,
        "chat_id": chat_id,
        "id": assistant_id,
        "session_id": f"e2e-{uuid.uuid4().hex[:8]}",
    },
    token,
)
print(f"completion accepted; keys: {sorted(completion.keys())}")

# chat_id-bound completions run as a background task — poll until the
# assistant message content lands (retrieval scan + two LLM calls ≈ 40-60s).
message = {}
for _ in range(60):
    stored = call(f"/api/v1/chats/{chat_id}", token=token)
    message = stored["chat"]["history"]["messages"][assistant_id]
    if message.get("content"):
        break
    time.sleep(5)
print(f"answer landed after {round(time.time() - started)}s")
for status in message.get("statusHistory", []):
    print("  status event:", status.get("description"))
content = message.get("content", "")
sources = message.get("sources", [])
print("persisted message content length:", len(content))
for header in ("📖 What Myron has said", "💭 What Myron might say", "🤖 Beyond Myron"):
    print(f"  tier {header!r}:", "PRESENT" if header in content else "MISSING")
print("  html artifact:", "PRESENT" if "```html" in content else "MISSING")
print("persisted citation sources:", len(sources))
for source in sources[:3]:
    name = (source.get("source") or {}).get("name")
    metadata = (source.get("metadata") or [{}])[0]
    print(
        "  -",
        name,
        "| metadata all-str:",
        all(isinstance(v, str) for v in metadata.values()),
        "| video:",
        metadata.get("video_id"),
        "@",
        metadata.get("timestamp"),
    )
