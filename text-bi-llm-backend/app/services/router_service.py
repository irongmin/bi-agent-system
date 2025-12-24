# app/services/router_service.py

import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.llm_client import llm_client
from app.core.config import get_settings
from app.schemas.sql_bi import SQLBIRequest, SQLBIResponse
from app.schemas.insight import InsightResult
from app.services.sql_bi_service import run_sql_bi
from app.services.insight_service import generate_insight_and_chart
from app.services.po_open_report import PO_OPEN_KEYWORDS, build_po_open_report

settings = get_settings()

# 🔥 Router LLM용 시스템 프롬프트 (사용자가 준 버전 그대로)
ROUTER_SYSTEM_PROMPT = """
너는 '구매·생산·재고·판매 BI 시스템'에서 들어오는 사용자의 질문을
어떤 처리 모듈로 보낼지 결정하는 라우터 역할을 한다.

반드시 아래 규칙을 지켜서 동작하라.

[역할]
- 사용자의 한국어 질문을 읽고, 이 질문을 어떻게 처리해야 할지 분류한다.
- 분류 결과는 action이라는 필드에 담아서 JSON으로만 출력한다.

[action 종류]
- "sql_bi"
    - SQL로 DB를 조회해서 수치/테이블/차트를 보고 싶은 질문
    - 예시:
      - "작년과 올해 수주금액 비교해줘"
      - "플랜트별 재고금액 TOP 10 보여줘"
      - "NH2 차종 재고 부족한 자재 알려줘"
      - "다음주 생산계획 기준으로 부족 자재 예측해줘"

- "report"
    - 이미 어떤 수치/인사이트가 있다고 가정하고
      그걸 보고서/메일/요약문/슬라이드 형식으로 정리해달라는 요청
    - 예시:
      - "위 분석 결과를 팀장님 보고용으로 정리해줘"
      - "BI 분석 내용을 이메일 형식으로 써줘"
      - "인사이트를 회의자료 형식으로 작성해줘"

- "help"
    - 시스템 사용법, 기능 설명, 메뉴 안내, 일반적인 질문
    - 예시:
      - "이 시스템으로 뭐 할 수 있어?"
      - "어떤 질문을 할 수 있는지 예시 보여줘"
      - "일지테크 AI 구매 BI가 뭐야?"
      - "너 뭐하는 애야?"

[분류 기준]
1. 데이터에서 실제로 값을 뽑아와야 하는 질문이면 → "sql_bi"
2. "위 내용", "앞에서 만든 결과", "보고서", "메일", "정리해줘" 등
   이미 있는 결과를 포맷만 바꾸는 느낌이면 → "report"
3. 시스템 자체의 설명이나 사용법을 묻는다면 → "help"
4. 애매하면 기본값으로 "sql_bi"를 선택한다.

[출력 형식 (중요)]
- 반드시 아래 JSON 형식 "하나만" 반환한다.
- 다른 텍스트, 설명, 마크다운, 코드블록을 절대 섞지 마라.

예시:
{"action": "sql_bi"}
"""


async def route_question(question: str) -> str:
    """
    자연어 질문을 받아서 처리 action을 결정한다.
    반환값 예: "sql_bi", "report", "help"
    """
    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    raw = await llm_client.chat(messages, model=settings.OPENAI_ROUTER_MODEL)
    # 기본값은 sql_bi
    action = "sql_bi"

    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "action" in data:
            candidate = str(data["action"]).strip()
            if candidate in {"sql_bi", "report", "help"}:
                action = candidate
    except json.JSONDecodeError:
        # JSON 아니면 그냥 기본값 유지
        pass

    return action


async def route_and_run(
    db: Session,
    question: str,
) -> Tuple[str, Optional[str], Optional[List[Dict[str, Any]]], Optional[InsightResult], List[Dict[str, Any]]]:
    """
    - router LLM으로 action을 결정하고
    - sql_bi면 SQL 생성 + 실행 + 인사이트 생성까지 수행
    - report/help이면 간단한 InsightResult만 만들어서 반환

    반환:
      (action, sql, rows, insight_obj)
    """
    # 0) 고정 리포트류는 Router LLM 없이 바로 처리 (OPENAI 키 없이도 동작하도록)
    q_lower = question.lower()
    if any(k.lower() in q_lower for k in PO_OPEN_KEYWORDS):
        sql_hint, main_rows, insight_obj, sub_analyses = build_po_open_report(db)
        return "po_open_report", sql_hint, main_rows, insight_obj, [s.model_dump() for s in sub_analyses]

    action = await route_question(question)
    print(f"[router_service] action={action} question={question}")

    # 1) SQL BI 분석 모드
    if action == "sql_bi":
        bi_req = SQLBIRequest(question=question)
        bi_res: SQLBIResponse = await run_sql_bi(db, bi_req)

        # rows가 없을 수도 있으니 방어적으로 처리
        rows = bi_res.rows or []

        # LLM 기반 인사이트 + 차트 스펙 생성
        # generate_insight_and_chart 함수 시그니처에 맞게 sql 인자 제거
        insight_obj = await generate_insight_and_chart(
            rows=rows,
            question=question,
        )

        sub_analyses: List[Dict[str, Any]] = []
        return action, bi_res.sql, bi_res.rows, insight_obj, sub_analyses

    # 2) 보고서/요약 모드 (임시: 안내 메시지)
    if action == "report":
        insight_obj = InsightResult(
            insight_text=(
                "현재 report 모드는 별도 구현되어 있지 않습니다.\n"
                "일단 SQL BI 결과를 먼저 조회한 뒤, 그 결과를 복사하여 "
                "보고서/메일 형식으로 정리해 달라고 요청해 주세요."
            ),
            chart_spec=None,
        )
        return action, None, None, insight_obj, []

    # 3) 도움말 모드
    insight_obj = InsightResult(
        insight_text=(
            "이 시스템은 구매·생산·재고·판매 데이터를 기반으로,\n"
            "자연어로 질문하면 SQL을 자동 생성하고, 결과 테이블과 차트, "
            "인사이트를 제공하는 AI 기반 BI 데모입니다.\n\n"
            "예시 질문:\n"
            "- 플랜트별 재고금액 상위 10개 보여줘\n"
            "- NH2 차종의 월별 생산대수 추이 보여줘\n"
            "- 구매그룹별 발주금액 TOP 10 보여줘\n"
        ),
        chart_spec=None,
    )
    return action, None, None, insight_obj, []
