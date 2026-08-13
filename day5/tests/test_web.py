import pytest
from starlette.testclient import TestClient

from secure_inventory import web
from secure_inventory.analysis import analyze_inventory
from secure_inventory.models import AgentResult

SAMPLE = {
    "items": [
        {"name": "TS101 iron", "qty": 4, "unit_cost_sar": 320},
        {"name": "ESC 45A", "qty": 12, "unit_cost_sar": 95},
    ]
}


@pytest.fixture
def client(monkeypatch):
    """Serve the dashboard with the MCP call replaced by validated sample data."""

    def fake_run(*, offline: bool = False) -> AgentResult:
        analysis = analyze_inventory(SAMPLE)
        return AgentResult(
            analysis=analysis,
            recommendation="Restock TS101 iron first because quantity is below 5.",
            mode="offline" if offline else "live",
        )

    monkeypatch.setattr(web, "run_agent_result", fake_run)
    with TestClient(web.app) as test_client:
        yield test_client


def test_health_reports_ok(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_page_is_served(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Secure Lab Inventory" in response.text


def test_analyze_defaults_to_offline_mode(client) -> None:
    response = client.post("/api/analyze", json={})
    assert response.status_code == 200

    payload = response.json()
    assert payload["mode"] == "offline"
    assert payload["analysis"]["grand_total_sar"] == 2420
    assert payload["analysis"]["low_stock_items"] == ["TS101 iron"]
    assert payload["recommendation"].startswith("Restock TS101 iron")


def test_analyze_accepts_live_mode(client) -> None:
    response = client.post("/api/analyze", json={"mode": "live"})
    assert response.status_code == 200
    assert response.json()["mode"] == "live"


def test_analyze_rejects_unknown_mode(client) -> None:
    response = client.post("/api/analyze", json={"mode": "sudo"})
    assert response.status_code == 400
    assert "offline" in response.json()["error"]


def test_analyze_never_returns_credentials(client) -> None:
    body = client.post("/api/analyze", json={}).text.lower()
    for secret in ("api_key", "token", "authorization", "bearer"):
        assert secret not in body


def test_guardrail_failure_returns_422(client, monkeypatch) -> None:
    def rejecting_run(*, offline: bool = False) -> AgentResult:
        raise ValueError("Inventory data failed the prompt-injection guardrail")

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
