"""Authenticated MCP client for protected inventory retrieval."""

import asyncio
import os
from typing import Any

from fastmcp import Client
from fastmcp.client.auth import BearerAuth


def fetch_inventory() -> dict[str, Any]:
    """Fetch inventory with the least credential capable of this operation."""
    url = os.getenv("MCP_URL", "http://localhost:8010/mcp")
    token = os.getenv("MCP_ADMIN_TOKEN", "admin-demo-token")

    async def _fetch() -> dict[str, Any]:
        async with Client(url, auth=BearerAuth(token=token)) as client:
            result = await client.call_tool("get_lab_inventory", {})
            return result.data

    return asyncio.run(_fetch())
