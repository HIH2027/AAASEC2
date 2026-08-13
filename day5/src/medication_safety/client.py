"""Authenticated MCP client for protected patient-profile retrieval."""

import asyncio
import os
from typing import Any

from fastmcp import Client
from fastmcp.client.auth import BearerAuth


def fetch_patient_profile() -> dict[str, Any]:
    """Fetch a de-identified profile with the least credential that allows it."""
    url = os.getenv("MCP_URL", "http://localhost:8010/mcp")
    token = os.getenv("MCP_CLINICAL_TOKEN", "clinical-demo-token")

    async def _fetch() -> dict[str, Any]:
        async with Client(url, auth=BearerAuth(token=token)) as client:
            result = await client.call_tool("get_patient_profile", {})
            return result.data

    return asyncio.run(_fetch())
