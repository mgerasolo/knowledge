"""
title: Professor
author: KnowledgeStack Professor spike
version: 0.3.0
description: Personality-grounded RAG professors (manifold). Three-tier answers (said / might say / AI extension) with timestamped YouTube citations and an embedded player artifact.
requirements: requests
"""

import asyncio
import html
import json
import os

import requests
from pydantic import BaseModel, Field

# One entry per personality manifest served by the Professor API.
# "short" is the name used inside tier headers and status lines.
PERSONALITIES = [
    {"id": "myron-golden", "name": "Professor: Myron Golden", "short": "Myron"},
    {
        "id": "chris-durkin",
        "name": "Professor: Pastor Chris Durkin",
        "short": "Pastor Chris",
    },
]


def _fmt_ts(seconds: float) -> str:
    s = max(0, int(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


class Pipe:
    class Valves(BaseModel):
        PROFESSOR_API_URL: str = Field(
            default="http://professor-api:5050",
            description="Base URL of the Professor API (same compose network).",
        )
        TIMEOUT_SECONDS: int = Field(default=280)
        MAX_HISTORY_TURNS: int = Field(
            default=20, description="History turns forwarded to /api/ask (API caps at 50)."
        )
        PROFESSOR_API_KEY: str = Field(
            default_factory=lambda: os.getenv("PROFESSOR_API_KEY", ""),
            description="Bearer key for /api/ask (defaults from the container env).",
        )

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self):
        """Manifold: expose one OpenWebUI model per personality."""
        return [{"id": p["id"], "name": p["name"]} for p in PERSONALITIES]

    @staticmethod
    def _personality(body: dict) -> dict:
        """Resolve the personality from the model id (function_id.personality_id)."""
        model = str(body.get("model") or "")
        pipe_id = model.rsplit(".", 1)[-1]
        for p in PERSONALITIES:
            if p["id"] == pipe_id:
                return p
        return PERSONALITIES[0]

    # ------------------------------------------------------------------ helpers

    def _split_messages(self, messages: list) -> tuple[str, list]:
        """Last user message is the question; prior user/assistant turns are history."""
        turns = [
            {"role": m.get("role"), "content": str(m.get("content", "")).strip()[:12000]}
            for m in messages
            if isinstance(m, dict)
            and m.get("role") in ("user", "assistant")
            and str(m.get("content", "")).strip()
        ]
        question = ""
        for i in range(len(turns) - 1, -1, -1):
            if turns[i]["role"] == "user":
                question = turns[i]["content"]
                history = turns[:i]
                break
        else:
            history = []
        return question, history[-self.valves.MAX_HISTORY_TURNS :]

    def _render_markdown(self, data: dict, short: str) -> str:
        tiers = data.get("tiers", {})
        disclaimer = data.get("disclaimer", "AI recreation from public videos")
        parts = [f"## 📖 What {short} has said"]
        said = tiers.get("said") or []
        if said:
            for claim in said:
                refs = "".join(f"[{n}]" for n in claim.get("citations", []))
                parts.append(f"- {claim.get('text', '').strip()} {refs}".rstrip())
        else:
            parts.append("_The corpus is silent here — no directly-supported claims._")
        parts.append(f"\n## 💭 What {short} might say")
        parts.append(tiers.get("might_say") or "_No inference offered for this question._")
        parts.append(f"\n## 🤖 Beyond {short} — AI extension")
        parts.append(tiers.get("extension") or "_(empty)_")
        parts.append(f"\n---\n> ⚠️ {disclaimer}")
        return "\n".join(parts)

    def _render_artifact(self, citations: dict) -> str:
        """HTML block for the Artifacts panel: first citation's player + link list."""
        if not citations:
            return ""
        ordered = sorted(citations.items(), key=lambda kv: int(kv[0]))
        first = ordered[0][1]
        vid = html.escape(str(first.get("video_id", "")), quote=True)
        start = max(0, int(float(first.get("start_time") or 0)))
        rows = []
        for n, c in ordered:
            url = html.escape(str(c.get("url", "")), quote=True)
            title = html.escape(str(c.get("title", "")))
            ts = _fmt_ts(float(c.get("start_time") or 0))
            rows.append(
                f'<li><a href="{url}" target="_blank" rel="noopener">'
                f"[{n}] {title} @ {ts}</a></li>"
            )
        doc = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
body {{ font-family: sans-serif; margin: 8px; background: rgb(255,255,255); }}
iframe {{ width: 100%; aspect-ratio: 16/9; border: 0; }}
h4 {{ margin: 10px 0 4px; }} li {{ margin: 3px 0; }}
</style></head>
<body>
<iframe src="https://www.youtube.com/embed/{vid}?start={start}"
        title="Citation [{ordered[0][0]}]" allowfullscreen></iframe>
<h4>Cited moments</h4>
<ul>
{chr(10).join(rows)}
</ul>
</body>
</html>"""
        return f"\n\n```html\n{doc}\n```\n"

    async def _emit_citations(self, citations: dict, emitter) -> None:
        if emitter is None:
            return
        for n, c in sorted(citations.items(), key=lambda kv: int(kv[0])):
            ts = _fmt_ts(float(c.get("start_time") or 0))
            # Frontend requirement: every metadata value must be a STRING —
            # integers break the citation modal.
            await emitter(
                {
                    "type": "citation",
                    "data": {
                        "document": [str(c.get("quote", ""))],
                        "metadata": [
                            {
                                "source": str(c.get("url", "")),
                                "video_id": str(c.get("video_id", "")),
                                "start_time": str(c.get("start_time", "")),
                                "end_time": str(c.get("end_time", "")),
                                "timestamp": ts,
                            }
                        ],
                        "source": {
                            "name": f"[{n}] {c.get('title', '')} @ {ts}",
                            "url": str(c.get("url", "")),
                        },
                    },
                }
            )

    async def _status(self, emitter, description: str, done: bool = False) -> None:
        if emitter is None:
            return
        await emitter(
            {"type": "status", "data": {"description": description, "done": done}}
        )

    # --------------------------------------------------------------------- pipe

    async def pipe(self, body: dict, __event_emitter__=None) -> str:
        personality = self._personality(body)
        short = personality["short"]
        question, history = self._split_messages(body.get("messages") or [])
        if not question:
            return f"Ask a question to consult {personality['name']}."

        await self._status(
            __event_emitter__,
            f"Consulting {personality['name']} (retrieval + composition)…",
        )
        payload = {
            "personality_id": personality["id"],
            "question": question,
            "history": history,
        }
        headers = {}
        if self.valves.PROFESSOR_API_KEY:
            headers["Authorization"] = f"Bearer {self.valves.PROFESSOR_API_KEY}"
        try:
            response = await asyncio.to_thread(
                requests.post,
                f"{self.valves.PROFESSOR_API_URL.rstrip('/')}/api/ask",
                json=payload,
                headers=headers,
                timeout=self.valves.TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            await self._status(__event_emitter__, "Professor API unreachable", done=True)
            return f"⚠️ Professor API request failed: {type(exc).__name__}"

        if response.status_code != 200:
            try:
                detail = response.json().get("error", "")
            except ValueError:
                detail = ""
            await self._status(__event_emitter__, "Professor API error", done=True)
            return f"⚠️ Professor API returned {response.status_code}. {detail}".strip()

        try:
            data = response.json()
        except ValueError:
            return "⚠️ Professor API returned malformed JSON."

        citations = data.get("citations") or {}
        await self._emit_citations(citations, __event_emitter__)

        meta = data.get("meta", {})
        total_ms = (meta.get("latency_ms") or {}).get("total", 0)
        coverage = meta.get("coverage_percent")
        await self._status(
            __event_emitter__,
            f"Answered in {total_ms / 1000:.1f}s · {len(citations)} citations"
            + (f" · corpus {coverage}% embedded" if coverage is not None else ""),
            done=True,
        )

        return self._render_markdown(data, short) + self._render_artifact(citations)
