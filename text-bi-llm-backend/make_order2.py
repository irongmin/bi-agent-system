import os
import json
import numpy as np
import pandas as pd
from sqlalchemy import create_engine

# ==========================
# 0. DB 설정
# ==========================
DB_URL = "mysql+pymysql://ironmin:1234@192.168.2.36:3306/manufacturing"
engine = create_engine(DB_URL)


# ==========================
# 1. PO 번호 생성 함수
# ==========================
def get_po_number(today: str, state_file: str = "po_number_state.json") -> int:
    """
    SAP 스타일 구매오더 번호 생성
    - 10자리 숫자
    - 45로 시작
    - 날짜가 같으면 같은 번호
    - 날짜가 바뀌면 +1
    """
    DEFAULT_PO_NO = 4500000000

    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {"last_date": "", "last_po_no": DEFAULT_PO_NO}

    if state["last_date"] == today:
        po_no = state["last_po_no"]
    else:
        po_no = state["last_po_no"] + 1
        state["last_date"] = today
        state["last_po_no"] = po_no
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    return po_no


# ==========================
# 2. 메인 함수: generate_po_docs
# ==========================
def generate_po_docs(order_date: str):
    """
    주어진 날짜(order_date)에 대해
    - 생산계획 / BOM / 재고 / 기준정보 / 단가를 종합해서
    - 업체별 발주 데이터 (po_docs) 를 생성해서 리턴
      (FastAPI → order_pdf.save_po_pdf 에 그대로 넘길 수 있는 형태)

    리턴 형태:
    [
      {
        "header": {
          "po_no": 4500000001,
          "po_date": "2025-11-24",
          "plant": "1021",
          "vendor_code": "100018",
          "vendor_name": "(주)대신정공",
          "buyer_name": "(자동생성)"
        },
        "items": [
          {
            "품목명": "...",
            "자재번호": "71118-P6000",
            "발주수량": 2900,
            "단위": "EA",
            "단가": 123.45,
            "금액": 358005.0
          },
          ...
        ]
      },
      ...
    ]
    """
    today = order_date
    print(f"[generate_po_docs] START, date = {today}")

    po_number = get_po_number(today)
    print(f"[generate_po_docs] PO 번호: {po_number}")

    # ------------------------------------------------------------
    # STEP 1) all_plan → 부족한 완성품 찾기
    # ------------------------------------------------------------
    sql_all_plan = f"""
    SELECT *
    FROM all_plan
    WHERE date = '{today}';
    """
    df_all = pd.read_sql(sql_all_plan, engine)
    df_all["D0_D1부족"] = pd.to_numeric(df_all["D0_D1부족"], errors="coerce").fillna(0)

    df_short_fg = df_all[df_all["D0_D1부족"] < 0].copy()
    df_short_fg["완성품부족"] = df_short_fg["D0_D1부족"].abs()
    df_short_fg["자재번호"] = df_short_fg["자재번호"].astype(str)

    print(f"[STEP1] all_plan 전체: {len(df_all)}, 부족 완성품: {len(df_short_fg)}")
    if df_short_fg.empty:
        print("[STEP1] 부족한 완성품 없음 → 발주 대상 없음")
        return []

    # ------------------------------------------------------------
    # STEP 2) BOM + 필터 (특별조달유형, 평가클래스)
    # ------------------------------------------------------------
    sql_bom = """
    SELECT 전개번호,
           자재번호,
           구성요소내역,
           소요량_구성품,
           단위량,
           단위,
           조달유형,
           공급업체,
           공급업체명,
           특별조달유형,
           평가클래스
    FROM bom;
    """
    df_bom = pd.read_sql(sql_bom, engine)
    df_bom["전개번호"] = df_bom["전개번호"].astype(str)
    df_bom["자재번호"] = df_bom["자재번호"].astype(str)
    df_bom["구성요소내역"] = df_bom["구성요소내역"].astype(str).str.strip()
    df_bom["소요량_구성품"] = pd.to_numeric(df_bom["소요량_구성품"], errors="coerce").fillna(0)
    df_bom["단위량"] = pd.to_numeric(df_bom["단위량"], errors="coerce").fillna(1)
    df_bom["단위"] = df_bom["단위"].astype(str).str.strip()

    # 전개번호 .0 = 완성품
    current_top = None
    top_list = []
    for _, row in df_bom.iterrows():
        if row["전개번호"] == ".0":
            current_top = row["자재번호"]
        top_list.append(current_top)
    df_bom["완성품자재"] = top_list
    df_bom["구성품"] = df_bom["자재번호"]

    df_bom_child = df_bom[df_bom["전개번호"] != ".0"].copy()

    df_bom_child["특별조달유형"] = (
        df_bom_child["특별조달유형"]
        .astype(str)
        .str.strip()
        .str.lower()
        .replace(["nan", "none"], "")
    )
    df_bom_child["평가클래스"] = (
        df_bom_child["평가클래스"]
        .astype(str)
        .str.strip()
        .replace("nan", "")
    )

    before_filter_len = len(df_bom_child)
    df_bom_child = df_bom_child[
        (df_bom_child["특별조달유형"] == "") |
        (df_bom_child["특별조달유형"] == "0")
    ]
    df_bom_child = df_bom_child[df_bom_child["평가클래스"] != "3000"]

    print(f"[STEP2] BOM 하위 구성품: {before_filter_len} → 필터 후 {len(df_bom_child)}")
    print(f"[STEP2] 조달유형 분포: {df_bom_child['조달유형'].value_counts(dropna=False).to_dict()}")

    # ------------------------------------------------------------
    # STEP 3) 부족 완성품 ↔ BOM 매칭 + 조달유형 F
    # ------------------------------------------------------------
    df_need = df_short_fg.merge(
        df_bom_child,
        left_on="자재번호",
        right_on="완성품자재",
        how="left"
    )

    df_need["필요구성품수량"] = (
        df_need["완성품부족"]
        * df_need["소요량_구성품"]
        * df_need["단위량"]
    )

    df_need = df_need.rename(columns={
        "자재번호_x": "완성품자재번호",
        "구성품": "자재번호",
        "공급업체": "공급업체코드",
        "공급업체명": "공급업체명"
    })

    df_need_F = df_need[df_need["조달유형"] == "F"].copy()
    print(f"[STEP3] 완성품↔BOM 매칭 후: {len(df_need)},  조달유형 F: {len(df_need_F)}")

    if df_need_F.empty:
        print("[STEP3] 조달유형 F(구매품) 없음 → 발주 대상 없음")
        return []

    # ------------------------------------------------------------
    # STEP 4) 재고 반영
    # ------------------------------------------------------------
    month_day = today[5:].replace("-", "_")
    table_name = f"stock_check_{month_day}"
    sql_check = f"""
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = 'manufacturing'
      AND table_name = '{table_name}';
    """
    exist = pd.read_sql(sql_check, engine).iloc[0, 0]
    if exist == 0:
        table_name = "stock_check"
        print(f"[STEP4] {table_name} 사용 (날짜별 테이블 없음)")
    else:
        print(f"[STEP4] {table_name} 사용")

    sql_stock = f"SELECT 플랜트, 자재번호, 재고수량 FROM {table_name};"
    df_stock = pd.read_sql(sql_stock, engine)
    df_stock["자재번호"] = df_stock["자재번호"].astype(str)
    df_stock["재고수량"] = pd.to_numeric(df_stock["재고수량"], errors="coerce").fillna(0)

    df_need_F = df_need_F.merge(
        df_stock,
        on=["플랜트", "자재번호"],
        how="left"
    )

    df_need_F["재고수량"] = df_need_F["재고수량"].fillna(0)
    df_need_F["구성품부족"] = (df_need_F["필요구성품수량"] - df_need_F["재고수량"]).clip(lower=0)

    print(
        f"[STEP4] 재고 반영 후 행 수: {len(df_need_F)}, "
        f"구성품부족 > 0: {(df_need_F['구성품부족'] > 0).sum()}"
    )

    # ------------------------------------------------------------
    # STEP 5) 기준정보 + 적입수량 계산
    # ------------------------------------------------------------
    sql_std = """
    SELECT 플랜트, 자재번호, 적입수량, 최소재고, 구매처
    FROM standard_info;
    """
    df_std = pd.read_sql(sql_std, engine)
    df_std["자재번호"] = df_std["자재번호"].astype(str)
    df_std["적입수량"] = pd.to_numeric(df_std["적입수량"], errors="coerce").fillna(0)
    df_std["최소재고"] = pd.to_numeric(df_std["최소재고"], errors="coerce").fillna(0)
    df_std["적입수량_raw"] = df_std["적입수량"].copy()
    df_std.loc[df_std["적입수량"] == 0, "적입수량"] = 1

    df_need2 = df_need_F.merge(
        df_std,
        on=["플랜트", "자재번호"],
        how="left"
    )

    df_need2["적입수량"] = df_need2["적입수량"].fillna(1)
    df_need2["최소재고"] = df_need2["최소재고"].fillna(0)
    df_need2["구매처"] = df_need2["구매처"].fillna("NO_VENDOR")

    print(f"[STEP5] 기준정보 병합 후 행 수: {len(df_need2)}")
    print(f"[STEP5] 적입수량_raw == 0: {(df_need2['적입수량_raw'] == 0).sum()}")

    df_need2 = df_need2[df_need2["적입수량_raw"] != 0]
    print(f"[STEP5] 적입수량_raw != 0 필터 후 행 수: {len(df_need2)}")

    df_need2["보충필요량"] = df_need2["구성품부족"]
    df_need2["발주수량"] = (
        np.ceil(df_need2["보충필요량"] / df_need2["적입수량"]) * df_need2["적입수량"]
    ).astype(int)

    print(f"[STEP5] 발주수량 > 0: {(df_need2['발주수량'] > 0).sum()}")

    # ------------------------------------------------------------
    # STEP 6) 자재번호 + 업체별 집계 → df_po
    # ------------------------------------------------------------
    df_item_info = df_bom_child[["자재번호", "구성요소내역", "단위"]].drop_duplicates()
    df_item_info = df_item_info.rename(columns={"구성요소내역": "품목명"})

    df_po = (
        df_need2[df_need2["발주수량"] > 0]
        .groupby(["플랜트", "자재번호", "공급업체코드", "공급업체명"], as_index=False)
        .agg({"발주수량": "sum"})
    )
    df_po = df_po.merge(df_item_info, on="자재번호", how="left")

    print(f"[STEP6] df_po 행 수: {len(df_po)}")
    if df_po.empty:
        print("[STEP6] 발주 대상 없음(df_po empty)")
        return []

    # ------------------------------------------------------------
    # STEP 7) 단가(purchase order) + 금액 계산
    # ------------------------------------------------------------
    sql_po_price = """
    SELECT 자재번호, 단가
    FROM `purchase order`;
    """
    df_price = pd.read_sql(sql_po_price, engine)
    df_price["자재번호"] = df_price["자재번호"].astype(str)
    df_price["단가"] = pd.to_numeric(df_price["단가"], errors="coerce").fillna(0)
    df_price = df_price.groupby("자재번호", as_index=False).agg({"단가": "last"})

    df_po = df_po.merge(df_price, on="자재번호", how="left")
    df_po["단가"] = df_po["단가"].fillna(0)

    # 100단위 올림
    df_po["발주수량"] = np.ceil(df_po["발주수량"] / 100) * 100
    df_po["발주수량"] = df_po["발주수량"].astype(int)
    df_po["금액"] = df_po["단가"] * df_po["발주수량"]

    print(f"[STEP7] 단가/금액 적용 후 샘플:\n{df_po.head()}")

    # ------------------------------------------------------------
    # STEP 8) 업체별 po_docs 생성
    # ------------------------------------------------------------
    po_docs = []
    unique_vendors = df_po["공급업체명"].fillna("NO_VENDOR").unique().tolist()
    max_vendors = unique_vendors[:10]  # 최대 10개 업체

    print(f"[STEP8] 총 업체 수: {len(unique_vendors)}, PDF 생성 대상: {len(max_vendors)}")

    for vendor_name in max_vendors:
        df_vendor = df_po[df_po["공급업체명"] == vendor_name].copy()
        if df_vendor.empty:
            continue

        plant = df_vendor["플랜트"].iloc[0]
        vendor_code = str(df_vendor["공급업체코드"].iloc[0]) if "공급업체코드" in df_vendor.columns else ""

        items = []
        for _, row in df_vendor.iterrows():
            items.append(
                {
                    "품목명": row.get("품목명") or "",
                    "자재번호": row["자재번호"],
                    "발주수량": int(row["발주수량"]),
                    "단위": row.get("단위") or "EA",
                    "단가": float(row.get("단가", 0) or 0),
                    "금액": float(row.get("금액", 0) or 0),
                }
            )

        po_docs.append(
            {
                "header": {
                    "po_no": po_number,
                    "po_date": today,
                    "plant": plant,
                    "vendor_code": vendor_code,
                    "vendor_name": vendor_name,
                    "buyer_name": "(자동생성)",
                },
                "items": items,
            }
        )

    print(f"[RESULT] po_docs 개수: {len(po_docs)}")
    return po_docs


# 단독 실행 테스트용
if __name__ == "__main__":
    TEST_DATE = "2025-11-24"
    docs = generate_po_docs(TEST_DATE)
    print("생성된 업체 수:", len(docs))
    for d in docs:
        print(d["header"]["vendor_name"], "아이템 수:", len(d["items"]))
