# app/schemas/analysis.py
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ChartSpec(BaseModel):
    """
    프론트에서 그대로 쓰는 차트 명세.
    (지금도 AskResponse.chart_spec 비슷하게 쓰고 있을 거라 그걸 일반화)
    """
    type: str = "bar"          # 기본 bar, 나중에 line, scatter 등 확장
    x_field: str
    y_field: str
    title: Optional[str] = None


class AnalysisResult(BaseModel):
    """
    하나의 '분석 블록' – 다중 쿼리/다중 분석을 위해 기본 단위로 쓸 모델.
    """
    name: str                               # 예: "plant_inventory_risk"
    sql_list: List[str] = []               # 실행된 SQL들 (1개 이상)
    rows: List[Dict[str, Any]] = []        # 대표 결과(프론트 테이블에 뿌릴 것)
    row_count: int = 0                     # 대표 rows 개수
    insight_text: Optional[str] = None     # 이 분석 블록에 대한 코멘트
    chart_spec: Optional[ChartSpec] = None # 이 블록용 차트 스펙
    kpis: Dict[str, Any] = {}              # KPI나 요약 수치 묶음 (원하는대로 확장)
