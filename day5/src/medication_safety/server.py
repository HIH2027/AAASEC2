"""Scope-protected MCP service holding the de-identified patient profile.

A medication list is clinical data. Scope separation here demonstrates that a
credential which can read public metadata still cannot read a patient profile.
"""

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
        os.getenv("MCP_CLINICAL_TOKEN", "clinical-demo-token"): {
            "client_id": "medication-safety-agent",
            "scopes": ["read:public", "read:patient"],
        },
    }
)

mcp = FastMCP("Medication Safety Service", auth=verifier)

# De-identified sample profile. No name, no record number, no date of birth.
SAMPLE_PROFILE = {
    "age": 78,
    "warfarin_indication": "DVT",
    "dvt_timing": "7 years ago",
    "inr": 1.6,
    "egfr": 42,
    "crcl": 38,
    "serum_creatinine": 1.6,
    "dialysis": False,
    "liver_status": "Not provided",
    "aspirin_clopidogrel_indication": "Not provided",
    "potassium": "Not provided",
    "magnesium": "Not provided",
    "qtc_ms": "Not provided",
    "heart_rate": "Not provided",
    "digoxin_level": "Not provided",
    "cbc_hemoglobin": "Not provided",
    "medications": [
        {"name": "Warfarin", "dose": "5 mg", "frequency": "once daily"},
        {"name": "Amiodarone", "dose": "200 mg", "frequency": "once daily"},
        {"name": "Aspirin", "dose": "81 mg", "frequency": "once daily"},
        {
            "name": "Ketoconazole",
            "dose": "200 mg",
            "frequency": "once daily",
            "route": "oral",
        },
        {"name": "Digoxin", "dose": "0.125 mg", "frequency": "once daily"},
        {"name": "Simvastatin", "dose": "40 mg", "frequency": "at bedtime"},
        {
            "name": "Metoprolol succinate",
            "dose": "50 mg",
            "frequency": "once daily",
        },
        {"name": "Fluoxetine", "dose": "20 mg", "frequency": "once daily"},
        {"name": "Clopidogrel", "dose": "75 mg", "frequency": "once daily"},
        {"name": "Spironolactone", "dose": "25 mg", "frequency": "once daily"},
        {
            "name": "Ibuprofen",
            "dose": "400 mg",
            "frequency": "three times daily as needed",
        },
    ],
}


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
