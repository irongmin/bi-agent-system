from pydantic import BaseModel
from typing import Any, List, Dict

class SQLBIRequest(BaseModel):
    question: str

class SQLBIResponse(BaseModel):
    question: str
    sql: str
    rows: List[Dict[str, Any]]
    row_count: int

class SqlBiRequest(BaseModel):
    question: str
