"""A2A discovery and delegation client for the Day 3 agent network.

The two halves of agent-to-agent interaction:

    1. DISCOVER  GET  {peer}/.well-known/agent-card.json
                 "who are you, what can you do, where do I reach you?"
    2. DELEGATE  POST {card["url"]}
                 "do this task for me"

The endpoint is read from the card and never hardcoded. That indirection is
the protocol: discovery decouples knowing where a peer lives from knowing how
to use it, so a peer can move or rename its endpoint without breaking callers.

Usage:
    uv run python src/a2a_client.py http://<peer-host>:<port> "task for their agent"
"""

from __future__ import annotations

import json
import sys
from typing import Any

import httpx

DISCOVERY_PATH = "/.well-known/agent-card.json"
DISCOVERY_TIMEOUT = 10
DELEGATION_TIMEOUT = 120


def discover(peer_base_url: str) -> dict[str, Any]:
    """Fetch and summarise a peer's agent card."""
    url = peer_base_url.rstrip("/") + DISCOVERY_PATH
    response = httpx.get(url, timeout=DISCOVERY_TIMEOUT)
    response.raise_for_status()
    card = response.json()

    if not isinstance(card, dict) or "url" not in card:
        raise ValueError(f"{url} did not return an agent card with a 'url' field")

    print(f"-- discovered: {card.get('name', '?')} (v{card.get('version', '?')})")
    if card.get("description"):
        print(f"   {card['description']}")
    for skill in card.get("skills", []):
        print(f"   * {skill.get('name', '?')}: {skill.get('description', '')}")
    return card


def _extract_output_text(payload: dict[str, Any]) -> str:
    """Pull the assistant text out of an OpenResponses-shaped reply."""
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                return part["text"]
    raise ValueError(
        "no output_text in the peer's response: "
        + json.dumps(payload, ensure_ascii=False)[:300]
    )


def delegate(card: dict[str, Any], task: str) -> str:
    """Send a task to the endpoint the card advertises."""
    endpoint = card["url"]  # from the card, never hardcoded
    print(f"-- delegating to {endpoint} ...")

    response = httpx.post(endpoint, json={"input": task}, timeout=DELEGATION_TIMEOUT)
    response.raise_for_status()
    return _extract_output_text(response.json())


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 1

    peer, task = argv[1], argv[2]
    try:
        card = discover(peer)
        answer = delegate(card, task)
    except httpx.HTTPStatusError as exc:
        print(f"peer returned {exc.response.status_code} for {exc.request.url}")
        return 2
    except httpx.RequestError as exc:
        print(f"could not reach {exc.request.url}: {type(exc).__name__}")
        return 2
    except ValueError as exc:
        print(str(exc))
        return 2

    print("\n-- their agent replied:\n")
    print(answer)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
