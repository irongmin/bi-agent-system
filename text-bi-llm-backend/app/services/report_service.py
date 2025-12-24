# app/services/report_service.py

import json
from typing import Any, Dict, List, Optional

from app.core.llm_client import llm_client
from app.core.config import get_settings

settings = get_settings()

REPORT_SYSTEM_PROMPT = """
너는 자동차 부품 1차 협력사(일지테크) 구매·생산·재고·판매 데이터를
임원/팀장 보고용으로 정리하는 보고서 작성 AI이다.

[역할]
- BI 분석 결과(질문, 인사이트 문장, 핵심 수치/표, 차트 스펙)를 입력으로 받아
  한국어로 깔끔한 보고용 텍스트를 작성한다.
- 대상 독자는 구매팀장, 생산관리팀장, 공장장 등이다.

[작성 스타일 가이드]
1. 말투
   - 존댓말, 보고서/메일에 바로 쓸 수 있는 톤
   - 예: "~로 보입니다.", "~가 필요합니다.", "~를 제안드립니다."

2. 구성
   - 1) 분석 개요 (질문/분석 목적)
   - 2) 핵심 인사이트 요약 (3~5줄)
   - 3) 주요 지표/수치 정리 (bullet로 3~7개 정도)
   - 4) 시사점 및 액션 포인트 (2~4개)

3. 표현
   - 숫자는 가능하면 대략적인 규모를 함께 설명
     (예: "약 12% 증가", "월평균 3천만 원 수준")
   - 너무 기술적인 DB/컬럼명은 사용하지 말고,
     플랜트/차종/공급사/재고/발주/판매 등 도메인 용어 위주로 바꿔서 설명.
   - SQL 쿼리 문자열 자체는 텍스트에 노출하지 않는다.

[입력 데이터 형식]
- question: 사용자가 처음 요청한 질문
- insight_text: 인사이트 LLM이 생성한 요약 문장
- chart_spec: 프론트에서 사용할 차트 스펙 (있으면 참조, 없으면 무시)
- rows_sample: SQL rows 일부 (예: 상위 N개)

이 정보를 JSON으로 넘겨준다.

[출력 형식]
- 자연어 한국어 텍스트만 반환한다.
- 마크다운/HTML/JSON 형식 없이, 보고서 본문으로 바로 사용할 수 있도록 작성한다.
"""


async def generate_report_text(
    question: str,
    insight_text: Optional[str] = None,
    rows: Optional[List[Dict[str, Any]]] = None,
    chart_spec: Optional[Dict[str, Any]] = None,
    max_rows_in_prompt: int = 30,
) -> str:
    """
    질문 + 인사이트 + (옵션) rows/chart_spec를 기반으로
    보고서/메일용 텍스트를 생성한다.
    """
    if rows is None:
        rows = []

    payload = {
        "question": question,
        "insight_text": insight_text,
        "chart_spec": chart_spec,
        "rows_sample": rows[:max_rows_in_prompt],
    }

    user_content = (
        "다음은 BI 분석 결과 요약 정보이다. 이 정보를 바탕으로 보고용 텍스트를 작성해라.\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    messages = [
        {"role": "system", "content": REPORT_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    text = await llm_client.chat(messages, model=settings.OPENAI_REPORT_MODEL)
    return text.strip()
