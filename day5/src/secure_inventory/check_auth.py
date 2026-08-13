"""Print a small authentication and authorization evidence matrix."""

import asyncio
import os

from fastmcp import Client
from fastmcp.client.auth import BearerAuth


async def _attempt(label: str, token: str | None) -> None:
    url = os.getenv("MCP_URL", "http://localhost:8010/mcp")
    auth = BearerAuth(token=token) if token else None
    try:
        async with Client(url, auth=auth) as client:
            await client.call_tool("get_lab_inventory", {})
        print(f"PASS {label}")
    except Exception as exc:
        print(f"FAIL {label}: {type(exc).__name__}")


async def _main() -> None:
    await _attempt("no token", None)
    await _attempt("wrong token", "wrong-token")
    await _attempt(
        "student token",
        os.getenv("MCP_STUDENT_TOKEN", "student-demo-token"),
    )
    await _attempt(
        "admin token",
        os.getenv("MCP_ADMIN_TOKEN", "admin-demo-token"),
    )


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()