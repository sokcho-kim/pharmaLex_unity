# -*- coding: utf-8 -*-
"""
build_yakje_total.py  — 약제종합 재구축 파이프라인

입력(예시)
  --src-price   "약제급여목록및급여상한금액표_(2025.8.1.)....xlsx"   # 가격표/급여목록
  --src-prod    "의약품등제품정보목록.xlsx"                           # 제품 마스터
  --src-master  "약제종합.csv"                                        # (있으면) 기존 약제종합
  --src-sub     "건강보험심사평가원_약가마스터_의약품주성분_20241014.csv" # 선택
  --src-atc     "건강보험심사평가원_ATC코드 매핑 목록_20240630.csv"      # 선택

산출
  out/약제종합_REBUILT.csv, out/약제종합_REBUILT.xlsx
  QA 결측/중복/열이동 의심 리포트 동시 생성
"""

import re, csv, argparse
import pandas as pd
from pathlib import Path
from collections import Counter

# ---------- 유틸: 안전 로더 ----------
def read_smart(path, dtype=str):
    p=str(path)
    if p.lower().endswith((".xlsx",".xlsm",".xls")):
        try:
            return pd.read_excel(p, dtype=dtype, engine="openpyxl")
        except Exception:
            return pd.read_excel(p, dtype=dtype)  # 엔진 자동
    last=None
    for enc in ("utf-8-sig","cp949","euc-kr","utf-16","utf-8","latin1"):
        try:
            return pd.read_csv(p, dtype=dtype, encoding=enc, keep_default_na=False, na_values=[])
        except Exception as e:
            last=e
    raise last

# ---------- 컬럼 매핑(느슨한 매칭) ----------
def pick(df, candidates):
    cols={c: c for c in df.columns}
    norm=lambda s: re.sub(r'\s+', '', str(s)).lower()
    normcols={norm(c): c for c in df.columns}
    for cand in candidates:
        if cand in df.columns: return cand
    for cand in candidates:
        nc=norm(cand)
        if nc in normcols: return normcols[nc]
    # 부분일치
    for c in df.columns:
        if any(norm(cand) in norm(c) for cand in candidates):
            return c
    return None

# ---------- 문자열/단위 정규화(이전 스크립트 내장판) ----------
BRMAP = str.maketrans({"（":"(", "［":"(", "｛":"(", "{":"(", "[":"(", "【":"(", "〔":"(",
                       "）":")", "］":")", "｝":")", "}":")", "]":")", "】":")", "〕":")"})
def unify_brackets(s): return (s or "").translate(BRMAP)
def norm_spaces(s):
    s=(s or "").replace("\ufeff","")
    s=re.sub(r'[\u3000\s]+',' ', s)
    return s.replace("→","->").replace("ᆞ","·").replace("ㆍ","·").replace("，",",").strip()

IU=r'(?:IU|I\.?U\.?|I\s?U|KIU|K\.?I\.?U\.?|K\s?I\s?U|kIU|k\.?I\.?U\.?|k\s?I\s?U|U)'
def unit_regex(keep_percent:bool):
    units=[r"mg",r"g",r"mcg",r"μg",r"㎍",r"㎎",r"L",r"ℓ",r"mL",r"ml",IU,
           r"밀리그램",r"밀리그람",r"그램",r"그람",r"마이크로그램",r"리터",r"밀리리터"]
    if not keep_percent: units.append(r"%")
    return r"(?:%s)" % "|".join(units)

PACK_WORDS={"병","회","스틱","패치","패취","vial","앰플","포","회분","펌프","스프레이","프리필드","백","bag"}
PACK=r'(?:정|캡슐|캅셀|병|회|스틱|패치|패취|vial|앰플|포|mL|ml|회분|펌프|스프레이|백|bag)'

def drop_pack_tokens(text):
    if not isinstance(text,str) or not text.strip(): return text
    pat=r'(?:(?<=^)|(?<=[\s,;/·ᆞㆍ\(\)-]))(?:'+"|".join(map(re.escape,PACK_WORDS))+r')(?:(?=$)|(?=[\s,;/·ᆞㆍ\(\)-]))'
    out=re.sub(pat,' ',text,flags=re.IGNORECASE)
    return re.sub(r'\s{2,}',' ',out).strip(' ,;/·ᆞㆍ-()')

def drop_dose_anywhere(text, keep_percent):
    if not isinstance(text,str): return text
    U=unit_regex(keep_percent)
    out=re.sub(rf'\d+(?:\.\d+)?\s*{U}','',text,flags=re.IGNORECASE)
    out=re.sub(r'\s*,\s*,+',', ',out).strip(' ,-/')
    return re.sub(r'\s{2,}',' ',out)

def drop_trailing_dose(text, keep_percent):
    if not isinstance(text,str): return text
    U=unit_regex(keep_percent)
    DOSE1=rf'\d+(?:\.\d+)?\s*{U}'
    DOSE2=rf'\d+\s*/\s*\d+\s*(?:{U}|{PACK})?'
    TAIL=rf'(?:{DOSE1}(?:\s*/\s*\d+(?:\.\d+)?\s*(?:{PACK}|{U}))?|{DOSE2}|{DOSE1}|(?:\d+\s*{PACK}))'
    out,prev=text,None
    while prev!=out:
        prev=out
        out=re.sub(rf'(?:{TAIL})+\s*$', '', out, flags=re.IGNORECASE)
    out=re.sub(r'\d+\s*주$','',out)
    return out.rstrip(' _,-/')

def drop_orphan_units(text, keep_percent):
    if not isinstance(text,str) or not text.strip(): return text
    U=[r"mg",r"g",r"mcg",r"μg",r"㎍",r"㎎",r"L",r"ℓ",r"mL",r"ml",
       r"IU",r"I\.?U\.?",r"I\s?U",r"KIU",r"K\.?I\.?U\.?",r"K\s?I\s?U",r"kIU",r"k\.?I\.?U\.?",r"k\s?I\s?U",r"U",
       r"밀리그램",r"밀리그람",r"그램",r"그람",r"마이크로그램",r"리터",r"밀리리터"]
    if not keep_percent: U.append(r"%")
    pat=r'(?:(?<=^)|(?<=[\s,;/·ᆞㆍ\(\)-]))(?:'+'|'.join(U)+r')(?:(?=$)|(?=[\s,;/·ᆞㆍ\(\)-]))'
    out=re.sub(pat,' ',text,flags=re.IGNORECASE)
    return re.sub(r'\s{2,}',' ',out).strip(' ,;/·ᆞㆍ-()')

def outer_paren_segments(text):
    if not isinstance(text,str) or not text: return []
    segs,buf,depth=[],[],0
    for ch in text:
        if ch=='(':
            if depth>0: buf.append(ch)
            depth+=1; continue
        if ch==')':
            depth-=1
            if depth<0: depth=0
            if depth==0:
                seg=''.join(buf).strip()
                if seg: segs.append(seg)
                buf=[]
            else: buf.append(ch)
            continue
        if depth>0: buf.append(ch)
    return segs

def split_outside_parens(text):
    if not isinstance(text,str) or not text: return []
    parts,buf,depth=[],[],0
    for ch in text:
        if ch=='(':
            depth+=1; buf.append(ch); continue
        if ch==')':
            if depth>0: depth-=1
            buf.append(ch); continue
        if ch in [',','/','·','ᆞ','ㆍ'] and depth==0:
            tok=''.join(buf).strip()
            if tok: parts.append(tok)
            buf=[]
        else: buf.append(ch)
    tok=''.join(buf).strip()
    if tok: parts.append(tok)
    return parts

DOSAGE_FORMS={"정","서방정","발포정","츄어블정","캡슐","캅셀","연질캡슐","경질캡슐",
              "현탁","현탁용분말","시럽","시럽용","시럽제","점안","점안액","주","주사","주사용",
              "크림","겔","겔제","액","액제","스프레이","패치","패취","좌제","분무",
              "흡입","흡입용분말","분말","용액","현탁액","농축액","시럽용현탁용분말","프리필드"}
def has_form(t): 
    z=(t or "").replace(' ','')
    return any(f in z for f in DOSAGE_FORMS)

def is_pure_dose(tok, keep_percent):
    U=unit_regex(keep_percent)
    return bool(re.fullmatch(rf'\(?\s*\d+(?:\.\d+)?\s*(?:{U}|{PACK})(?:\s*/\s*\d+(?:\.\d+)?\s*(?:{U}|{PACK}))?\s*\)?', tok or "", flags=re.IGNORECASE))
def is_ratio_only(s):
    if not isinstance(s,str) or not s.strip(): return False
    t=s.strip()
    if t.startswith('(') and t.endswith(')'): t=t[1:-1].strip()
    return bool(re.fullmatch(r'[0-9\.\s:>\-~→/]+', t)) and not re.search(r'[A-Za-z가-힣]', t)

def extract_pumyeong(raw, keep_percent):
    if not isinstance(raw,str) or not raw.strip(): return ""
    s=norm_spaces(unify_brackets(raw))
    base=s.split('(',1)[0]
    base=drop_trailing_dose(base, keep_percent)
    base=drop_dose_anywhere(base, keep_percent)
    base=drop_orphan_units(base, keep_percent)
    return base

def components_from_name(raw, keep_percent):
    if not isinstance(raw,str) or not raw.strip(): return ""
    s=norm_spaces(unify_brackets(raw))
    comps=[]
    for seg in outer_paren_segments(s):
        if not seg or seg.startswith("수출명"): continue
        if is_ratio_only(seg): continue
        seg=drop_dose_anywhere(seg, keep_percent)
        seg=drop_pack_tokens(seg)
        seg=drop_orphan_units(seg, keep_percent).strip(' _,-/')
        if not seg or is_pure_dose(seg, keep_percent): continue
        for tok in split_outside_parens(seg):
            t=tok.strip()
            if not t or is_pure_dose(t, keep_percent): continue
            if has_form(t):
                t2=re.sub(r'^(시럽용|주사용|점안|흡입용|경구용|좌제용|현탁용|외용|주사)\s*','',t)
                if not t2 or has_form(t2): continue
                t=t2
            t=re.sub(r'\((?:\s*[0-9\.\s:>\-~→/]+\s*)\)','',t).strip()
            t=drop_orphan_units(t, keep_percent)
            if t: comps.append(t)
    seen,out=set(),[]
    for t in comps:
        if t not in seen:
            seen.add(t); out.append(t)
    return '·'.join(out) if out else ""

def normalize_general(gen, keep_percent):
    if not isinstance(gen,str) or not gen.strip(): return ""
    s=norm_spaces(unify_brackets(gen))
    s=re.sub(r'\((?:\s*[0-9\.\s:>\-~→/]+\s*)\)','',s)
    s=drop_dose_anywhere(s, keep_percent)
    s=drop_pack_tokens(s)
    s=drop_orphan_units(s, keep_percent)
    parts=[p.strip() for p in re.split(r'\s*[,/]\s*|[·ᆞㆍ]', s) if p.strip()]
    parts2=[]
    for t in parts:
        if has_form(t) or is_ratio_only(t) or is_pure_dose(t, keep_percent): continue
        parts2.append(t)
    seen,out=set(),[]
    for t in parts2:
        if t not in seen:
            seen.add(t); out.append(t)
    return '·'.join(out) if out else ""

def english_only(gen):
    if not isinstance(gen,str) or not gen.strip(): return ""
    if re.search(r'[A-Za-z]', gen) and not re.search(r'[가-힣]', gen):
        parts=[p.strip().lower() for p in re.split(r'[,/·ᆞㆍ]+', gen) if p.strip()]
        return '·'.join(parts)
    return ""

def is_blank(x):
    s=str(x) if x is not None else ""
    return s.strip()=="" or s.strip().lower() in {"nan","none","null","-","없음"}

# ---------- 통합 빌드 ----------
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--src-price", help="급여목록/상한금액표 xlsx", required=False)
    ap.add_argument("--src-prod",  help="의약품등제품정보목록 xlsx", required=False)
    ap.add_argument("--src-master",help="기존 약제종합 csv/xlsx", required=False)
    ap.add_argument("--src-sub",   help="주성분 마스터 csv", required=False)
    ap.add_argument("--src-atc",   help="ATC 매핑 csv", required=False)

    ap.add_argument("--keep-percent", action="store_true")
    ap.add_argument("--group-by", default="품목기준코드", help="병합키(기본: 품목기준코드)")
    ap.add_argument("--expect-rows", type=int, default=None)

    ap.add_argument("--out-csv",  default="out/약제종합_REBUILT.csv")
    ap.add_argument("--out-xlsx", default="out/약제종합_REBUILT.xlsx")
    args=ap.parse_args()

    keep_percent=args.keep_percent

    # 0) 읽기
    dfs=[]
    if args.src_master: dfs.append(("master", read_smart(args.src_master)))
    if args.src_price:  dfs.append(("price",  read_smart(args.src_price)))
    if args.src_prod:   dfs.append(("prod",   read_smart(args.src_prod)))
    if not dfs: raise SystemExit("[ERR] 최소 하나의 소스가 필요합니다.")

    # 1) 표준 스키마 변환
    rows_before=0
    buckets=[]
    for tag,df in dfs:
        rows_before+=len(df)
        # 후보 컬럼 매핑
        c_item = pick(df, ["품목기준코드","제품코드","품목코드","HIRA제품코드","item_code"])
        c_prod = pick(df, ["제품코드","품목기준코드","product_code"])
        c_name = pick(df, ["제품명","품명","품목명","제품(한글명)","제품명(한글)","product_name"])
        c_gen  = pick(df, ["일반명","성분명","주성분명","영문성분명","일반명칭","generic","general_name"])
        c_comp = pick(df, ["주성분코드","주성분코드값","성분코드","substance_code"])
        c_form = pick(df, ["제형","성상","제형명","투여제형","dosage_form"])
        c_route= pick(df, ["투여경로","투여경로명","route"])
        c_amt  = pick(df, ["함량","규격","strength","dose"])
        c_unit = pick(df, ["단위","unit"])
        c_co   = pick(df, ["업체명","제조회사","회사명","사","회사","manufacturer","company"])

        std = pd.DataFrame({
            "source": tag,
            "item_code": df.get(c_item, ""),
            "product_code": df.get(c_prod, ""),
            "product_name_raw": df.get(c_name, ""),
            "general_name_raw": df.get(c_gen, ""),
            "substance_code": df.get(c_comp, ""),
            "form": df.get(c_form, ""),
            "route": df.get(c_route, ""),
            "amount": df.get(c_amt, ""),
            "unit": df.get(c_unit, ""),
            "company": df.get(c_co, "")
        }, dtype=str)
        buckets.append(std)

    base = pd.concat(buckets, ignore_index=True)

    # 2) 키/텍스트 정리
    for col in ["item_code","product_code","product_name_raw","general_name_raw","company","form","route","amount","unit","substance_code"]:
        base[col]=base[col].astype(str).fillna("").map(lambda x: norm_spaces(unify_brackets(x)))
    # item_code가 비면 product_code로 대체(최소 하나는 갖게)
    base["item_code"] = base.apply(lambda r: r["item_code"] if not is_blank(r["item_code"]) else r["product_code"], axis=1)

    # 3) 제품명 보강(display_name + 출처 라벨)
    def derive_display(r):
        # ① 소스에서 제품명
        for s in ["master","price","prod"]:
            cand = base_name_by_source.get((r.name, s), "")
        # 위는 row index 기반이라 불편 → 간단히 아래로:
        return ""

    # 우선순위 기반 보강
    def pick_name(row):
        # ORIGINAL
        for src in ("master","price","prod"):
            # 해당 소스에서 온 레코드들 중 동일 키의 제품명을 본다
            pass

    # 간단/효율적으로: 같은 item_code 그룹에서 우선순위 소스의 비공백 제품명 first
    order = ["master","price","prod"]
    def group_pick_name(g):
        # 소스 우선순위별로 제품명 후보 수집
        for src in order:
            vals=[v for v in g.loc[g["source"]==src,"product_name_raw"].tolist() if not is_blank(v)]
            if vals: return vals[0],"ORIGINAL"
        # MAP: 다른 소스의 제품명
        vals=[v for v in g["product_name_raw"].tolist() if not is_blank(v)]
        if vals: return vals[0],"MAP"
        # DERIVED: 일반명 정규화 + 제형 키워드
        gn = normalize_general("".join([v for v in g["general_name_raw"].tolist() if v]) , keep_percent)
        fm = next((v for v in g["form"].tolist() if not is_blank(v)), "")
        if gn:
            label = gn
            if fm:
                # 핵심 제형만 남기기
                if any(f in fm for f in ["정","캡슐","주","시럽","점안","연질","겔","크림"]):
                    label += (" " + re.sub(r'.*(정|캡슐|주|시럽|점안|연질|겔|크림).*', r'\1', fm))
            return label,"DERIVED"
        return "", "BLOCK"

    picked = base.groupby("item_code", dropna=False).apply(lambda g: pd.Series(group_pick_name(g), index=["display_name","name_source"])).reset_index()
    base = base.merge(picked, on="item_code", how="left")

    # 4) 최종 표기명: display_name이 비면 BLOCK → 보고
    base["display_name"] = base["display_name"].fillna("")
    # 품명_정제/성분/영문 성분 생성(대표행 기준으로)
    rep = base.groupby("item_code", as_index=False).agg({
        "product_code":"first","company":"first","form":"first","route":"first","amount":"first","unit":"first",
        "substance_code":"first","display_name":"first","name_source":"first",
        "product_name_raw": "first", "general_name_raw":"first"
    })
    # 정제
    rep["품명_정제"] = rep["display_name"].apply(lambda x: extract_pumyeong(x, keep_percent))
    rep["성분_정제"] = rep.apply(lambda r: components_from_name(r["product_name_raw"], keep_percent), axis=1)
    rep["성분_EN"]  = rep["general_name_raw"].apply(english_only)

    # 성분 보간(b→a): 동일 주성분코드 그룹에서 일반명 정규화 최빈 → 성분_정제 보완
    def norm_gen(series):
        arr=[normalize_general(x, keep_percent) for x in series.tolist() if x]
        arr=[a for a in arr if a]
        return Counter(arr).most_common(1)[0][0] if arr else ""
    gen_rep = base.groupby("substance_code", as_index=False).agg(gen_norm=("general_name_raw", norm_gen))
    rep = rep.merge(gen_rep, on="substance_code", how="left")
    rep["성분_정제"] = rep.apply(lambda r: (r["성분_정제"] if r["성분_정제"] else r["gen_norm"]), axis=1).fillna("")
    rep.drop(columns=["gen_norm"], inplace=True)

    # 티씰류 다성분 병합: group-by 인자 사용
    key = args.group_by or "품목기준코드"
    if key not in rep.columns:
        # key가 item_code 별칭인 경우 맞추기
        if key == "품목기준코드": rep[key]=rep["item_code"]
        else: rep[key]=""
    def merge_tokens(series):
        toks=[]
        for v in series:
            if not isinstance(v,str) or not v.strip(): continue
            for t in re.split(r'[·,]+', v):
                t=t.strip()
                if t: toks.append(t)
        seen,out=set(),[]
        for t in toks:
            if t not in seen:
                seen.add(t); out.append(t)
        return '·'.join(out)
    rep2 = rep.groupby(key, as_index=False).agg({
        "item_code":"first","product_code":"first","display_name":"first","name_source":"first",
        "company":"first","form":"first","route":"first","amount":"first","unit":"first","substance_code":"first",
        "품명_정제":"first", "성분_정제":merge_tokens, "성분_EN":merge_tokens,
        "product_name_raw":"first","general_name_raw":"first"
    })

    # QA
    outdir=Path(args.out_csv).parent
    outdir.mkdir(parents=True, exist_ok=True)
    # 결측/블록
    missing = rep2[rep2["display_name"].map(is_blank)]
    missing.to_csv(outdir/"QA_missing_display_name.csv", index=False, encoding="utf-8-sig")
    # 행수 검증
    print(f"[QA] 입력 총행수(소스 합): {rows_before:,}  | 통합 후: {len(rep2):,}")
    if args.expect-rows and len(rep2)!=args.expect_rows:
        print(f"[WARN] 출력 행수 {len(rep2):,} != 기대 {args.expect_rows:,}")

    # 저장
    rep2.to_csv(args.out_csv, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_ALL)
    try:
        with pd.ExcelWriter(args.out_xlsx, engine="openpyxl") as w:
            rep2.astype(str).to_excel(w, index=False, sheet_name="yakje")
        print(f"[OK] saved CSV → {args.out_csv} | XLSX → {args.out_xlsx}")
    except Exception as e:
        print(f"[OK] saved CSV → {args.out_csv} | [WARN] XLSX 실패: {e} (pip install openpyxl)")
    # 요약
    print(rep2[["item_code","display_name","name_source","품명_정제","성분_정제","성분_EN"]].head(10).to_string(index=False))

if __name__=="__main__":
    main()


# python .\build_yakje_total.py `
#   --src-price ".\약제급여목록및급여상한금액표_(2025.8.1.)(21,953)_공개용_7.31. 1부.xlsx" `
#   --src-prod  ".\의약품등제품정보목록.xlsx" `
#   --src-master ".\약제종합.csv" `
#   --out-csv  ".\out\약제종합_REBUILT.csv" `
#   --out-xlsx ".\out\약제종합_REBUILT.xlsx" `
#   --keep-percent `
#   --group-by "품목기준코드" `
#   --expect-rows 54717

