from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


ReportPeriod = Literal["day", "week", "month", "year", "all"]


class ListingSummaryBreakdownItem(BaseModel):
    key: str
    label: str
    count: int = Field(ge=0)


class ListingSummaryResponse(BaseModel):
    global_total: int = Field(ge=0)
    filtered_total: int = Field(ge=0)
    breakdown: list[ListingSummaryBreakdownItem]


class AnalyticsReportResponse(BaseModel):
    filters_applied: dict[str, Any]
    kpis: list[dict[str, Any]]
    series: dict[str, list[dict[str, Any]]]
    rankings: dict[str, list[dict[str, Any]]]
    table_rows: dict[str, list[dict[str, Any]]]


class ReportFilterMetadata(BaseModel):
    period: ReportPeriod = "all"
    date_from: date | None = None
    date_to: date | None = None
