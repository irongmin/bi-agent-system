# app/schemas/insight.py

from typing import Optional, Dict, Any
from pydantic import BaseModel


class InsightResult(BaseModel):
    """
    LLM이 생성한 BI 인사이트 + 시각화용 chart spec
    """
    insight_text: Optional[str] = None
    chart_spec: Optional[Dict[str, Any]] = None
