"""Validated data contracts for inventory input and analysis output."""

from pydantic import BaseModel, Field


class InventoryItem(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    qty: int = Field(ge=0)
    unit_cost_sar: int = Field(ge=0)


class InventoryPayload(BaseModel):
    items: list[InventoryItem] = Field(min_length=1, max_length=500)


class AnalyzedItem(BaseModel):
    name: str
    qty: int
    unit_cost_sar: int
    total_value_sar: int
    low_stock: bool


class InventoryAnalysis(BaseModel):
    items: list[AnalyzedItem]
    grand_total_sar: int
    low_stock_items: list[str]
