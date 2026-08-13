from secure_inventory.agent import _safe_recommendation
from secure_inventory.analysis import analyze_inventory


ANALYSIS = analyze_inventory(
    {"items": [{"name": "TS101 iron", "qty": 4, "unit_cost_sar": 320}]}
)


def test_clean_ai_recommendation_is_accepted() -> None:
    candidate = "Restock TS101 iron because its quantity is below 5."
    assert _safe_recommendation(ANALYSIS, candidate) == candidate


def test_reasoning_leak_uses_trusted_fallback() -> None:
    leaked = "Here is my thinking process: analyze user input step-by-step."
    assert _safe_recommendation(ANALYSIS, leaked) == (
        "Restock TS101 iron first because quantity is below 5."
    )