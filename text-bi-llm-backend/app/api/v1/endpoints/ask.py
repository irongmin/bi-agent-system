from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ask import AskRequest, AskResponse, SubAnalysis
from app.schemas.analysis import ChartSpec
from app.services.router_service import route_and_run
from app.services.po_open_mock import get_mock_po_open_payload

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask_endpoint(req: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    """
    자연어 질문을 받아 BI/리포트/차트/서브 분석/리포트 텍스트를 반환한다.
    """
    lower_q = (req.question or "").lower()

    # 구매오더 미결 키워드면 목업으로 즉시 응답
    if any(k in lower_q for k in ["구매오더", "미결", "po open", "@5d@"]):
        mock = get_mock_po_open_payload(req.question)
        return AskResponse(
            question=req.question,
            action=mock.get("action", "po_open_mock"),
            sql=mock.get("sql"),
            rows=mock.get("rows", []),
            row_count=len(mock.get("rows", [])),
            insight=mock.get("insight"),
            report_text=mock.get("report_text"),
            chart_spec=ChartSpec(**mock["chart_spec"]) if mock.get("chart_spec") else None,
            sub_analyses=[SubAnalysis(**sa) for sa in mock.get("sub_analyses", [])],
            kpis=mock.get("kpis") or {},
        )

    # 기본 라우팅 실행
    try:
        action, sql, rows, insight_obj, sub_analyses = await route_and_run(db, req.question)
    except Exception as e:
        import traceback
        print("[ask_endpoint] route_and_run error:", e)
        print(traceback.format_exc())
        raise

    rows = rows or []
    row_count = len(rows)

    insight_text = None
    chart_spec = None
    kpis = None
    report_text = None

    if insight_obj:
        if isinstance(insight_obj, dict):
            insight_text = insight_obj.get("insight_text")
            chart_spec = insight_obj.get("chart_spec")
            kpis = insight_obj.get("kpis")
            report_text = insight_obj.get("report_text")
        else:
            insight_text = getattr(insight_obj, "insight_text", None)
            chart_spec = getattr(insight_obj, "chart_spec", None)
            kpis = getattr(insight_obj, "kpis", None)
            report_text = getattr(insight_obj, "report_text", None)

    # chart_spec 정규화
    chart_spec_model = None
    if chart_spec:
        if isinstance(chart_spec, dict):
            chart_spec_model = ChartSpec(**chart_spec)
        elif isinstance(chart_spec, ChartSpec):
            chart_spec_model = chart_spec

    # sub_analyses 정규화
    norm_sub_analyses: List[SubAnalysis] = []
    for item in sub_analyses or []:
        if isinstance(item, dict):
            norm_sub_analyses.append(SubAnalysis(**item))
        elif isinstance(item, SubAnalysis):
            norm_sub_analyses.append(item)

    # 로그
    print("[ask_endpoint] action=", action)
    print("[ask_endpoint] sql=", sql)
    print("[ask_endpoint] row_count=", row_count)
    print("[ask_endpoint] insight_text=", insight_text)
    print("[ask_endpoint] chart_spec=", chart_spec)
    print("[ask_endpoint] sub_analyses count=", len(norm_sub_analyses))

    # PO 키워드인데 report_text 비어 있으면 목업으로 보완
    if any(k in lower_q for k in ["구매오더", "미결", "po open", "@5d@"]) and report_text is None:
        mock = get_mock_po_open_payload(req.question)
        return AskResponse(
            question=req.question,
            action=mock.get("action", action),
            sql=mock.get("sql", sql),
            rows=mock.get("rows", rows),
            row_count=len(mock.get("rows", rows)),
            insight=mock.get("insight", insight_text),
            report_text=mock.get("report_text"),
            chart_spec=ChartSpec(**mock["chart_spec"]) if mock.get("chart_spec") else chart_spec_model,
            sub_analyses=[SubAnalysis(**sa) for sa in mock.get("sub_analyses", norm_sub_analyses)],
            kpis=mock.get("kpis") or kpis or {},
        )

    return AskResponse(
        question=req.question,
        action=action,
        sql=sql,
        rows=rows,
        row_count=row_count,
        insight=insight_text,
        report_text=report_text,
        chart_spec=chart_spec_model,
        sub_analyses=norm_sub_analyses,
        kpis=kpis or {},
    )
