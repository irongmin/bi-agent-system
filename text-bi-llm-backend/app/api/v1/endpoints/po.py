from fastapi import APIRouter, HTTPException
from app.schemas.po import GeneratePORequest
import make_order2
from order_pdf import save_po_pdf
import traceback
import logging
import os
from fastapi.responses import FileResponse


router = APIRouter()

PO_BASE_DIR = r"C:/po_gen"

@router.post("/generate_po")
async def generate_po(req: GeneratePORequest):
    """
    1) make_order2.generate_po_docs()로 발주 데이터 생성
    2) order_pdf.save_po_pdf()로 PDF 생성
    3) 생성 건수 / 파일 정보만 리턴
    """
    try:
        print(f"[API] generate_po 호출, date = {req.date}")
        po_docs = make_order2.generate_po_docs(req.date)
        print(f"[API] generate_po_docs 결과 개수: {len(po_docs)}")
    except Exception as e:
        logging.error("발주 데이터 생성 중 오류", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"발주 데이터 생성 중 오류: {e}",
        )

    if not po_docs:
        return {
            "ok": False,
            "date": req.date,
            "count": 0,
            "pdf_infos": [],
            "message": "발주 대상이 없습니다.",
        }

    try:
        pdf_infos = save_po_pdf(po_docs)
        print(f"[API] save_po_pdf 완료, PDF 개수: {len(pdf_infos)}")
    except Exception as e:
        logging.error("PDF 생성 중 오류", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"PDF 생성 중 오류: {e}",
        )

    return {
        "ok": True,
        "date": req.date,
        "count": len(pdf_infos),
        "pdf_infos": pdf_infos,
        "message": f"{len(pdf_infos)}건 발주서 생성 완료 (서버: C:/po_gen)",
    }

@router.get("/download_po")
async def download_po(file_name: str):
    """
    C:/po_gen 아래에 저장된 발주서 PDF 한 건을 브라우저로 내려주는 엔드포인트
    예: /api/v1/po/download_po?file_name=PO_2025-11-24_삼성전자.pdf
    """
    # 혹시라도 상대경로 장난 방지용
    safe_name = os.path.basename(file_name)
    file_path = os.path.join(PO_BASE_DIR, safe_name)

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="해당 파일이 존재하지 않습니다.")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=safe_name,
    )