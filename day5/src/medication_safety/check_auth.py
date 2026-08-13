"""Print a small authentication and authorization evidence matrix."""

import asyncio
import os

from fastmcp import Client
from fastmcp.client.auth import BearerAuth


async def _attempt(label: str, token: str | None, tool: str) -> None:
    url = os.getenv("MCP_URL", "http://localhost:8010/mcp")
    auth = BearerAuth(token=token) if token else None
    try:
        async with Client(url, auth=auth) as client:
            await client.call_tool(tool, {})
        print(f"PASS {label}")
    except Exception as exc:
        print(f"FAIL {label}: {type(exc).__name__}")


async def _main() -> None:
    student = os.getenv("MCP_STUDENT_TOKEN", "student-demo-token")
    clinical = os.getenv("MCP_CLINICAL_TOKEN", "clinical-demo-token")

    await _attempt("no token -> patient profile", None, "get_patient_profile")
    await _attempt("wrong token -> patient profile", "wrong-token", "get_patient_profile")
    await _attempt("student token -> service info", student, "get_service_info")
    await _attempt("student token -> patient profile", student, "get_patient_profile")
    await _attempt("clinical token -> patient profile", clinical, "get_patient_profile")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
