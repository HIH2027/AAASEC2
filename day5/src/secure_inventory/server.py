"""Scope-protected MCP inventory service used by the capstone agent."""

import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth import require_scopes
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

load_dotenv()

verifier = StaticTokenVerifier(
    tokens={
        os.getenv("MCP_STUDENT_TOKEN", "student-demo-token"): {
            "client_id": "student",
            "scopes": ["read:public"],
        },
        os.getenv("MCP_ADMIN_TOKEN", "admin-demo-token"): {
            "client_id": "inventory-agent",
            "scopes": ["read:public", "read:inventory"],
        },
    }
)

mcp = FastMCP("Secure Inventory Service", auth=verifier)


@mcp.tool(auth=require_scopes("read:inventory"))
def get_lab_inventory() -> dict:
    """Return protected lab inventory for authorized clients."""
    return {
        "items": [
            {"name": "TS101 iron", "qty": 4, "unit_cost_sar": 320},
            {"name": "ESC 45A", "qty": 12, "unit_cost_sar": 95},
            {"name": "LiPo 4S", "qty": 7, "unit_cost_sar": 210},
        ]
    }


def main() -> None:
    mcp.run(transport="http", host="127.0.0.1", port=8010)


if __name__ == "__main__":
    main()
