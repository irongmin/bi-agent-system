# app/test_llm_main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx
from dotenv import load_dotenv

# .env 로드 (OPENAI_API_KEY 사용)
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_BI_MODEL", "gpt-4.1-mini")

app = FastAPI(title="LLM Test Only (No DB)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용이니까 일단 전부 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LLMTestRequest(BaseModel):
    question: str

class LLMTestResponse(BaseModel):
    answer: str

@app.get("/")
async def root():
    return {"message": "LLM test server running (no DB)"}

@app.post("/test-llm", response_model=LLMTestResponse)
async def test_llm(req: LLMTestRequest):
    """
    DB 전혀 안 쓰고 LLM 호출만 테스트하는 엔드포인트
    """
    if not OPENAI_API_KEY:
        return LLMTestResponse(answer="OPENAI_API_KEY가 설정되어 있지 않습니다. .env를 확인해주세요.")

    system_prompt = (
        "당신은 제조업 구매팀을 위한 BI 분석 도우미입니다. "
        "항상 한국어로 답변하고, 핵심 인사이트를 짧게 요약해 주세요."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.question},
    ]

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": OPENAI_MODEL, "messages": messages}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

    return LLMTestResponse(answer=content)
