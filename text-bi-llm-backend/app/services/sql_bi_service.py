# app/services/sql_bi_service.py

import json
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.llm_client import llm_client
from app.core.config import get_settings
from app.schemas.sql_bi import SQLBIRequest, SQLBIResponse
from app.services.sql_schema import (
    SQL_SYSTEM_PROMPT,
    PURCHASE_SCHEMA_DOC,
)

settings = get_settings()


async def generate_sql(question: str) -> str:
    """
    자연어 질문과 스키마 설명을 기반으로 LLM에게 SQL을 생성시키는 함수.
    """
    user_content = f"스키마:\n{PURCHASE_SCHEMA_DOC}\n\n질문:\n{question}"

    messages = [
        {"role": "system", "content": SQL_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    raw = await llm_client.chat(messages, model=settings.OPENAI_SQL_MODEL)

    # LLM은 {"sql": "..."} 형태의 JSON 문자열을 반환하도록 설계
    try:
        parsed = json.loads(raw)
        sql = parsed.get("sql", "").strip()
    except Exception:
        # 혹시 몰라서 raw 전체를 SQL로 쓰는 fallback
        sql = raw.strip()

    if not sql:
        raise ValueError("LLM이 빈 SQL을 반환했습니다.")

    # 방어 로직: SELECT만 허용, 세미콜론 금지
    if not sql.lstrip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")
    if ";" in sql:
        raise ValueError("Semicolons are forbidden in the SQL query.")

    return sql


def _normalize_value(value):
    """
    DB 조회 결과를 JSON 직렬화 가능한 타입으로 변환.

    - Decimal  -> float
    - date/datetime -> ISO 문자열
    - 나머지는 그대로
    """
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def execute_sql(db: Session, sql: str, limit: int = 200):
    """
    실제로 SQL을 실행하고, JSON-friendly dict 리스트로 반환.
    """
    result = db.execute(text(sql))
    rows = result.fetchmany(limit)
    cols = result.keys()

    json_rows = []
    for r in rows:
        row_dict = {}
        for col, val in zip(cols, r):
            row_dict[col] = _normalize_value(val)
        json_rows.append(row_dict)

    return json_rows


async def run_sql_bi(db: Session, req: SQLBIRequest) -> SQLBIResponse:
    """
    라우터에서 호출하는 메인 진입점:
    - SQL 생성
    - SQL 실행
    - 결과를 스키마에 맞춰 래핑
    """
    sql = await generate_sql(req.question)
    rows = execute_sql(db, sql)

    return SQLBIResponse(
        question=req.question,
        sql=sql,
        rows=rows,
        row_count=len(rows),
    )
