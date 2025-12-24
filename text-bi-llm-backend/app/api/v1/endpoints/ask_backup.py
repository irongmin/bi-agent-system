# Backup of ask.py prior to mock logic (for reference)
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ask import AskRequest, AskResponse, SubAnalysis
from app.schemas.analysis import ChartSpec
from app.services.router_service import route_and_run

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask_endpoint(req: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    action, sql, rows, insight_obj, sub_analyses = await route_and_run(db, req.question)

    rows = rows or []
    row_count = len(rows)

    insight_text = None
    chart_spec = None
    kpis = None

    if insight_obj:
        if isinstance(insight_obj, dict):
            insight_text = insight_obj.get("insight_text")
            chart_spec = insight_obj.get("chart_spec")
            kpis = insight_obj.get("kpis")
        else:
            insight_text = getattr(insight_obj, "insight_text", None)
            chart_spec = getattr(insight_obj, "chart_spec", None)
            kpis = getattr(insight_obj, "kpis", None)

    chart_spec_model = None
    if chart_spec:
        if isinstance(chart_spec, dict):
            chart_spec_model = ChartSpec(**chart_spec)
        elif isinstance(chart_spec, ChartSpec):
            chart_spec_model = chart_spec

    norm_sub_analyses: List[SubAnalysis] = []
    for item in sub_analyses or []:
        if isinstance(item, dict):
            norm_sub_analyses.append(SubAnalysis(**item))
        elif isinstance(item, SubAnalysis):
            norm_sub_analyses.append(item)

    return AskResponse(
        question=req.question,
        action=action,
        sql=sql,
        rows=rows,
        row_count=row_count,
        insight=insight_text,
        chart_spec=chart_spec_model,
        sub_analyses=norm_sub_analyses,
        kpis=kpis or {},
    )
