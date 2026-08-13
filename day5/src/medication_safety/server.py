"""Scope-protected MCP service holding the de-identified patient profile.

A medication list is clinical data. Scope separation here demonstrates that a
credential which can read public metadata still cannot read a patient profile.
"""

import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth import require_scopes
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from .sample import SAMPLE_PROFILE

load_dotenv()

verifier = StaticTokenVerifier(
    tokens={
        os.getenv("MCP_STUDENT_TOKEN", "student-demo-token"): {
            "client_id": "student",
            "scopes": ["read:public"],
        },
        os.getenv("MCP_CLINICAL_TOKEN", "clinical-demo-token"): {
            "client_id": "medication-safety-agent",
            "scopes": ["read:public", "read:patient"],
        },
    }
)

mcp = FastMCP("Medication Safety Service", auth=verifier)

@mcp.tool(auth=require_scopes("read:public"))
def get_service_info() -> dict:
    """Return non-clinical service metadata for any authenticated client."""
    return {
        "service": "Medication Safety Service",
        "rule_set": "seven verified deterministic rules",
        "clinical_data": "requires the read:patient scope",
    }


@mcp.tool(auth=require_scopes("read:patient"))
def get_patient_profile() -> dict:
    """Return the de-identified patient profile for authorized clients."""
    return SAMPLE_PROFILE


def main() -> None:
    port = int(os.getenv("MCP_PORT", "8010"))
    mcp.run(transport="http", host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
