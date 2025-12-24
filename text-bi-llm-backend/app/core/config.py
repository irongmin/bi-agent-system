# app/core/config.py

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl


class Settings(BaseSettings):
    PROJECT_NAME: str = "IJI Text BI LLM Backend"
    API_V1_STR: str = "/api/v1"

    # CORS (필요시)
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # ========= OPENAI =========
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # (구 버전 호환용)
    OPENAI_BI_MODEL: str = "gpt-4.1-mini"

    # ========= 역할별 모델 =========
    # 0) Router LLM (자연어 질문 → 어떤 모듈로 보낼지 분류)
    OPENAI_ROUTER_MODEL: str = "gpt-4.1-mini"

    # 1) 자연어 → SQL (SQL 생성기)
    OPENAI_SQL_MODEL: str = "gpt-4.1-mini"

    # 2) SQL 결과 → 인사이트 요약 + chart_spec
    OPENAI_INSIGHT_MODEL: str = "gpt-4.1"

    # 3) 보고서/서머리 생성
    OPENAI_REPORT_MODEL: str = "o1-mini"

    # ========= DB 설정 =========
    SQLALCHEMY_DATABASE_URI: str

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
