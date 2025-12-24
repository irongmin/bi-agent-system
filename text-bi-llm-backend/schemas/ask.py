# app/schemas/ask.py

from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel


class SQLResultPayload(BaseModel):
    sql: str
    rows: List[Dict[str, Any]]
    row_count: int


class AskRequest(BaseModel):
    """
    프론트에서 보내는 요청 바디.
    예: { "question": "플랜트별 재고금액 상위 10개 보여줘" }
    """
    question: str


class AskResponse(BaseModel):
    """
    프론트로 나가는 응답 형식.
    - action: 라우터가 선택한 모듈 (sql_bi / report / help)
    - sql_result: sql_bi인 경우에만 채워짐
    - insight: LLM이 만든 인사이트 텍스트
    - chart_spec: 프론트에서 그대로 쓰는 차트 스펙(dict)
    - message: help / report 같은 경우 텍스트 안내용으로 사용 가능
    """
    question: str
    action: Literal["sql_bi", "report", "help"]
    sql_result: Optional[SQLResultPayload] = None
    insight: Optional[str] = None
    chart_spec: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
