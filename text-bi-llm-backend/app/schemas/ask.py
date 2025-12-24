# app/schemas/ask.py
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.analysis import ChartSpec


class AskRequest(BaseModel):
    question: str


class SubAnalysis(BaseModel):
    name: Optional[str] = None
    insight_text: Optional[str] = None
    chart_spec: Optional[ChartSpec] = None
    rows: List[Dict[str, Any]] = Field(default_factory=list)


class AskResponse(BaseModel):
    question: str
    action: str
    sql: Optional[str] = None
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    insight: Optional[str] = None
    chart_spec: Optional[ChartSpec] = None
    sub_analyses: List[SubAnalysis] = Field(default_factory=list)
    kpis: Dict[str, Any] = Field(default_factory=dict)
    report_text: Optional[str] = None
