# -*- coding: utf-8 -*-
# build_class_maps.py
import argparse
from pathlib import Path
import pandas as pd
from utils_kor import ensure_dir, read_korean_csv

def build_class_maps(list_xlsx, submaster_csv, out_dir):
    out_dir = ensure_dir(out_dir)

    # 1) 로드
    df_list = pd.read_excel(list_xlsx, dtype=str).rename(columns=lambda c: c.strip())
    df_list['제품코드'] = df_list['제품코드'].astype(str).str.replace(r'\D','', regex=True)
    df_list = df_list[df_list['제품코드'].str.len()==9].copy()

    df_subm = read_korean_csv(submaster_csv).rename(columns=lambda c: c.strip())
    # 표준 컬럼명으로 치환
    colmap = {}
    if '일반명코드' in df_subm.columns: colmap['일반명코드'] = '주성분코드'
    if '일반명'   in df_subm.columns: colmap['일반명']   = '주성분명'
    if '분류번호' in df_subm.columns: colmap['분류번호'] = '분류'
    df_subm = df_subm.rename(columns=colmap)

    # 2) (분류, 주성분) 교차표
    cross = df_list[['분류','주성분코드','제품코드','제품명','업체명']].dropna(subset=['분류','주성분코드'])
    agg = (cross.groupby(['분류','주성분코드'])
                .agg(제품수=('제품코드','nunique'),
                     업체수=('업체명','nunique'),
                     예시제품=('제품명','first'))
                .reset_index())

    # 3) 주성분명 합치기
    agg2 = agg.merge(df_subm[['분류','주성분코드','주성분명']].drop_duplicates(),
                     on=['분류','주성분코드'], how='left')

    # 4) 저장물
    # (a) 분류↔주성분 교차표
    agg2.to_csv(Path(out_dir)/"class3_to_substance_crosswalk.csv", index=False, encoding="utf-8-sig")
    # (b) 분류↔제품 매핑
    cross[['분류','제품코드','제품명','업체명','주성분코드']].drop_duplicates().to_csv(
        Path(out_dir)/"class3_to_product_map.csv", index=False, encoding="utf-8-sig"
    )
    # (c) KG 엣지: (HIRAClass3)-[:HAS_SUBSTANCE]->(Substance)
    agg[['분류','주성분코드']].drop_duplicates().rename(
        columns={'분류':'class3_code','주성분코드':'substance_code'}
    ).to_csv(Path(out_dir)/"kg_edges_class3_has_substance.csv", index=False, encoding="utf-8-sig")

    # 콘솔 요약
    print(f"[OK] class3: {agg['분류'].nunique():,}, substances: {agg['주성분코드'].nunique():,}")
    print(f"[OK] outputs @ {out_dir}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--list_xlsx",     required=True, help="HIRA 9자리 제품코드 포함 약제목록 엑셀")
    ap.add_argument("--submaster_csv", required=True, help="심평원 약가마스터 의약품주성분 CSV(분류번호/일반명코드/일반명 포함)")
    ap.add_argument("--out_dir",       default="out", help="결과물 저장 폴더")
    args = ap.parse_args()
    build_class_maps(args.list_xlsx, args.submaster_csv, args.out_dir)
