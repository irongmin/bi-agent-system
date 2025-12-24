# debug_po_pipeline.py
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

DB_URL = "mysql+pymysql://ironmin:1234@192.168.2.36:3306/manufacturing"
engine = create_engine(DB_URL)

def debug_po(date_str: str):
    print("=== 구매 발주 파이프라인 디버깅 ===")
    print(f"[INPUT] date = {date_str}")
    print()

    # 1) all_plan에서 부족한 완성품
    sql_all_plan = f"""
    SELECT *
    FROM all_plan
    WHERE date = '{date_str}';
    """
    df_all = pd.read_sql(sql_all_plan, engine)
    df_all["D0_D1부족"] = pd.to_numeric(df_all["D0_D1부족"], errors="coerce").fillna(0)
    print(f"[STEP1] all_plan 전체 행 수: {len(df_all)}")

    df_short_fg = df_all[df_all["D0_D1부족"] < 0].copy()
    df_short_fg["완성품부족"] = df_short_fg["D0_D1부족"].abs()
    df_short_fg["자재번호"] = df_short_fg["자재번호"].astype(str)
    print(f"[STEP1] D0_D1부족 < 0 인 부족 완성품 개수: {len(df_short_fg)}")
    print(df_short_fg[["플랜트", "자재번호", "완성품부족"]].head())
    print("-" * 60)

    if df_short_fg.empty:
        print(">> 여기서 이미 0건이라 발주가 안 나옴 (부족한 완성품 없음)")
        return

    # 2) BOM + 필터
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
        df_bom_child["특별조달유형"].astype(str).str.strip().str.lower().replace(["nan", "none"], "")
    )
    df_bom_child["평가클래스"] = df_bom_child["평가클래스"].astype(str).str.strip().replace("nan", "")

    before_filter_len = len(df_bom_child)
    df_bom_child = df_bom_child[
        (df_bom_child["특별조달유형"] == "") |
        (df_bom_child["특별조달유형"] == "0")
    ]
    df_bom_child = df_bom_child[df_bom_child["평가클래스"] != "3000"]

    print(f"[STEP2] BOM 하위 구성품(전개번호 != '.0') 개수(필터 전): {before_filter_len}")
    print(f"[STEP2] BOM 하위 구성품(필터 후) 개수: {len(df_bom_child)}")
    print(f"[STEP2] 조달유형 분포: {df_bom_child['조달유형'].value_counts(dropna=False).to_dict()}")
    print("-" * 60)

    # 3) 필요 구성품 수량 + 조달유형 F 필터
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

    print(f"[STEP3] 완성품 ↔ BOM 매칭 후 행 수: {len(df_need)}")
    print(df_need[["완성품자재", "구성품", "완성품부족", "소요량_구성품", "단위량", "필요구성품수량"]].head())

    df_need = df_need.rename(columns={
        "자재번호_x": "완성품자재번호",
        "구성품": "자재번호",
        "공급업체": "공급업체코드",
        "공급업체명": "공급업체명"
    })

    df_need_F = df_need[df_need["조달유형"] == "F"].copy()
    print(f"[STEP3] 조달유형 = 'F' 인 행 수: {len(df_need_F)}")
    print("-" * 60)

    if df_need_F.empty:
        print(">> 여기서 0건 → 구매품(F)이 없어서 발주 대상이 없음")
        return

    # 4) 재고 반영
    month_day = date_str[5:].replace("-", "_")
    table_name = f"stock_check_{month_day}"
    print(f"[STEP4] 재고 테이블 후보: {table_name}")

    sql_check = f"""
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = 'manufacturing'
      AND table_name = '{table_name}';
    """
    exist = pd.read_sql(sql_check, engine).iloc[0, 0]
    if exist == 0:
        print(f"[STEP4] {table_name} 없음 → stock_check 테이블 사용")
        table_name = "stock_check"
    else:
        print(f"[STEP4] {table_name} 테이블 존재, 해당 테이블 사용")

    sql_stock = f"""
    SELECT 플랜트, 자재번호, 재고수량
    FROM {table_name};
    """
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

    print(f"[STEP4] 재고 반영 후 행 수(그대로): {len(df_need_F)}")
    print(f"[STEP4] 구성품부족 > 0 인 행 수: {(df_need_F['구성품부족'] > 0).sum()}")
    print(df_need_F[["자재번호", "필요구성품수량", "재고수량", "구성품부족"]].head())
    print("-" * 60)

    # 5) 기준정보 + 적입수량
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

    print(f"[STEP5] 기준정보 병합 후 전체 행 수: {len(df_need2)}")
    print(f"[STEP5] 적입수량_raw == 0 인 행 수: {(df_need2['적입수량_raw'] == 0).sum()}")

    df_need2 = df_need2[df_need2["적입수량_raw"] != 0]
    print(f"[STEP5] 적입수량_raw != 0 필터 후 행 수: {len(df_need2)}")

    df_need2["보충필요량"] = df_need2["구성품부족"]
    df_need2["발주수량"] = (
        np.ceil(df_need2["보충필요량"] / df_need2["적입수량"]) * df_need2["적입수량"]
    ).astype(int)

    print(f"[STEP5] 발주수량 > 0 인 행 수: {(df_need2['발주수량'] > 0).sum()}")
    print(df_need2[["자재번호", "보충필요량", "적입수량_raw", "적입수량", "발주수량"]].head())
    print("-" * 60)

    # 6) 자재번호 + 공급업체별 집계
    df_item_info = df_bom_child[["자재번호", "구성요소내역", "단위"]].drop_duplicates()
    df_item_info = df_item_info.rename(columns={"구성요소내역": "품목명"})

    df_po = (
        df_need2[df_need2["발주수량"] > 0]
        .groupby(["플랜트", "자재번호", "공급업체코드", "공급업체명"], as_index=False)
        .agg({"발주수량": "sum"})
    )
    df_po = df_po.merge(df_item_info, on="자재번호", how="left")

    print(f"[STEP6] 최종 발주 리스트 행 수(df_po): {len(df_po)}")
    print(df_po.head())
    print("=== 디버깅 종료 ===")


if __name__ == "__main__":
    # 여기 날짜를 실제로 프론트에서 쏜 날짜랑 맞춰서 테스트
    TEST_DATE = "2025-11-24"
    debug_po(TEST_DATE)
