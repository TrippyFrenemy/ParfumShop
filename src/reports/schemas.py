"""Pydantic schemas for reports module."""
from datetime import date
from typing import Optional
from pydantic import BaseModel
from enum import Enum


class PeriodType(str, Enum):
    """Period types for reports filtering."""
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    CUSTOM = "custom"


class ReportFilters(BaseModel):
    """Filters for reports."""
    period: PeriodType = PeriodType.MONTH
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    category_id: Optional[int] = None
    brand: Optional[str] = None
    compare_previous: bool = False
