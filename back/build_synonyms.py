# -*- coding: utf-8 -*-
# build_synonyms.py
import argparse, json, re
from collections import defaultdict, Counter
from pathlib import Path
import pandas as pd

from utils_kor import ensure_dir, read_korean_csv, norm_text, extract_paren_terms_refined

def build_synonyms(list_xlsx, atc_csv, out_dir):
    out_dir = ensure_dir(out_dir)

    # 1) 로드
    df_list = pd.read_excel(list_xlsx, dtype=str).rename(columns=lambda c: c.strip())
    df_list['제품코드'] = df_list['제품코드'].astype(str).str.replace(r'\D','', regex=True)
    df_list = df_list[df_list['제품코드'].str.len()==9].copy()

    df_atc = read_korean_csv(atc_csv).rename(columns=lambda c: c.strip())
    atc_small = df_atc[['제품코드','ATC코드','ATC코드 명칭']].dropna().astype(str).drop_duplicates()

    # 2) 결합 (제품코드 기준)
    df = pd.merge(df_list[['주성분코드','제품코드','제품명','업체명']],
                  atc_small, on='제품코드', how='left')

    # 3) 주성분코드 단위 그룹핑
    groups = defaultdict(lambda: {
        "products": set(), "paren_terms": [], "atc_codes": set(), "atc_names": set(), "manufacturers": set()
    })
    for _, r in df.iterrows():
        sc = r['주성분코드']
        pname = norm_text(r['제품명'])
        mname = norm_text(r['업체명'])
        atc   = r.get('ATC코드')
        atc_n = norm_text(r.get('ATC코드 명칭'))
        if pname: groups[sc]["products"].add(pname)
        if mname: groups[sc]["manufacturers"].add(mname)
        if pd.notna(atc): groups[sc]["atc_codes"].add(atc)
        if pd.notna(atc_n): groups[sc]["atc_names"].add(atc_n)
        groups[sc]["paren_terms"].extend(extract_paren_terms_refined(pname or ""))

    # 4) 대표라벨/동치어 산출
    records = []
    for sc, data in groups.items():
        paren_counts = Counter([t for t in data["paren_terms"] if t])
        # 한글 성분/염 후보(최빈)
        ko_candidates = [t for t,_ in paren_counts.most_common() if re.search(r'[가-힣]', t)]
        preferred_ko = ko_candidates[0] if ko_candidates else None
        # ATC 영문 후보
        en_candidates = list(data["atc_names"]) if data["atc_names"] else []
        preferred_en = None
        if en_candidates:
            en_candidates = sorted(en_candidates, key=lambda x: (0 if re.search(r'[A-Za-z]', x) else 1, len(x)))
            preferred_en = en_candidates[0]

        # 동치 후보: 제품명 + ATC명칭 + 괄호토큰
        syns = set()
        syns |= {norm_text(x) for x in data["products"] if x}
        syns |= {norm_text(x) for x in data["atc_names"] if x}
        syns |= {norm_text(x) for x in paren_counts if x}
        # 변형(공백삭제, 영문 소문자)
        variants = set()
        for s in list(syns):
            if not s: continue
            variants.add(re.sub(r'\s+', '', s))
            if re.search(r'[A-Za-z]', s):
                variants.add(s.lower())
        syns |= variants
        syns = {s for s in syns if s}

        records.append({
            "canonical_id": f"SUB:{sc}",
            "substance_code": sc,
            "preferred_label_ko": preferred_ko,
            "preferred_label_en": preferred_en,
            "atc_codes": "|".join(sorted(data["atc_codes"])) if data["atc_codes"] else "",
            "synonyms": sorted(list(syns))[:200],   # 과도 노이즈 억제
            "synonym_count": len(syns),
        })

    syn_df = pd.DataFrame(records).sort_values(by=['preferred_label_ko','preferred_label_en','substance_code'])

    # 5) 산출물
    # 5-1) 마스터 CSV/JSONL
    out_csv  = Path(out_dir) / "synonyms_by_substance_code.csv"
    out_jsonl= Path(out_dir) / "synonyms_by_substance_code.jsonl"
    tmp = syn_df.copy()
    tmp['synonyms'] = tmp['synonyms'].apply(lambda L: " | ".join(L))
    tmp.to_csv(out_csv, index=False, encoding="utf-8-sig")

    with open(out_jsonl, "w", encoding="utf-8") as f:
        for _, row in syn_df.iterrows():
            f.write(json.dumps({
                "canonical_id": row["canonical_id"],
                "substance_code": row["substance_code"],
                "preferred_label_ko": row["preferred_label_ko"],
                "preferred_label_en": row["preferred_label_en"],
                "atc_codes": row["atc_codes"],
                "synonyms": row["synonyms"],
            }, ensure_ascii=False) + "\n")

    # 5-2) OpenSearch synonyms_graph 포맷
    def pick_canonical(row):
        return row["preferred_label_ko"] or row["preferred_label_en"]

    lines = []
    for _, row in syn_df.iterrows():
        canon = pick_canonical(row)
        if not canon:
            continue
        syns = [s for s in set(row["synonyms"]) if s and s != canon]
        if not syns:
            continue
        line = ", ".join(sorted(syns)[:50]) + " => " + canon
        lines.append(line)

    with open(Path(out_dir)/"opensearch_synonyms_substance.txt","w",encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 5-3) 고유명사 사전(표면형)
    unique_terms = set()
    unique_terms.update(df_list['제품명'].dropna().map(norm_text))
    unique_terms.update(df_list['업체명'].dropna().map(norm_text))
    unique_terms.update(df_atc['ATC코드 명칭'].dropna().map(norm_text))
    for nm in df_list['제품명'].dropna().map(norm_text):
        unique_terms.update(extract_paren_terms_refined(nm))
    pd.DataFrame({"term": sorted(t for t in unique_terms if t)}).to_csv(
        Path(out_dir)/"proper_nouns_dictionary.txt", index=False, header=False, encoding="utf-8-sig"
    )

    # 5-4) 코드→대표명 매핑들
    code2label = syn_df[['substance_code','preferred_label_ko','preferred_label_en','atc_codes']].copy()
    code2label['representative_label'] = code2label.apply(
        lambda r: r['preferred_label_ko'] or r['preferred_label_en'] or "", axis=1
    )
    code2label.to_csv(Path(out_dir)/"code_to_label_substance.csv", index=False, encoding="utf-8-sig")

    prod_map = df_list[['제품코드','제품명','업체명']].drop_duplicates()
    prod_map.to_csv(Path(out_dir)/"code_to_label_product_hira9.csv", index=False, encoding="utf-8-sig")

    atc_map = atc_small.drop_duplicates()
    atc_map.to_csv(Path(out_dir)/"code_to_label_atc.csv", index=False, encoding="utf-8-sig")

    # 콘솔 요약
    print(f"[OK] clusters(substance): {syn_df['substance_code'].nunique():,}")
    print(f"[OK] outputs @ {out_dir}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--list_xlsx", required=True, help="HIRA 9자리 제품코드 포함 약제목록 엑셀")
    ap.add_argument("--atc_csv",   required=True, help="ATC 매핑 CSV (제품코드, ATC코드, ATC코드 명칭)")
    ap.add_argument("--out_dir",   default="out", help="결과물 저장 폴더")
    args = ap.parse_args()
    build_synonyms(args.list_xlsx, args.atc_csv, args.out_dir)
