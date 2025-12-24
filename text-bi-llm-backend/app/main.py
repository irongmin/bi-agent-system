# app/main.py

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router


app = FastAPI(
    title="Text BI LLM Backend",
    version="0.1.0",
)

# ---------------------------------------------------------
# CORS 설정
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 필요하면 "http://localhost:3000" 처럼 좁혀도 됨
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# API 라우터 (/api/v1/...)
# ---------------------------------------------------------
app.include_router(api_router)

# ---------------------------------------------------------
# 프론트엔드 정적 파일 서빙
# 실제 위치: 프로젝트 루트/frontend/index.html
# ---------------------------------------------------------
FRONTEND_DIR = (
    Path(__file__)
    .resolve()
    .parent  # app/
    .parent  # 프로젝트 루트 (text-bi-llm-backend)
    / "frontend"
)

if FRONTEND_DIR.exists():
    # "/" 로 들어오는 요청은 frontend/index.html 로 서빙
    app.mount(
        "/", 
        StaticFiles(directory=str(FRONTEND_DIR), html=True),
        name="frontend",
    )
else:
    # 디버깅용: 프론트 폴더 못 찾을 때 메시지 반환
    @app.get("/")
    async def root():
        return {
            "message": "frontend 디렉터리를 찾을 수 없습니다.",
            "expected_path": str(FRONTEND_DIR),
        }
