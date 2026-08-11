"""Day 3 evidence-brief agent with a stable build_agent() boundary."""

from __future__ import annotations

import ast
import operator as op
import os
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv():
        return False

load_dotenv()
USE_FAKE = os.getenv("USE_FAKE", "0") == "1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

_ALLOWED_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.USub: op.neg,
}


def _safe_eval(node: ast.AST) -> int | float:
    """Evaluate arithmetic AST nodes without allowing names or calls."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](
            _safe_eval(node.left), _safe_eval(node.right)
        )
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Only basic arithmetic is allowed")


def calculate(expression: str) -> float:
    """Evaluate basic arithmetic such as 2 * (3 + 4) safely."""
    return float(_safe_eval(ast.parse(expression, mode="eval").body))


def current_time() -> str:
    """Return the current UTC date and time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def save_evidence_brief(filename: str, markdown: str) -> str:
    """Save a Markdown artifact, confined to the project artifacts folder."""
    stem = Path(filename).stem
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-_").lower()
    if not safe_stem:
        safe_stem = "evidence-brief"
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    destination = ARTIFACTS_DIR / f"{safe_stem}.md"
    destination.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    return f"Saved evidence brief to /artifacts/{destination.name}"


SYSTEM_PROMPT = """You are HIH2027's Evidence Brief Agent.
Turn supplied evidence, notes, or source excerpts into concise, decision-ready
Markdown briefs. Follow the produce-evidence-brief skill whenever it matches.
Separate sourced facts, interpretation, uncertainty, and recommended next
steps. Never invent sources or imply medical diagnosis. If an artifact is
requested, call save_evidence_brief after drafting it.
"""


class FakeAgent:
    """Deterministic stand-in for testing the complete Day 3 pipeline."""

    class _Message:
        def __init__(self, content: str):
            self.content = content

    async def ainvoke(self, payload, config=None):
        user_message = payload["messages"][-1]
        text = (
            user_message["content"]
            if isinstance(user_message, dict)
            else user_message.content
        )
        report = f"""# Evidence Brief: Multi-Agent Systems in Clinical Research

## Question
How can multi-agent systems support clinical research while preserving safety?

## Executive summary
Multi-agent architectures can separate research, quality review, and reporting
responsibilities. Their value depends on explicit handoffs, traceable evidence,
human approval for consequential outputs, and strict tool permissions.

## Evidence supplied
- No external evidence was supplied in this fake-mode smoke test.
- The originating request was: {text[:160]}

## Key findings
- Role separation can improve auditability.
- More agents create more interfaces where context or permissions can fail.
- Human review remains necessary for consequential health-related outputs.

## Uncertainty and limitations
This artifact demonstrates the workflow only. It is not a literature review,
does not cite external sources, and must not be used for clinical decisions.

## Recommended next steps
1. Provide authoritative source material or enable approved research tools.
2. Require source-level citations and an independent quality-review step.
3. Keep a human approval gate before publication or clinical use.

_Generated in deterministic fake mode at {current_time()}._
"""
        saved = save_evidence_brief("multi-agent-clinical-research.md", report)
        reply = (
            "[FAKE AGENT] I created a safety-aware evidence brief. "
            f"{saved}. Arithmetic check: 6 * 7 = {calculate('6*7'):.0f}."
        )
        return {"messages": payload["messages"] + [self._Message(reply)]}


def build_agent():
    """Build the fake or real agent behind the stable Day 3 interface."""
    if USE_FAKE:
        return FakeAgent()

    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=os.getenv(
            "OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free"
        ),
        temperature=0,
        base_url="https://openrouter.ai/api/v1",
    )
    backend = FilesystemBackend(
        root_dir=str(PROJECT_ROOT),
        virtual_mode=True,
    )
    return create_deep_agent(
        model=model,
        tools=[calculate, current_time, save_evidence_brief],
        system_prompt=SYSTEM_PROMPT,
        backend=backend,
        skills=["/skills/"],
    )


if __name__ == "__main__":
    import asyncio

    evidence_agent = build_agent()
    result = asyncio.run(
        evidence_agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Create and save a short evidence brief about safe use "
                            "of multi-agent systems in clinical research."
                        ),
                    }
                ]
            }
        )
    )
    print(result["messages"][-1].content)
