"""FastAPI boundary for the Day 3 Evidence Brief Agent."""

from __future__ import annotations

import os
import time
import uuid

from fastapi import FastAPI, HTTPException
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
    version="0.1.0",
)

# Build once when the service starts, not once per request.
agent = build_agent()


class ResponseRequest(BaseModel):
    input: str = Field(min_length=1, description="Plain-text request for the agent")
    model: str | None = None


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
        "version": "0.1.0",
        "capabilities": {"streaming": False},
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
