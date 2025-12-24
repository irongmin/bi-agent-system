# app/services/multi_analysis.py
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.schemas.analysis import AnalysisResult, ChartSpec


def _rows_from_result(result) -> List[dict]:
    """
    SQLAlchemy 결과를 List[dict]로 변환하는 유틸
    """
    rows = []
    for row in result:
        # row._mapping 은 1.4+에서 dict 비슷하게 동작
        rows.append(dict(row._mapping))
    return rows


async def build_multi_analysis(
    db: Session,
    question: str,
    main_rows: List[dict]
) -> List[AnalysisResult]:
    """
    메인 분석 결과(main_rows)를 받은 뒤,
    추가로 쏠 만한 서브 분석들을 수행해서 AnalysisResult 리스트로 반환.

    1차 버전: 질문 안에 '플랜트' 또는 '공장'이 들어가면
      - 플랜트별 재고금액 TOP 5
      - 플랜트별 D0_D1 부족 수량 TOP 5
    두 개 서브 분석을 붙여 준다.
    """
    q = question or ""
    sub_results: List[AnalysisResult] = []

    # 플랜트/공장 관련 질문이 아니면 과감히 스킵
    if ("플랜트" not in q) and ("공장" not in q):
        return sub_results

    # ---------------------------
    # 1) 플랜트별 재고금액 TOP 5
    # ---------------------------
    try:
        # 여기서는 예시로 stock_check 테이블 사용
        # 필요하면 stock_check_11_24 등으로 변경 가능
        sql_stock = text("""
            SELECT
                플랜트,
                SUM(재고수량)      AS 재고수량합계,
                SUM(재고금액)      AS 재고금액합계
            FROM stock_check
            GROUP BY 플랜트
            ORDER BY 재고금액합계 DESC
            LIMIT 5
        """)
        result_stock = db.execute(sql_stock)
        rows_stock = _rows_from_result(result_stock)

        if rows_stock:
            sub_results.append(
                AnalysisResult(
                    name="plant_inventory_top5",
                    sql_list=[str(sql_stock)],
                    rows=rows_stock,
                    row_count=len(rows_stock),
                    insight_text=(
                        "플랜트별 재고금액 TOP 5 현황입니다. "
                        "재고금액이 높은 플랜트는 재고부담/캐시플로우 관점에서 추가 점검이 필요할 수 있습니다."
                    ),
                    chart_spec=ChartSpec(
                        type="bar",
                        x_field="플랜트",
                        y_field="재고금액합계",
                        title="플랜트별 재고금액 TOP 5"
                    ),
                    kpis={}
                )
            )
    except Exception as e:
        # 에러 나도 전체 ask는 죽지 않도록 로그만 찍고 넘어간다
        print("[multi_analysis] plant_inventory_top5 error:", e)

    # ---------------------------
    # 2) 플랜트별 2일 기준 부족 수량(D0_D1부족) TOP 5
    # ---------------------------
    try:
        sql_shortage = text("""
            SELECT
                플랜트,
                SUM(
                    CASE
                        WHEN D0_D1부족 < 0 THEN -D0_D1부족
                        ELSE 0
                    END
                ) AS 이틀부족수량
            FROM all_plan
            GROUP BY 플랜트
            HAVING 이틀부족수량 > 0
            ORDER BY 이틀부족수량 DESC
            LIMIT 5
        """)
        result_shortage = db.execute(sql_shortage)
        rows_shortage = _rows_from_result(result_shortage)

        if rows_shortage:
            sub_results.append(
                AnalysisResult(
                    name="plant_shortage_top5",
                    sql_list=[str(sql_shortage)],
                    rows=rows_shortage,
                    row_count=len(rows_shortage),
                    insight_text=(
                        "플랜트별 2일 기준 부족 수량 상위 5개입니다. "
                        "이 구간은 생산·납기 리스크가 높은 구간으로, 사전 발주/증산 여부 검토가 필요합니다."
                    ),
                    chart_spec=ChartSpec(
                        type="bar",
                        x_field="플랜트",
                        y_field="이틀부족수량",
                        title="플랜트별 2일 기준 부족 수량 TOP 5"
                    ),
                    kpis={}
                )
            )
    except Exception as e:
        print("[multi_analysis] plant_shortage_top5 error:", e)

    return sub_results
