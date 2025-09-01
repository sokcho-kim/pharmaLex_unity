# -*- coding: utf-8 -*-
"""
build_snapshot_yakje.py

목표: '약제급여목록및급여상한금액표_(YYYY.M.D)...xlsx'를 "헤더/품목" 구조로 올바르게 파싱하여
      실제 품목(숫자 제품코드) 1행당 1레코드의 스냅샷(예: 21,953행)을 생성.
보강:
  - 헤더 행(비-숫자 제품코드)의 텍스트를 아래 품목들에 'header_ctx'로 전파(영문 일반명/강도 힌트)
  - ATC 매핑 파일은 제품코드 기준으로 유니크 병합(행 증가 방지)
  - 성분/품명 정규화(괄호, 단위, 비율-only, '백(bag)', KIU/IU/L·ℓ 등)

입력:
  --snapshot  약제급여목록 스냅샷 xlsx (예: "(2025.8.1.)(21,953)..." 파일)
  --atc       건강보험심사평가원_ATC코드 매핑 목록_YYYYMMDD.csv

출력:
  --out-csv   CSV
  --out-xlsx  XLSX (검수용)

사용 예:
  python build_snapshot_yakje.py \
    --snapshot "약제급여목록및급여상한금액표_(2025.8.1.)(21,953)_공개용_7.31. 1부.xlsx" \
    --atc "건강보험심사평가원_ATC코드 매핑 목록_20240630.csv" \
    --out-csv "./out/약제종합_SNAPSHOT_20250801.csv" \
    --out-xlsx "./out/약제종합_SNAPSHOT_20250801.xlsx"
"""

import re, csv, argparse, pandas as pd
from pathlib import Path

# ---------- 텍스트 정규화(괄호/단위/포장/비율 처리) ----------
BRMAP = str.maketrans({
    "（":"(", "［":"(", "｛":"(", "{":"(", "[":"(", "【":"(", "〔":"(",
    "）":")", "］":")", "｝":")", "}":")", "]":")", "】":")", "〕":")"
})
def unify_brackets(s): return (s or "").translate(BRMAP)
def norm_spaces(s):
    s=(s or "").replace("\ufeff",""); s=re.sub(r'[\u3000\s]+',' ', s)
    return s.replace("→","->").replace("ᆞ","·").replace("ㆍ","·").replace("，",",").strip()

IU=r'(?:IU|I\.?U\.?|I\s?U|KIU|K\.?I\.?U\.?|K\s?I\s?U|kIU|k\.?I\.?U\.?|k\s?I\s?U|U)'
def unit_regex():
    units=[r"mg",r"g",r"mcg",r"μg",r"㎍",r"㎎",r"L",r"ℓ",r"mL",r"ml",IU,
           r"밀리그램",r"밀리그람",r"그램",r"그람",r"마이크로그램",r"리터",r"밀리리터",r"%"]
    return r"(?:%s)" % "|".join(units)

PACK_WORDS={"병","회","스틱","패치","패취","vial","앰플","포","회분","펌프","스프레이","프리필드","백","bag"}
PACK=r'(?:정|캡슐|캅셀|병|회|스틱|패치|패취|vial|앰플|포|mL|ml|회분|펌프|스프레이|백|bag)'

def drop_pack_tokens(text):
    if not isinstance(text,str) or not text.strip(): return text
    pat=r'(?:(?<=^)|(?<=[\s,;/·ᆞㆍ\(\)-]))(?:'+"|".join(map(re.escape,PACK_WORDS))+r')(?:(?=$)|(?=[\s,;/·ᆞㆍ\(\)-]))'
    out=re.sub(pat,' ',text,flags=re.IGNORECASE)
    return re.sub(r'\s{2,}',' ',out).strip(' ,;/·ᆞㆍ-()')

def drop_dose_anywhere(text):
    if not isinstance(text,str): return text
    U=unit_regex()
    out=re.sub(rf'\d+(?:\.\d+)?\s*{U}','',text,flags=re.IGNORECASE)
    out=re.sub(r'\s*,\s*,+',', ',out).strip(' ,-/')
    return re.sub(r'\s{2,}',' ',out)

def drop_trailing_dose(text):
    if not isinstance(text,str): return text
    U=unit_regex()
    DOSE1=rf'\d+(?:\.\d+)?\s*{U}'
    DOSE2=rf'\d+\s*/\s*\d+\s*(?:{U}|{PACK})?'
    TAIL=rf'(?:{DOSE1}(?:\s*/\s*\d+(?:\.\d+)?\s*(?:{PACK}|{U}))?|{DOSE2}|{DOSE1}|(?:\d+\s*{PACK}))'
    out,prev=text,None
    while prev!=out:
        prev=out
        out=re.sub(rf'(?:{TAIL})+\s*$', '', out, flags=re.IGNORECASE)
    out=re.sub(r'\d+\s*주$','',out)
    return out.rstrip(' _,-/')

def drop_orphan_units(text):
    if not isinstance(text,str) or not text.strip(): return text
    U=[r"mg",r"g",r"mcg",r"μg",r"㎍",r"㎎",r"L",r"ℓ",r"mL",r"ml",
       r"IU",r"I\.?U\.?",r"I\s?U",r"KIU",r"K\.?I\.?U\.?",r"K\s?I\s?U",r"kIU",r"k\.?I\.?U\.?",r"k\s?I\s?U",r"U",
       r"밀리그램",r"밀리그람",r"그램",r"그람",r"마이크로그램",r"리터",r"밀리리터",r"%"]
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

def is_pure_dose(tok):
    U=unit_regex()
    return bool(re.fullmatch(rf'\(?\s*\d+(?:\.\d+)?\s*(?:{U}|{PACK})(?:\s*/\s*\d+(?:\.\d+)?\s*(?:{U}|{PACK}))?\s*\)?', tok or "", flags=re.IGNORECASE))
def is_ratio_only(s):
    if not isinstance(s,str) or not s.strip(): return False
    t=s.strip()
    if t.startswith('(') and t.endswith(')'): t=t[1:-1].strip()
    return bool(re.fullmatch(r'[0-9\.\s:>\-~→/]+', t)) and not re.search(r'[A-Za-z가-힣]', t)

def extract_pumyeong(raw):
    if not isinstance(raw,str) or not raw.strip(): return ""
    s=norm_spaces(unify_brackets(raw))
    base=s.split('(',1)[0]
    base=drop_trailing_dose(base)
    base=drop_dose_anywhere(base)
    base=drop_orphan_units(base)
    return base

def components_from_name(raw):
    if not isinstance(raw,str) or not raw.strip(): return ""
    s=norm_spaces(unify_brackets(raw))
    comps=[]
    for seg in outer_paren_segments(s):
        if not seg or seg.startswith("수출명"): continue
        if is_ratio_only(seg): continue
        seg=drop_dose_anywhere(seg)
        seg=drop_pack_tokens(seg)
        seg=drop_orphan_units(seg).strip(' _,-/')
        if not seg or is_pure_dose(seg): continue
        for tok in split_outside_parens(seg):
            t=tok.strip()
            if not t or is_pure_dose(t): continue
            if has_form(t):
                t2=re.sub(r'^(시럽용|주사용|점안|흡입용|경구용|좌제용|현탁용|외용|주사)\s*','',t)
                if not t2 or has_form(t2): continue
                t=t2
            t=re.sub(r'\((?:\s*[0-9\.\s:>\-~→/]+\s*)\)','',t).strip()
            t=drop_orphan_units(t)
            if t: comps.append(t)
    # 순서 유지 유니크
    seen,out=set(),[]
    for t in comps:
        if t not in seen:
            seen.add(t); out.append(t)
    return '·'.join(out) if out else ""

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

# ---------- 메인 ----------
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True, help="약제급여목록 스냅샷 xlsx")
    ap.add_argument("--atc", required=True, help="ATC 매핑 csv (cp949 등)")
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-xlsx", required=True)
    args=ap.parse_args()

    # 1) 스냅샷 로드 + 헤더/품목 분리 + 헤더 전파
    snap = pd.read_excel(args.snapshot, dtype=str)
    needed = ["연번","투여","분류","주성분코드","제품코드","제품명","업체명","규격","단위","상한금액","전일","비고"]
    for c in needed:
        if c not in snap.columns:
            raise SystemExit(f"[ERR] 스냅샷에 '{c}' 컬럼 없음. 실제: {list(snap.columns)}")
    rows=[]; ctx=None
    for _,r in snap.iterrows():
        code=str(r["제품코드"])
        if re.fullmatch(r'\d{6,}', code):
            rr=r.to_dict()
            rr["header_ctx"]=ctx  # 영문 일반명/강도 헤더
            rows.append(rr)
        else:
            # 헤더 갱신
            ctx = norm_spaces(unify_brackets(code))
    snap2 = pd.DataFrame(rows)
    # 기대 행수 체크(파일명 표기와 일치해야 함)
    print(f"[INFO] snapshot parsed → {len(snap2):,} rows (품목)")

    # 2) ATC 매핑(제품코드 조인, 중복은 병합)
    # 인코딩 탐색
    atc=None
    for enc in ("utf-8-sig","cp949","euc-kr","utf-16","latin1"):
        try:
            atc=pd.read_csv(args.atc, encoding=enc, dtype=str)
            break
        except Exception:
            continue
    if atc is None:
        raise SystemExit("[ERR] ATC csv 읽기 실패(인코딩 확인)")
    for c in ["제품코드","ATC코드","ATC코드 명칭"]:
        if c not in atc.columns:
            raise SystemExit(f"[ERR] ATC csv '{c}' 없음. 실제: {list(atc.columns)}")

    atc_g = atc.groupby("제품코드", as_index=False).agg({
        "ATC코드": merge_tokens,
        "ATC코드 명칭": merge_tokens
    })
    df = snap2.merge(atc_g, on="제품코드", how="left")

    # 3) 텍스트 정제(품명/성분)
    df["품명_정제"] = df["제품명"].fillna("").map(extract_pumyeong)
    # 성분은 제품명 기반 + (비었을 때) 헤더 컨텍스트에서 보강
    comp_from_name = df["제품명"].fillna("").map(components_from_name)
    comp_from_hdr  = df["header_ctx"].fillna("").map(components_from_name)
    df["성분_정제"] = comp_from_name
    df.loc[df["성분_정제"].eq(""), "성분_정제"] = comp_from_hdr

    # 4) 품목별 단일행 보장(혹시라도 ATC 조인에서 중복이 생겼을 때 안전장치)
    df = df.groupby("제품코드", as_index=False).agg({
        "연번":"first","투여":"first","분류":"first","주성분코드":"first","제품명":"first",
        "업체명":"first","규격":"first","단위":"first","상한금액":"first","전일":"first","비고":"first","header_ctx":"first",
        "ATC코드":merge_tokens,"ATC코드 명칭":merge_tokens,
        "품명_정제":"first","성분_정제":merge_tokens
    })

    # 5) QA
    def has_num_unit(s):
        return bool(re.search(rf'\d+(?:\.\d+)?\s*{unit_regex()}', str(s) or "", flags=re.IGNORECASE))
    bad_pum = df["품명_정제"].map(has_num_unit).sum()
    bad_comp = df["성분_정제"].map(has_num_unit).sum()
    empty_name = df["제품명"].isna().sum() + (df["제품명"].astype(str).str.strip()=="").sum()

    print(f"[QA] 최종 행수: {len(df):,} (스냅샷 품목 기대와 같아야 함)")
    print(f"[QA] 제품명 빈값: {empty_name:,}  | 품명_정제에 숫자+단위 잔존: {bad_pum:,}  | 성분_정제에 숫자+단위 잔존: {bad_comp:,}")

    # 6) 저장
    out_csv, out_xlsx = Path(args.out_csv), Path(args.out_xlsx)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_ALL)
    try:
        with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
            df.astype(str).to_excel(w, index=False, sheet_name="snapshot")
        print(f"[OK] saved → {out_csv} / {out_xlsx}")
    except Exception as e:
        print(f"[OK] saved → {out_csv}  | [WARN] XLSX 실패: {e} (pip install openpyxl)")
if __name__=="__main__":
    main()
