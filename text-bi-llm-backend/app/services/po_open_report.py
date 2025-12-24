# app/services/po_open_report.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.analysis import ChartSpec
from app.schemas.ask import SubAnalysis


PO_OPEN_KEYWORDS = [
    "구매오더 미결",
    "미결 구매오더",
    "미결 관리",
    "po open",
    "po 미결",
    "@5d@",
    "미결 현황",
    "경고 건",
    "확인필요",
]


@dataclass(frozen=True)
class POOpenConfig:
    start_date: date
    end_date: date
    base_date: date


def _as_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"Unsupported date type: {type(value)}")


def _rows_from_result(result) -> List[Dict[str, Any]]:
    keys = list(result.keys())
    return [dict(zip(keys, row)) for row in result.fetchall()]


def _po_open_base_cte_sql() -> str:
    # NOTE: 테이블/컬럼명은 실제 DB(migyul) 기준으로 작성.
    # - 상태: @5B@ (완료), @5D@ (미결)
    # - 사유(비고) 컬럼은 현재 DB 인코딩 이슈로 SQL에서 직접 처리하지 않고(=0으로 고정),
    #   리포트 룰은 "미결 + 경과일수" 기준으로만 분류한다.
    return """
WITH base AS (
  SELECT
    `상태`,
    DATE(`생성일`) AS `생성일자`,
    `생성일`,
    `플랜트`,
    `플랜트명`,
    `구매오더`,
    `구매오더품목`,
    `생성자`,
    `생성자명`,
    `공급업체`,
    `공급업체명`,
    `대표차종`,
    `자재번호`,
    `내역`,
    `납품요청일`,
    `오더수량`,
    0 AS `사유있음`,
    DATEDIFF(:base_date, DATE(`생성일`)) AS `경과일수`,
    CASE
      WHEN `상태` = '@5B@' THEN '정상'
      WHEN `상태` = '@5D@' AND DATEDIFF(:base_date, DATE(`생성일`)) >= 14
        THEN '경고'
      WHEN `상태` = '@5D@' AND DATEDIFF(:base_date, DATE(`생성일`)) < 14
        THEN '확인필요'
      WHEN `상태` = '@5D@' THEN '확인필요'
      ELSE '기타'
    END AS `알림등급`
  FROM migyul
  WHERE `생성일` >= :start_dt
    AND `생성일` < DATE_ADD(:end_dt, INTERVAL 1 DAY)
)
"""


def build_po_open_report(
    db: Session,
    config: Optional[POOpenConfig] = None,
) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any], List[SubAnalysis]]:
    """
    구매오더 미결(PO Open) 보고서용 고정 분석.

    return:
      sql_hint, main_rows, insight_obj(dict), sub_analyses
    """
    if config is None:
        config = POOpenConfig(
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
            base_date=date(2025, 11, 30),
        )

    params = {
        "start_dt": config.start_date.isoformat(),
        "end_dt": config.end_date.isoformat(),
        "base_date": config.base_date.isoformat(),
    }

    cte = _po_open_base_cte_sql()

    # 1) KPI / 등급 분포 (메인 차트)
    sql_grade_dist = (
        cte
        + """
SELECT `알림등급`, COUNT(*) AS `건수`
FROM base
GROUP BY `알림등급`
ORDER BY FIELD(`알림등급`, '정상', '확인필요', '경고', '기타');
"""
    )
    main_rows = _rows_from_result(db.execute(text(sql_grade_dist), params))

    # 2) 핵심 카운트
    sql_counts = (
        cte
        + """
SELECT
  COUNT(*) AS total_cnt,
  SUM(CASE WHEN `상태`='@5B@' THEN 1 ELSE 0 END) AS done_cnt,
  SUM(CASE WHEN `상태`='@5D@' THEN 1 ELSE 0 END) AS open_cnt,
  SUM(CASE WHEN `알림등급`='경고' THEN 1 ELSE 0 END) AS warn_cnt,
  SUM(CASE WHEN `알림등급`='확인필요' THEN 1 ELSE 0 END) AS check_cnt,
  SUM(CASE WHEN `상태`='@5D@' AND `사유있음`=1 THEN 1 ELSE 0 END) AS open_reason_cnt
FROM base;
"""
    )
    counts = dict(db.execute(text(sql_counts), params).mappings().first() or {})
    total_cnt = int(counts.get("total_cnt") or 0)
    done_cnt = int(counts.get("done_cnt") or 0)
    open_cnt = int(counts.get("open_cnt") or 0)
    warn_cnt = int(counts.get("warn_cnt") or 0)
    check_cnt = int(counts.get("check_cnt") or 0)
    open_reason_cnt = int(counts.get("open_reason_cnt") or 0)

    def pct(n: int, d: int) -> float:
        return round((n / d * 100.0), 2) if d else 0.0

    reason_rate = pct(open_reason_cnt, open_cnt)
    insight_text = (
        f"분석기간: {config.start_date} ~ {config.end_date} (기준일: {config.base_date})\n"
        f"- 전체 {total_cnt:,}건 중 완료 {done_cnt:,}건({pct(done_cnt, total_cnt)}%), 미결 {open_cnt:,}건({pct(open_cnt, total_cnt)}%)\n"
        f"- 미결 중 확인필요 {check_cnt:,}건({pct(check_cnt, open_cnt)}%), 경고 {warn_cnt:,}건({pct(warn_cnt, open_cnt)}%)\n"
        f"- 미결 건 사유(비고) 기재율 {reason_rate}% (현 버전은 사유 미기재로 가정하여 등급 산정)"
    )

    insight_obj: Dict[str, Any] = {
        "insight_text": insight_text,
        "chart_spec": ChartSpec(type="bar", x_field="알림등급", y_field="건수", title="11월 구매오더 알림등급 분포").model_dump(),
        "kpis": {
            "period_start": config.start_date.isoformat(),
            "period_end": config.end_date.isoformat(),
            "base_date": config.base_date.isoformat(),
            "total_cnt": total_cnt,
            "done_cnt": done_cnt,
            "open_cnt": open_cnt,
            "warn_cnt": warn_cnt,
            "check_cnt": check_cnt,
            "open_rate_pct": pct(open_cnt, total_cnt),
            "warn_rate_total_pct": pct(warn_cnt, total_cnt),
            "warn_rate_open_pct": pct(warn_cnt, open_cnt),
            "check_rate_open_pct": pct(check_cnt, open_cnt),
            "reason_rate_open_pct": reason_rate,
        },
    }

    # 3) 서브 분석들 (차트는 현재 프론트가 bar 1개만 지원하므로 각각 단일 지표로 구성)
    sub_analyses: List[SubAnalysis] = []

    # 3-1. 일별 미결 건수
    sql_daily_open = (
        cte
        + """
SELECT `생성일자`, COUNT(*) AS `미결건수`
FROM base
WHERE `상태`='@5D@'
GROUP BY `생성일자`
ORDER BY `생성일자`;
"""
    )
    rows_daily_open = _rows_from_result(db.execute(text(sql_daily_open), params))
    sub_analyses.append(
        SubAnalysis(
            name="일별 미결 추이",
            insight_text="미결( @5D@ ) 구매오더가 특정 날짜에 급증하는지 확인합니다.",
            chart_spec=ChartSpec(type="line", x_field="생성일자", y_field="미결건수", title="일별 미결( @5D@ ) 건수"),
            rows=rows_daily_open,
        )
    )

    # 3-2. 일별 경고 건수
    sql_daily_warn = (
        cte
        + """
SELECT `생성일자`, COUNT(*) AS `경고건수`
FROM base
WHERE `알림등급`='경고'
GROUP BY `생성일자`
ORDER BY `생성일자`;
"""
    )
    rows_daily_warn = _rows_from_result(db.execute(text(sql_daily_warn), params))
    sub_analyses.append(
        SubAnalysis(
            name="일별 경고 추이",
            insight_text="경고(경과 14일 이상 미결) 발생 구간이 월초에 몰리는지 확인합니다.",
            chart_spec=ChartSpec(type="line", x_field="생성일자", y_field="경고건수", title="일별 경고 건수"),
            rows=rows_daily_warn,
        )
    )

    # 3-3. 경과일수 분포 (미결만)
    sql_elapsed_hist = (
        cte
        + """
SELECT `경과일수`, COUNT(*) AS `건수`
FROM base
WHERE `상태`='@5D@'
GROUP BY `경과일수`
ORDER BY `경과일수`;
"""
    )
    rows_elapsed = _rows_from_result(db.execute(text(sql_elapsed_hist), params))
    sub_analyses.append(
        SubAnalysis(
            name="미결 경과일수 분포",
            insight_text="경고 전환 기준(14일)을 중심으로 미결이 어디에 몰려 있는지 확인합니다.",
            chart_spec=ChartSpec(type="bar", x_field="경과일수", y_field="건수", title="미결 경과일수 분포 (기준일 대비)"),
            rows=rows_elapsed,
        )
    )

    # 3-4. 플랜트별 경고 물량 TOP
    sql_plant_warn = (
        cte
        + """
SELECT
  `플랜트명`,
  SUM(CASE WHEN `알림등급`='경고' THEN 1 ELSE 0 END) AS `경고건수`,
  SUM(CASE WHEN `상태`='@5D@' THEN 1 ELSE 0 END) AS `미결건수`,
  ROUND(
    SUM(CASE WHEN `알림등급`='경고' THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN `상태`='@5D@' THEN 1 ELSE 0 END), 0),
    4
  ) AS `경고비율(미결대비)`
FROM base
GROUP BY `플랜트명`
HAVING `미결건수` > 0
ORDER BY `경고건수` DESC
LIMIT 10;
"""
    )
    rows_plant_warn = _rows_from_result(db.execute(text(sql_plant_warn), params))
    sub_analyses.append(
        SubAnalysis(
            name="플랜트별 경고 Top 10",
            insight_text="경고 물량이 많은 플랜트를 우선 점검합니다. (미결대비 경고비율도 함께 확인)",
            chart_spec=ChartSpec(type="bar", x_field="플랜트명", y_field="경고건수", title="플랜트별 경고 건수 Top 10"),
            rows=rows_plant_warn,
        )
    )

    # 3-5. 생성자별 경고 Top (파레토 근사: 막대 Top 10)
    sql_creator_warn = (
        cte
        + """
SELECT
  COALESCE(NULLIF(TRIM(`생성자명`), ''), '(미상)') AS `생성자명`,
  SUM(CASE WHEN `알림등급`='경고' THEN 1 ELSE 0 END) AS `경고건수`,
  SUM(CASE WHEN `상태`='@5D@' THEN 1 ELSE 0 END) AS `미결건수`,
  ROUND(
    SUM(CASE WHEN `알림등급`='경고' THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN `상태`='@5D@' THEN 1 ELSE 0 END), 0),
    4
  ) AS `경고비율(미결대비)`
FROM base
GROUP BY COALESCE(NULLIF(TRIM(`생성자명`), ''), '(미상)')
HAVING `경고건수` > 0
ORDER BY `경고건수` DESC
LIMIT 10;
"""
    )
    rows_creator_warn = _rows_from_result(db.execute(text(sql_creator_warn), params))
    sub_analyses.append(
        SubAnalysis(
            name="생성자별 경고 Top 10",
            insight_text="경고가 특정 생성자에 편중되는지 확인합니다. (업무 범위 편중 여부 Drill-down 권장)",
            chart_spec=ChartSpec(type="bar", x_field="생성자명", y_field="경고건수", title="생성자별 경고 건수 Top 10"),
            rows=rows_creator_warn,
        )
    )

    # 3-6. 대표차종별 경고 Top
    sql_model_warn = (
        cte
        + """
SELECT
  COALESCE(NULLIF(TRIM(`대표차종`), ''), '(미상)') AS `대표차종`,
  SUM(CASE WHEN `알림등급`='경고' THEN 1 ELSE 0 END) AS `경고건수`,
  SUM(CASE WHEN `상태`='@5D@' THEN 1 ELSE 0 END) AS `미결건수`,
  ROUND(
    SUM(CASE WHEN `알림등급`='경고' THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN `상태`='@5D@' THEN 1 ELSE 0 END), 0),
    4
  ) AS `경고비율(미결대비)`
FROM base
GROUP BY COALESCE(NULLIF(TRIM(`대표차종`), ''), '(미상)')
HAVING `미결건수` > 0
ORDER BY `경고건수` DESC
LIMIT 10;
"""
    )
    rows_model_warn = _rows_from_result(db.execute(text(sql_model_warn), params))
    sub_analyses.append(
        SubAnalysis(
            name="대표차종별 경고 Top 10",
            insight_text="경고 물량이 큰 대표차종을 우선 관리 대상으로 선정합니다.",
            chart_spec=ChartSpec(type="bar", x_field="대표차종", y_field="경고건수", title="대표차종별 경고 건수 Top 10"),
            rows=rows_model_warn,
        )
    )

    # 3-7. 경고 리스트 (업무 처리용 Top 50)
    sql_warn_list = (
        cte
        + """
SELECT
  `플랜트명`,
  `대표차종`,
  `구매오더`,
  `구매오더품목`,
  `공급업체명`,
  `자재번호`,
  `내역`,
  `생성일`,
  `경과일수`,
  `납품요청일`,
  `오더수량`
FROM base
WHERE `알림등급`='경고'
ORDER BY `경과일수` DESC, `플랜트명`, `대표차종`
LIMIT 50;
"""
    )
    rows_warn_list = _rows_from_result(db.execute(text(sql_warn_list), params))
    sub_analyses.append(
        SubAnalysis(
            name="경고 리스트 (Top 50)",
            insight_text="즉시 확인/처리 대상(경고) 상세 목록입니다. 경과일수 기준으로 우선순위를 부여합니다.",
            chart_spec=None,
            rows=rows_warn_list,
        )
    )

    sql_hint = (
        f"-- 구매오더 미결 관리 리포트\n"
        f"-- 기간: {config.start_date} ~ {config.end_date} / 기준일: {config.base_date}\n"
        f"-- 테이블: migyul / 상태: @5B@(완료), @5D@(미결)\n"
        f"-- 알림등급(현 버전): 미결 + 경과>=14 => 경고 / 미결 + 경과<14 => 확인필요\n"
    )

    return sql_hint, main_rows, insight_obj, sub_analyses
