from app.core.llm_client import llm_client
from app.core.config import get_settings

settings = get_settings()

HELP_SYSTEM = """
너는 '텍스트 기반 BI 시스템'의 도움말 안내 역할을 한다.

사용자가 시스템 사용법, 기능, 메뉴, 가능한 질문 등을 물으면
간단하고 친절하게 설명해라.

SQL, DB 컬럼명 등을 생성하지 마라. 개념 설명만 한다.
"""

async def generate_help_text(question: str) -> str:
    messages = [
        {"role": "system", "content": HELP_SYSTEM},
        {"role": "user", "content": question},
    ]

    return await llm_client.chat(messages, model=settings.OPENAI_INSIGHT_MODEL)
