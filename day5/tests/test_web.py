"""Dashboard routes, with the MCP call replaced by validated sample data."""

import pytest
from starlette.testclient import TestClient

from medication_safety import web
from medication_safety.agent import _deterministic_summary
from medication_safety.analysis import assess_profile
from medication_safety.models import AgentResult

SAMPLE = {
    "age": 78,
    "warfarin_indication": "DVT",
    "inr": 1.6,
    "egfr": 42,
    "medications": [
        {"name": "Warfarin"},
        {"name": "Amiodarone"},
        {"name": "Ketoconazole"},
        {"name": "Simvastatin"},
    ],
}


@pytest.fixture
def client(monkeypatch):
    def fake_run(*, offline: bool = False) -> AgentResult:
        assessment = assess_profile(SAMPLE)
        return AgentResult(
            assessment=assessment,
            summary=_deterministic_summary(assessment),
            summary_source="deterministic",
            mode="offline" if offline else "live",
        )

    monkeypatch.setattr(web, "run_agent_result", fake_run)
    with TestClient(web.app) as test_client:
        yield test_client


def test_health_reports_ok_and_rule_count(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "rules": 7}


def test_index_page_carries_the_prototype_notice(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Medication Safety Review" in response.text
    assert "not for clinical use" in response.text
    assert "does not replace" in response.text


def test_analyze_defaults_to_offline_mode(client) -> None:
    response = client.post("/api/analyze", json={})
    assert response.status_code == 200

    payload = response.json()
    assert payload["mode"] == "offline"
    findings = payload["assessment"]["findings"]
    assert findings[0]["severity"] == "CONTRAINDICATED"
    assert findings[0]["action_class"] == "AVOID"
    assert all(f["sources"] for f in findings)


def test_analyze_accepts_live_mode(client) -> None:
    response = client.post("/api/analyze", json={"mode": "live"})
    assert response.status_code == 200
    assert response.json()["mode"] == "live"


def test_analyze_rejects_unknown_mode(client) -> None:
    response = client.post("/api/analyze", json={"mode": "sudo"})
    assert response.status_code == 400
    assert "offline" in response.json()["error"]


def test_response_carries_boundary_and_missing_information(client) -> None:
    assessment = client.post("/api/analyze", json={}).json()["assessment"]
    assert any("does not replace" in line for line in assessment["boundary"])
    assert "Potassium" in assessment["missing_information"]
    assert assessment["profile_summary"]["Liver status"] == "Not provided"


def test_analyze_never_returns_credentials(client) -> None:
    body = client.post("/api/analyze", json={}).text.lower()
    for secret in ("api_key", "token", "authorization", "bearer"):
        assert secret not in body


def test_guardrail_failure_returns_422(client, monkeypatch) -> None:
    def rejecting_run(*, offline: bool = False) -> AgentResult:
        raise ValueError("Medication data failed the prompt-injection guardrail")

    monkeypatch.setattr(web, "run_agent_result", rejecting_run)
    response = client.post("/api/analyze", json={})
    assert response.status_code == 422
    assert "guardrail" in response.json()["error"]


def test_agent_failure_returns_502_without_details(client, monkeypatch) -> None:
    def failing_run(*, offline: bool = False) -> AgentResult:
        raise RuntimeError("OPENROUTER_API_KEY=sk-secret-value is invalid")

    monkeypatch.setattr(web, "run_agent_result", failing_run)
    response = client.post("/api/analyze", json={})
    assert response.status_code == 502
    assert "sk-secret-value" not in response.text
    assert response.json()["error"] == "RuntimeError: agent run failed"
