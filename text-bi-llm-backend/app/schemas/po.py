# app/schemas/po.py
from typing import List, Optional, Any
from pydantic import BaseModel

class GeneratePORequest(BaseModel):
    date: str  # "2025-11-24" 형식

class PDFInfo(BaseModel):
    vendor_name: str
    po_date: str
    filepath: str

class GeneratePOResponse(BaseModel):
    date: str
    po_docs: List[Any]      # 상세 구조까지 validation 안 걸고 그냥 통과
    pdf_infos: List[PDFInfo]
    message: Optional[str] = None
