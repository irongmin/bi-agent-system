# app/services/insight_service.py

import json
from typing import Any, Dict, List, Optional

from app.core.llm_client import llm_client
from app.core.config import get_settings

settings = get_settings()

# 🔥 인사이트 + 차트 스펙 생성용 시스템 프롬프트
INSIGHT_SYSTEM_PROMPT = """
너는 자동차 1차 협력사(일지테크)의 구매·생산·재고·판매 데이터를 분석하는
BI 인사이트 생성 AI이다.

입력으로 SQL 조회 결과(행 리스트)를 받으면,
다음 두 가지를 반드시 JSON으로만 반환한다.

1) insight_text
   - 한국어로 3~6줄 정도의 핵심 인사이트 요약
   - 경영진/구매팀장이 바로 이해할 수 있는 수준으로 작성
   - 수치/변동 방향/리스크/액션 포인트를 간단히 언급

2) chart_spec
   - 프론트엔드에서 공통 차트 컴포넌트로 사용하기 위한 메타 정보
   - 형식:
     {
       "type": "line" | "bar" | "pie",
       "x_field": "<가로축 필드명>",
       "y_field": "<세로축 필드명>",
       "title": "<차트 제목 (한국어)>"
     }

[chart_spec 작성 가이드]
- 기간(연도/월/일) 추세면 → type: "line"
- 플랜트/공급사/자재 등 카테고리 비교면 → type: "bar"
- 비중(구성비, 점유율) 위주면 → type: "pie"
- x_field: 가로축으로 쓰기 좋은 필드 (예: year, year_month, plant, vendor_name 등)
- y_field: 합계/평균 등 분석의 대상이 되는 수치 필드 (예: total_amount, stock_amount, shortage_qty 등)
- 차트에 쓸 수 없는 경우(필드가 애매함)에도 최대한 합리적으로 선택하되,
  정말 불가능하면 chart_spec에 null을 넣지 말고, 의미 있는 값을 작성하려고 시도하라.

[출력 형식 (중요)]
- 반드시 아래 JSON 형식 "하나만" 반환한다.
- 자연어 설명, 마크다운, 코드블록, 다른 텍스트를 절대 섞지 마라.

예시:
{
  "insight_text": "2025년 재고금액은 2024년 대비 12% 증가했습니다. ...",
  "chart_spec": {
    "type": "bar",
    "x_field": "plant",
    "y_field": "stock_amount",
    "title": "플랜트별 재고금액 비교"
  }
}
"""


async def generate_insight_and_chart(
    rows: List[Dict[str, Any]],
    question: Optional[str] = None,
    max_preview_rows: int = 50,
) -> Dict[str, Any]:
    """
    SQL 결과 rows + (옵션) 원 질문을 기반으로
    - insight_text
    - chart_spec
    를 생성해서 dict로 반환.

    반환 예:
    {
      "insight_text": "...",
      "chart_spec": { "type": "bar", "x_field": "...", "y_field": "...", "title": "..." }
    }
    """
    # rows가 너무 많으면 앞에서 일부만 잘라서 보냄 (토큰 절약)
    preview_rows = rows[:max_preview_rows]

    payload = {
        "question": question,
        "rows_preview": preview_rows,
    }

    user_content = (
        "다음은 BI 분석용 SQL 조회 결과 일부이다.\n"
        "이 데이터를 보고 핵심 인사이트와 차트 스펙을 JSON으로 생성해라.\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    messages = [
        {"role": "system", "content": INSIGHT_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    raw = await llm_client.chat(messages, model=settings.OPENAI_INSIGHT_MODEL)

    # 기본 반환값
    result: Dict[str, Any] = {
        "insight_text": "",
        "chart_spec": None,
    }

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            result["insight_text"] = parsed.get("insight_text", "") or ""
            result["chart_spec"] = parsed.get("chart_spec", None)
        else:
            # JSON이 dict가 아니면 통째로 insight_text로 씀
            result["insight_text"] = str(parsed)
    except json.JSONDecodeError:
        # JSON 파싱 실패하면 raw 전체를 insight_text로 사용
        result["insight_text"] = raw.strip()

    return result
