"""MCP server exposing the Day 3 agent's tools and skills to other agents.

Two categories live here and the distinction is the lesson:

    TOOLS  = actions another agent can CALL   (@mcp.tool)
    SKILLS = knowledge another agent can READ (SkillsDirectoryProvider)

The provider publishes everything under ``skills/`` as MCP resources, for
example ``skill://produce-evidence-brief/SKILL.md``. MCP transports and
discovers a skill; it never executes one. The agent that fetches a skill
interprets SKILL.md in its own runtime with its own tools, which is why any
skill that wants to run something needs an execution boundary of its own.

Run it:
    uv run python src/mcp_server.py
"""

from __future__ import annotations

import os
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider

try:
    from .agent import calculate as _calculate
    from .agent import current_time as _current_time
except ImportError:
    from agent import calculate as _calculate
    from agent import current_time as _current_time

STUDENT_NAME = os.getenv("STUDENT_NAME", "HIH2027")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = PROJECT_ROOT / "skills"

mcp = FastMCP(f"{STUDENT_NAME} Tools")


# ---------- tools: what another agent can do through us ----------


@mcp.tool
def calculate(expression: str) -> float:
    """Evaluate a basic arithmetic expression, for example '2 * (3 + 4) ** 2'."""
    # Shares the agent's parser, so a caller over MCP gets the same
    # names-and-calls-rejected guarantee the local agent has.
    return _calculate(expression)


@mcp.tool
def word_stats(text: str) -> dict:
    """Count words, characters, sentences, and lines in a piece of text."""
    return {
        "words": len(text.split()),
        "characters": len(text),
        "lines": text.count("\n") + 1,
        "sentences": sum(text.count(mark) for mark in ".!?"),
    }


@mcp.tool
def current_time() -> str:
    """Return the current UTC date and time in ISO 8601 format."""
    return _current_time()


# ---------- skills: what another agent can read from us ----------

mcp.add_provider(SkillsDirectoryProvider(roots=SKILLS_DIR))


def main() -> None:
    port = int(os.getenv("MCP_PORT", "8001"))
    # 0.0.0.0 so the container and other machines on the network can reach it.
    mcp.run(transport="http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
