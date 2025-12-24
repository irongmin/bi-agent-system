# app/schemas/sql_bi.py

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class SQLBIRequest(BaseModel):
    """
    자연어 질문을 받아 SQL BI 모듈에서 처리할 때 사용하는 요청 스키마
    """
    question: str


class SQLBIResponse(BaseModel):
    """
    SQL BI 모듈에서 반환하는 결과 스키마
    - 생성된 SQL
    - 조회된 rows
    - row 개수
    """
    sql: Optional[str] = None
    rows: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0


# 예전 코드에서 쓰던 이름과의 호환용 alias
SqlBiRequest = SQLBIRequest
SqlBiResponse = SQLBIResponse
