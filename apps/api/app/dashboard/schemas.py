from datetime import datetime

from pydantic import BaseModel, Field


class DashboardMetric(BaseModel):
    label: str
    value: int | float
    detail: str


class RecentScan(BaseModel):
    barcode: str
    product_name: str | None
    score: int | None
    created_at: datetime


class DashboardOut(BaseModel):
    metrics: list[DashboardMetric]
    risk_distribution: dict[str, int] = Field(default_factory=dict)
    top_warnings: list[dict[str, int | str]] = Field(default_factory=list)
    recent_scans: list[RecentScan] = Field(default_factory=list)
