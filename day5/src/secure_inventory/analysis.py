"""Deterministic inventory analysis and untrusted-data guardrails."""

import re
from typing import Any

from .models import AnalyzedItem, InventoryAnalysis, InventoryPayload

LOW_STOCK_THRESHOLD = 5
INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?previous",
    r"system\s+prompt",
    r"developer\s+message",
    r"execute\s+(this|the following|command)",
    r"read\s+.*\.ssh",
    r"reveal\s+.*(secret|token|key)",
)


def _reject_prompt_injection(text: str) -> None:
    """Reject instruction-like content arriving through MCP data fields."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise ValueError("Inventory data failed the prompt-injection guardrail")


def analyze_inventory(raw_payload: dict[str, Any]) -> InventoryAnalysis:
    """Validate untrusted MCP data and calculate trusted stock metrics."""
    payload = InventoryPayload.model_validate(raw_payload)
    analyzed: list[AnalyzedItem] = []

    for item in payload.items:
        _reject_prompt_injection(item.name)
        analyzed.append(
            AnalyzedItem(
                name=item.name,
                qty=item.qty,
                unit_cost_sar=item.unit_cost_sar,
                total_value_sar=item.qty * item.unit_cost_sar,
                low_stock=item.qty < LOW_STOCK_THRESHOLD,
            )
        )

    return InventoryAnalysis(
        items=analyzed,
        grand_total_sar=sum(item.total_value_sar for item in analyzed),
        low_stock_items=[item.name for item in analyzed if item.low_stock],
    )
