"""
휴먼 검증용 질문 100개를 /api/v1/ask 에 순차 호출하고
결과/에러를 모두 CSV로 저장하는 스크립트.

실행:
(textbi) python human_eval_runner.py
"""

import csv
import json
import time
import requests

API_URL = "http://localhost:8000/api/v1/ask"
OUTPUT_CSV = "C:/Users/KDT39/Desktop/KDT_9/최종프로젝트/text-bi-llm-backend/test/output/result1.csv"
INPUT_CSV = "C:/Users/KDT39/Desktop/KDT_9/최종프로젝트/text-bi-llm-backend/test/q_list/question1.csv"  # 선택: CSV로 질문 관리할 경우 사용


def load_questions_from_csv(path: str):
    """
    questions.csv 에서 질문 목록을 읽어온다.
    - 헤더에 'question' 컬럼이 있다고 가정.
    """
    questions = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            q = (row.get("question") or "").strip()
            if q:
                questions.append(q)
    return questions


def load_questions_inline():
    """
    코드 안에 직접 박아 넣는 버전 (필요하면 여기다가 100개 넣어도 됨)
    """
    return [
        "플랜트별 재고금액 상위 10개 보여줘.",
        "공급업체별 발주금액 상위 10개 보여줘.",
        # TODO: 여기에 100개 질문을 쭉 나열
    ]


def main():
    # 1) 질문 로딩: CSV 사용 or 인라인 사용 택1
    try:
        questions = load_questions_from_csv(INPUT_CSV)
        print(f"[INFO] CSV에서 질문 {len(questions)}건 로딩 완료 ({INPUT_CSV})")
    except FileNotFoundError:
        print(f"[WARN] {INPUT_CSV} 파일이 없어 인라인 리스트를 사용합니다.")
        questions = load_questions_inline()
        print(f"[INFO] 인라인 질문 {len(questions)}건 사용")

    results = []

    for idx, q in enumerate(questions, start=1):
        print(f"\n[{idx}/{len(questions)}] 질문: {q}")
        rec = {
            "index": idx,
            "question": q,
            "http_status": None,
            "action": "",
            "sql": "",
            "row_count": "",
            "insight": "",
            "chart_spec_json": "",
            "error_type": "",
            "error_detail": "",
        }

        try:
            resp = requests.post(
                API_URL,
                json={"question": q},
                timeout=60,
            )
            rec["http_status"] = resp.status_code

            # JSON 응답인지 확인
            content_type = resp.headers.get("content-type", "")
            is_json = "application/json" in content_type.lower()

            if resp.ok and is_json:
                data = resp.json()

                rec["action"] = data.get("action", "")
                rec["sql"] = (data.get("sql") or "")[:2000]  # 너무 길면 잘라서 저장
                rec["row_count"] = data.get("row_count", "")

                insight = data.get("insight")
                if isinstance(insight, str):
                    rec["insight"] = insight[:2000]

                chart_spec = data.get("chart_spec")
                if chart_spec is not None:
                    # dict/object → JSON string
                    try:
                        rec["chart_spec_json"] = json.dumps(chart_spec, ensure_ascii=False)
                    except Exception:
                        rec["chart_spec_json"] = str(chart_spec)

            else:
                # 4xx/5xx인 경우 에러 정보 기록
                if is_json:
                    try:
                        data = resp.json()
                    except Exception:
                        data = None
                else:
                    data = None

                rec["error_type"] = "HTTPError"
                if data and isinstance(data, dict):
                    # FastAPI HTTPException(detail=...) 케이스
                    detail = data.get("detail")
                    rec["error_detail"] = str(detail)[:2000]
                else:
                    # text 그대로
                    rec["error_detail"] = resp.text[:2000]

        except Exception as e:
            # 네트워크 오류 / 타임아웃 등
            rec["error_type"] = type(e).__name__
            rec["error_detail"] = str(e)[:2000]

        results.append(rec)

        # API 과부하 방지용 (원하면 더 줄이거나 늘려도 됨)
        time.sleep(0.1)

    # 3) CSV 저장
    fieldnames = [
        "index",
        "question",
        "http_status",
        "action",
        "sql",
        "row_count",
        "insight",
        "chart_spec_json",
        "error_type",
        "error_detail",
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[DONE] 결과 {len(results)}건을 {OUTPUT_CSV} 로 저장 완료")


if __name__ == "__main__":
    main()
