import os
import re
import pdfkit
from jinja2 import Template

WKHTML_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
config = pdfkit.configuration(wkhtmltopdf=WKHTML_PATH)

# ✅ sample.html 형식 그대로(하드코딩 값만 Jinja 변수로 변경)
PO_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 6mm; }

  body{
    font-family: "Malgun Gothic", sans-serif;
    font-size: 11px;
    margin:0; padding:0; color:#000;
  }

  /* 제목(샘플처럼 중앙 + 밑줄) */
  .title-wrap{ text-align:center; margin-top:6mm; margin-bottom:3mm; }
  .title{ font-size:20px; font-weight:700; letter-spacing:12px; }
  .title-line{ width:140px; margin:6px auto 0; border-bottom:1px solid #000; height:0; }

  table{ border-collapse:collapse; width:100%; }
  th, td{ border:1px solid #000; padding:3px 4px; vertical-align:middle; }
  .left{ text-align:left; }
  .right{ text-align:right; }
  .center{ text-align:center; }

  /* 상단 헤더 표 */
  .top-table td, .top-table th{ font-size:11px; }
  .po-label{ width:90px; font-weight:700; }
  .po-value{ width:240px; }
  .buyer-label{ width:110px; font-weight:700; }
  .buyer-value{ width:200px; }
  .label{ width:90px; font-weight:700; }

  /* 결재 박스 */
  .appr-head th{ font-weight:700; text-align:center; height:26px; }
  .appr-sign td{ height:64px; }

  /* 품목 표 */
  .items th{ font-weight:700; text-align:center; height:24px; }
  .items td{ height:22px; }

  /* 합계/하단 박스 */
  .sum-row td{ height:24px; font-weight:700; }
  .bottom-box td{ height:86px; }

  /* 하단 좌/우 문구 */
  .footer{ width:100%; margin-top:4px; font-size:10px; overflow:hidden; }
  .footer .l{ float:left; }
  .footer .r{ float:right; }
</style>
</head>

<body>

<!-- 제목 -->
<div class="title-wrap">
  <div class="title">발&nbsp;&nbsp;주&nbsp;&nbsp;서</div>
  <div class="title-line"></div>
</div>

<!-- 상단 헤더: 샘플처럼 한 덩어리 표 + 우측 결재박스(rowspan) -->
<table class="top-table">
  <tr>
    <td class="po-label left">P / O&nbsp;&nbsp;NO&nbsp;&nbsp;:</td>
    <td class="po-value left">{{ po_no }}</td>
    <td class="buyer-label left">구매담당자&nbsp;&nbsp;:</td>
    <td class="buyer-value left">{{ buyer_name }}</td>

    <td rowspan="4" style="width:270px; padding:0;">
      <table style="width:100%; border-collapse:collapse;">
        <tr class="appr-head">
          <th>결재권자</th>
          <th>결재자</th>
          <th>기안자</th>
        </tr>
        <tr class="appr-sign">
          <td></td>
          <td></td>
          <td></td>
        </tr>
      </table>
    </td>
  </tr>

  <tr>
    <td class="label left">발신처</td>
    <td class="left" colspan="3">
      일지테크-경산공장(본사)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;주소&nbsp;:&nbsp;경상북도 경산시 진량읍 공단4로 50
    </td>
  </tr>

  <tr>
    <td class="label left">수신처</td>
    <td class="left" colspan="3">{{ vendor_name }}</td>
  </tr>

  <tr>
    <td class="label left">발주일자</td>
    <td class="left" colspan="3">{{ po_date_display }}</td>
  </tr>
</table>

<!-- 품목 표 -->
<table class="items" style="margin-top:6px;">
  <thead>
    <tr>
      <th style="width:55px;">NO</th>
      <th style="width:200px;">품목명</th>
      <th style="width:170px;">품번</th>
      <th style="width:90px;">수량</th>
      <th style="width:60px;">단위</th>
      <th style="width:80px;">단가</th>
      <th style="width:110px;">금액</th>
      <th style="width:90px;">의뢰부서</th>
      <th style="width:80px;">요청자</th>
    </tr>
  </thead>

  <tbody>
    {% for item in items %}
    <tr>
      <td class="center">{{ 10 * loop.index }}</td>
      <td class="left">{{ item.품목명 }}</td>
      <td class="left">{{ item.자재번호 }}</td>
      <td class="right">{{ "{:,.0f}".format(item.발주수량) }}</td>
      <td class="center">{{ item.단위 }}</td>
      <td class="right">{{ "{:,.0f}".format(item.단가) }}</td>
      <td class="right">{{ "{:,.0f}".format(item.금액) }}</td>
      <td class="center"></td>
      <td class="center"></td>
    </tr>
    {% endfor %}

    {% for _ in range(items|length, 20) %}
    <tr><td>&nbsp;</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
    {% endfor %}
  </tbody>
</table>

<!-- 합계 -->
<table style="margin-top:4px;">
  <tr class="sum-row">
    <td class="center" style="width:75%;">합&nbsp;&nbsp;&nbsp;계</td>
    <td class="right" style="width:25%;">{{ "{:,.0f}".format(total_amount) }}</td>
  </tr>
</table>

<!-- 하단 큰 빈 박스 -->
<table class="bottom-box" style="margin-top:4px;">
  <tr>
    <td style="width:50%;"></td>
    <td style="width:50%;"></td>
  </tr>
</table>

<!-- 푸터 -->
<div class="footer">
  <div class="l">{{ footer_left }}</div>
  <div class="r">{{ footer_right }}</div>
</div>

</body>
</html>
"""

def _safe_filename(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"[\\/:*?\"<>|]", "_", text)
    text = re.sub(r"\s+", "_", text)
    return text

def _date_to_dot(date_str: str) -> str:
    if not date_str:
        return ""
    s = str(date_str).strip()
    if "-" in s:
        y, m, d = s.split("-")
        return f"{y}.{m.zfill(2)}.{d.zfill(2)}"
    return s

def save_po_pdf(po_docs, save_dir="C:/po_gen"):
    abs_path = os.path.abspath(save_dir)
    os.makedirs(abs_path, exist_ok=True)

    template = Template(PO_TEMPLATE)
    pdf_infos = []   # ✅ 생성된 PDF 정보 모으는 리스트

    for po in po_docs:
        header = po["header"]
        items = po["items"]

        po_no = header.get("po_no", "")
        vendor_name = header.get("vendor_name", "")
        buyer_name = header.get("buyer_name", "(자동생성)")
        po_date = header.get("po_date", "")

        po_date_display = _date_to_dot(po_date)

        footer_left = header.get("footer_left", "PUPF01-4    TSP CO., LTD")
        footer_right = header.get("footer_right", "")

        total_amount = sum(float(it.get("금액", 0) or 0) for it in items)

        html = template.render(
            po_no=po_no,
            vendor_name=vendor_name,
            buyer_name=buyer_name,
            po_date_display=po_date_display,
            items=items,
            total_amount=total_amount,
            footer_left=footer_left,
            footer_right=footer_right,
        )

        safe_vendor = _safe_filename(vendor_name) or "VENDOR"
        filename = os.path.join(abs_path, f"PO_{po_date}_{safe_vendor}.pdf")

        pdfkit.from_string(
            html,
            filename,
            configuration=config,
            options={
                "encoding": "utf-8",
                "page-size": "A4",
                "margin-top": "6mm",
                "margin-bottom": "6mm",
                "margin-left": "6mm",
                "margin-right": "6mm",
                "disable-smart-shrinking": ""
            }
        )

        print(f"[✔] PDF 생성 완료 → {filename}")

        # ✅ 프론트에서 쓸 수 있게 정보 저장
        pdf_infos.append({
            "vendor_name": vendor_name,
            "file_path": filename,
            "file_name": os.path.basename(filename),
        })

    # ✅ 반드시 리턴
    return pdf_infos

