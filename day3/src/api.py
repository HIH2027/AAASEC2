"""FastAPI boundary for the Day 3 Evidence Brief Agent."""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

try:
    from .agent import build_agent
except ImportError:
    from agent import build_agent


STUDENT_NAME = os.getenv("STUDENT_NAME", "HIH2027")
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8000").rstrip("/")

app = FastAPI(
    title=f"{STUDENT_NAME} Evidence Brief Agent",
    description="AAASEC2 Day 3 agent exposed through an OpenResponses-style API.",
    version="0.2.0",
)

# Build once when the service starts, not once per request.
agent = build_agent()


class ResponseRequest(BaseModel):
    input: str = Field(min_length=1, description="Plain-text request for the agent")
    model: str | None = None


def _sse(event: str, data: dict[str, Any]) -> str:
    """Encode one server-sent event."""
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


def _message_text(data: Any) -> str:
    """Extract text deltas from a LangGraph v3 messages event."""
    if not isinstance(data, (tuple, list)) or not data:
        return ""

    message = data[0]
    if isinstance(message, dict):
        event = message.get("event")
        if event == "content-block-delta":
            delta = message.get("delta", {})
            if delta.get("type") == "text-delta":
                return delta.get("text", "")
        if event == "content-block-start":
            block = message.get("content", {})
            if block.get("type") == "text":
                return block.get("text", "")
        return ""

    # Compatibility with message-object streams used by older LangGraph builds.
    message_content = getattr(message, "content", "")
    if isinstance(message_content, str):
        return message_content
    if not isinstance(message_content, list):
        return ""

    text_parts: list[str] = []
    for block in message_content:
        if isinstance(block, str):
            text_parts.append(block)
        elif isinstance(block, dict):
            text = block.get("text")
            if isinstance(text, str):
                text_parts.append(text)
    return "".join(text_parts)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/responses")
async def create_response(request: ResponseRequest) -> dict:
    started = int(time.time())
    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": request.input}]}
        )
        text = result["messages"][-1].content
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Agent request failed") from exc

    return {
        "id": f"resp_{uuid.uuid4().hex[:24]}",
        "object": "response",
        "created_at": started,
        "status": "completed",
        "model": request.model or "hih2027-evidence-brief-agent",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
    }


@app.post("/v1/responses/stream")
async def stream_response(request: ResponseRequest) -> StreamingResponse:
    """Stream agent text over SSE while preserving the regular endpoint."""
    response_id = f"resp_{uuid.uuid4().hex[:24]}"
    payload = {"messages": [{"role": "user", "content": request.input}]}

    async def events() -> AsyncIterator[str]:
        yield _sse(
            "response.created",
            {
                "id": response_id,
                "status": "in_progress",
                "model": request.model or "hih2027-evidence-brief-agent",
            },
        )
        try:
            if hasattr(agent, "astream_events"):
                stream = agent.astream_events(payload, version="v3")
                if inspect.isawaitable(stream):
                    stream = await stream
                async for raw_event in stream:
                    if not isinstance(raw_event, dict):
                        continue
                    if raw_event.get("method") != "messages":
                        continue
                    data = raw_event.get("params", {}).get("data")
                    text = _message_text(data)
                    if text:
                        yield _sse("response.output_text.delta", {"delta": text})
            else:
                # FakeAgent keeps the same HTTP contract without implementing
                # LangGraph's event protocol.
                result = await agent.ainvoke(payload)
                text = result["messages"][-1].content
                yield _sse("response.output_text.delta", {"delta": text})

            yield _sse(
                "response.completed",
                {"id": response_id, "status": "completed"},
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            yield _sse(
                "response.failed",
                {"id": response_id, "status": "failed", "error": "Agent stream failed"},
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/.well-known/agent-card.json")
async def agent_card() -> dict:
    return {
        "protocolVersion": "1.0",
        "name": f"{STUDENT_NAME}-evidence-brief-agent",
        "description": (
            "Creates concise, safety-aware evidence briefs and Markdown artifacts "
            "while clearly stating source and evidence limitations."
        ),
        "url": f"{PUBLIC_URL}/v1/responses",
        "version": "0.2.0",
        "capabilities": {"streaming": True},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/markdown", "text/plain"],
        "skills": [
            {
                "id": "produce-evidence-brief",
                "name": "Evidence brief",
                "description": (
                    "Turns supplied notes or sources into a structured, "
                    "uncertainty-aware evidence brief."
                ),
                "tags": ["research", "evidence", "writing", "safety"],
            },
            {
                "id": "save-evidence-brief",
                "name": "Save evidence brief",
                "description": "Saves the completed brief as a Markdown artifact.",
                "tags": ["artifact", "markdown"],
            },
        ],
    }
