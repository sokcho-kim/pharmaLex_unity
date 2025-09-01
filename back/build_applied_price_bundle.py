# -*- coding: utf-8 -*-
"""
build_applied_price_bundle.py

입력(기본값은 형님이 주신 경로)
  --applied  "C:\\Jimin\\pharmaLex_unity\\data\\20220901_20250901 적용약가파일_8.28.수정.xlsx"
  --atc      "C:\\Jimin\\pharmaLex_unity\\data\\건강보험심사평가원_ATC코드 매핑 목록_20240630.csv"
  --subs     "C:\\Jimin\\pharmaLex_unity\\data\\건강보험심사평가원_약가마스터_의약품주성분_20241014.csv"
  --outdir   출력 폴더 (기본: .\\out)

산출
  01_applied_price_enriched.csv        ← (적용약가 + ATC + 성분) 기준 테이블
  02_yakjejonghap_for_syn.csv          ← 유의어 사전용 정제 테이블
  03_rules_synonyms.txt                ← synonyms 규칙 (OpenSearch/ES 호환)
  03_rules_proper_nouns.txt            ← proper nouns 사전

원칙
- 기준은 적용약가. ATC/주성분은 선집계 후 좌조인(행수 불변).
"""

import re, csv, argparse, os, math
import pandas as pd
from pathlib import Path
from collections import Counter

# ---------------- 공통 헬퍼 ----------------
def to_text(x) -> str:
    """NaN/None/숫자 섞임 방지용 안전 캐스팅"""
    if x is None:
        return ""
    if isinstance(x, float):
        if math.isnan(x):
            return ""
    s = str(x).strip()
    if s.lower() in {"nan", "none", "null"}:
        return ""
    return s

# ---------------- I/O helpers ----------------
def read_excel_all_sheets(path: str, dtype=str) -> pd.DataFrame:
    """엑셀의 모든 시트 concat (헤더 동일 가정, 없으면 가능한 열만 사용)"""
    xl = pd.read_excel(path, dtype=dtype, sheet_name=None, engine="openpyxl")
    frames = []
    for name, df in xl.items():
        if not isinstance(df, pd.DataFrame):
            continue
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    # 컬럼 교집합만 남겨 정렬
    cols = list(frames[0].columns)
    return pd.concat([f.reindex(columns=cols) for f in frames], ignore_index=True)

def read_csv_any(path: str, dtype=str) -> pd.DataFrame:
    last = None
    for enc in ("utf-8-sig","cp949","euc-kr","utf-16","utf-8","latin1"):
        try:
            return pd.read_csv(path, dtype=dtype, encoding=enc, keep_default_na=False, na_values=[])
        except Exception as e:
            last = e
            continue
    raise last

def write_csv(df: pd.DataFrame, path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_ALL)

# ---------------- column matcher ----------------
def pick(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """느슨한 매칭(공백/대소문자 무시, 부분일치 허용)"""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    cols = list(df.columns)
    norm = lambda s: re.sub(r'\s+', '', str(s)).lower()
    normcols = {norm(c): c for c in cols}
    for cand in candidates:
        if cand in cols: return cand
    for cand in candidates:
        nc = norm(cand)
        if nc in normcols: return normcols[nc]
    for c in cols:
        if any(re.sub(r'\s+','',cand).lower() in norm(c) for cand in candidates):
            return c
    return None

# ---------------- text normalize utils ----------------
BRMAP = str.maketrans({
    "（":"(", "［":"(", "｛":"(", "{":"(", "[":"(", "【":"(", "〔":"(",
    "）":")", "］":")", "｝":")", "}":")", "]":")", "】":")", "〔":")", "〕":")"
})
def unify_brackets(s:str) -> str: return (s or "").translate(BRMAP)
def norm_spaces(s:str) -> str:
    s=(s or "").replace("\ufeff","")
    s=re.sub(r'[\u3000\s]+',' ', s)
    return s.replace("→","->").replace("ᆞ","·").replace("ㆍ","·").replace("，",",").strip()

IU = r'(?:IU|I\.?U\.?|I\s?U|KIU|K\.?I\.?U\.?|K\s?I\s?U|kIU|k\.?I\.?U\.?|k\s?I\s?U|U)'
def unit_regex():
    units=[r"mg",r"g",r"mcg",r"μg",r"㎍",r"㎎",r"L",r"ℓ",r"mL",r"ml",IU,
           r"밀리그램",r"밀리그람",r"그램",r"그람",r"마이크로그램",r"리터",r"밀리리터",r"%"]
    return r"(?:%s)" % "|".join(units)

PACK_WORDS = {"병","회","스틱","패치","패취","vial","앰플","포","회분","펌프","스프레이","프리필드","백","bag"}
PACK = r'(?:정|캡슐|캅셀|병|회|스틱|패치|패취|vial|앰플|포|mL|ml|회분|펌프|스프레이|백|bag)'

def drop_pack_tokens(text:str) -> str:
    if not isinstance(text,str) or not text.strip(): return text
    pat=r'(?:(?<=^)|(?<=[\s,;/·ᆞㆍ\(\)-]))(?:'+"|".join(map(re.escape,PACK_WORDS))+r')(?:(?=$)|(?=[\s,;/·ᆞㆍ\(\)-]))'
    out=re.sub(pat,' ',text,flags=re.IGNORECASE)
    return re.sub(r'\s{2,}',' ',out).strip(' ,;/·ᆞㆍ-()')

def drop_dose_anywhere(text:str) -> str:
    if not isinstance(text,str): return text
    U=unit_regex()
    out=re.sub(rf'\d+(?:\.\d+)?\s*{U}','',text,flags=re.IGNORECASE)
    out=re.sub(r'\s*,\s*,+',', ',out).strip(' ,-/')
    return re.sub(r'\s{2,}',' ',out)

def drop_trailing_dose(text:str) -> str:
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

def drop_orphan_units(text:str) -> str:
    if not isinstance(text,str) or not text.strip(): return text
    U=[r"mg",r"g",r"mcg",r"μg",r"㎍",r"㎎",r"L",r"ℓ",r"mL",r"ml",
       r"IU",r"I\.?U\.?",r"I\s?U",r"KIU",r"K\.?I\.?U\.?",r"K\s?I\s?U",r"kIU",r"k\.?I\.?U\.?",r"k\s?I\s?U",r"U",
       r"밀리그램",r"밀리그람",r"그램",r"그람",r"마이크로그램",r"리터",r"밀리리터",r"%"]
    pat=r'(?:(?<=^)|(?<=[\s,;/·ᆞㆍ\(\)-]))(?:'+'|'.join(U)+r')(?:(?=$)|(?=[\s,;/·ᆞㆍ\(\)-]))'
    out=re.sub(pat,' ',text,flags=re.IGNORECASE)
    return re.sub(r'\s{2,}',' ',out).strip(' ,;/·ᆞㆍ-()')

def outer_paren_segments(text:str) -> list[str]:
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

def split_outside_parens(text:str) -> list[str]:
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
        else:
            buf.append(ch)
    tok=''.join(buf).strip()
    if tok: parts.append(tok)
    return parts

DOSAGE_FORMS={"정","서방정","발포정","츄어블정","캡슐","캅셀","연질캡슐","경질캡슐",
              "현탁","현탁용분말","시럽","시럽용","시럽제","점안","점안액","주","주사","주사용",
              "크림","겔","겔제","액","액제","스프레이","패치","패취","좌제","분무",
              "흡입","흡입용분말","분말","용액","현탁액","농축액","시럽용현탁용분말","프리필드"}
def has_form(t:str)->bool:
    z=(t or "").replace(' ','')
    return any(f in z for f in DOSAGE_FORMS)
def is_pure_dose(tok:str)->bool:
    U=unit_regex()
    return bool(re.fullmatch(rf'\(?\s*\d+(?:\.\d+)?\s*(?:{U}|{PACK})(?:\s*/\s*\d+(?:\.\d+)?\s*(?:{U}|{PACK}))?\s*\)?', tok or "", flags=re.IGNORECASE))
def is_ratio_only(s:str)->bool:
    if not isinstance(s,str) or not s.strip(): return False
    t=s.strip()
    if t.startswith('(') and t.endswith(')'): t=t[1:-1].strip()
    return bool(re.fullmatch(r'[0-9\.\s:>\-~→/]+', t)) and not re.search(r'[A-Za-z가-힣]', t)

def extract_pumyeong(raw:str) -> str:
    if not isinstance(raw,str) or not raw.strip(): return ""
    s=norm_spaces(unify_brackets(raw))
    base=s.split('(',1)[0]
    base=drop_trailing_dose(base)
    base=drop_dose_anywhere(base)
    base=drop_orphan_units(base)
    return base

def components_from_name(raw:str) -> str:
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
    seen,out=set(),[]
    for t in comps:
        if t not in seen:
            seen.add(t); out.append(t)
    return '·'.join(out) if out else ""

def normalize_general(gen:str) -> str:
    if not isinstance(gen,str) or not gen.strip(): return ""
    s=norm_spaces(unify_brackets(gen))
    s=re.sub(r'\((?:\s*[0-9\.\s:>\-~→/]+\s*)\)','',s)
    s=drop_dose_anywhere(s); s=drop_pack_tokens(s); s=drop_orphan_units(s)
    parts=[p.strip() for p in re.split(r'\s*[,/]\s*|[·ᆞㆍ]', s) if p.strip()]
    parts2=[]
    for t in parts:
        if has_form(t) or is_ratio_only(t) or is_pure_dose(t): continue
        parts2.append(t)
    seen,out=set(),[]
    for t in parts2:
        if t not in seen:
            seen.add(t); out.append(t)
    return '·'.join(out) if out else ""
def english_only(gen:str) -> str:
    if not isinstance(gen,str) or not gen.strip(): return ""
    if re.search(r'[A-Za-z]', gen) and not re.search(r'[가-힣]', gen):
        parts=[p.strip().lower() for p in re.split(r'[,/·ᆞㆍ]+', gen) if p.strip()]
        return '·'.join(parts)
    return ""

def merge_tokens(series: pd.Series) -> str:
    toks=[]
    for v in series:
        s = to_text(v)
        if not s: 
            continue
        for t in re.split(r'[·,]+', s):
            tt=t.strip()
            if tt: toks.append(tt)
    seen,out=set(),[]
    for t in toks:
        if t not in seen:
            seen.add(t); out.append(t)
    return '·'.join(out)

# -------------- business logic --------------
def choose_latest_per_code(df: pd.DataFrame, code_col: str) -> pd.DataFrame:
    """적용약가가 이력형일 때 제품코드별 최신 1행 선별. 가능한 날짜열 우선순위 적용."""
    cand_dates = [c for c in ["기준일자","기준일","고시일자","적용일자","고시일","적용일"] if c in df.columns]
    df2 = df.copy()
    def parse_date(s):
        s=to_text(s).replace(".","-").replace("/","-")
        # yyyy-mm-dd or yyyymmdd
        if re.fullmatch(r'\d{8}', s):
            s=f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
        try:
            return pd.to_datetime(s, errors="coerce")
        except Exception:
            return pd.NaT
    if cand_dates:
        # 대표 날짜열 만들기
        df2["_sort_date"] = pd.NaT
        for c in cand_dates:
            if c in df2.columns:
                d = df2[c].map(parse_date)
                df2["_sort_date"] = df2["_sort_date"].fillna(d)
        # 같은 날짜 tie-breaker: 연번/버전/일련
        tiebreak = None
        for c in ["연번","연번(정렬)","버전","일련번호","순번"]:
            if c in df2.columns:
                tiebreak = c; break
        if tiebreak:
            try:
                df2["_tie"] = pd.to_numeric(df2[tiebreak], errors="coerce").fillna(0)
            except Exception:
                df2["_tie"] = 0
        else:
            df2["_tie"] = 0
        df2 = df2.sort_values(by=["_sort_date","_tie"], ascending=[True, True])
        df2 = df2.drop(columns=["_tie"])
        # 최신만
        last = df2.groupby(code_col, as_index=False).tail(1)
        return last.drop(columns=["_sort_date"])
    else:
        # 스냅샷형: 첫 행만
        return df2.groupby(code_col, as_index=False).first()

def aggregate_atc(atc: pd.DataFrame) -> pd.DataFrame:
    c_code = pick(atc, ["제품코드","product_code"])
    c_atc  = pick(atc, ["ATC코드","ATC Code","ATC"])
    c_name = pick(atc, ["ATC코드 명칭","ATC명칭","ATC Name"])
    if not c_code or not c_atc:
        return pd.DataFrame(columns=["제품코드","ATC코드","ATC코드 명칭"])
    atc2 = atc.rename(columns={c_code:"제품코드", c_atc:"ATC코드"})
    if c_name and c_name!="ATC코드 명칭": atc2 = atc2.rename(columns={c_name:"ATC코드 명칭"})
    g = atc2.groupby("제품코드", as_index=False).agg({
        "ATC코드": merge_tokens,
        "ATC코드 명칭": merge_tokens if "ATC코드 명칭" in atc2.columns else "first"
    })
    if "ATC코드 명칭" not in g.columns: g["ATC코드 명칭"] = ""
    return g

def aggregate_substances(subs: pd.DataFrame) -> pd.DataFrame:
    c_code = pick(subs, ["주성분코드","성분코드","substance_code"])
    c_name = pick(subs, ["주성분명","성분명","일반명","한글명","성분한글명"])
    c_en   = pick(subs, ["영문명","성분영문명","일반명(영문)","영문일반명"])
    if not c_code:
        return pd.DataFrame(columns=["주성분코드","성분명_KO","성분명_EN"])
    tmp = subs.rename(columns={c_code:"주성분코드"})
    if c_name and c_name!="성분명_KO": tmp = tmp.rename(columns={c_name:"성분명_KO"})
    if c_en and c_en!="성분명_EN":     tmp = tmp.rename(columns={c_en:"성분명_EN"})
    # 정규화
    if "성분명_KO" in tmp.columns:
        tmp["성분명_KO"] = tmp["성분명_KO"].map(normalize_general)
    else:
        tmp["성분명_KO"] = ""
    if "성분명_EN" in tmp.columns:
        tmp["성분명_EN"] = tmp["성분명_EN"].map(english_only)
    else:
        tmp["성분명_EN"] = ""
    # 대표값(최빈)
    out = []
    for code, g in tmp.groupby("주성분코드"):
        ko_candidates = [t for t in g["성분명_KO"].tolist() if t]
        en_candidates = [t for t in g["성분명_EN"].tolist() if t]
        ko = Counter(ko_candidates).most_common(1)[0][0] if ko_candidates else ""
        en = Counter(en_candidates).most_common(1)[0][0] if en_candidates else ""
        out.append({"주성분코드":to_text(code), "성분명_KO":ko, "성분명_EN":en})
    return pd.DataFrame(out)

# surfaces (유의어) 추출
def export_names_from_product(raw:str) -> list[str]:
    """제품명 괄호 세그먼트 중 '수출명:'이 포함된 토큰만 파싱"""
    s=to_text(raw)
    if not s: return []
    s=norm_spaces(unify_brackets(s))
    outs=[]
    for seg in outer_paren_segments(s):
        if not seg: continue
        if seg.startswith("수출명"):
            seg = re.sub(r'^수출명\s*:\s*','', seg).strip()
            seg = drop_dose_anywhere(seg); seg = drop_orphan_units(seg)
            for tok in split_outside_parens(seg):
                t = to_text(tok)
                if t: outs.append(extract_pumyeong(t))
    # 유니크
    seen, res = set(), []
    for t in outs:
        if t and t not in seen:
            seen.add(t); res.append(t)
    return res

def generate_variants(surface:str) -> list[str]:
    """간단 변형: 캅셀→캡슐, 하이픈/공백 제거 버전"""
    s=to_text(surface)
    if not s: return []
    outs = set()
    outs.add(s)
    outs.add(s.replace("캅셀","캡슐"))
    outs.add(s.replace("-",""))
    outs.add(s.replace(" ",""))
    outs.add(s.replace("·"," "))
    return [t for t in outs if t and t!=s]

# ---------------- main pipeline ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--applied", default=r"C:\Jimin\pharmaLex_unity\data\20220901_20250901 적용약가파일_8.28.수정.xlsx")
    ap.add_argument("--atc",     default=r"C:\Jimin\pharmaLex_unity\data\건강보험심사평가원_ATC코드 매핑 목록_20240630.csv")
    ap.add_argument("--subs",    default=r"C:\Jimin\pharmaLex_unity\data\건강보험심사평가원_약가마스터_의약품주성분_20241014.csv")
    ap.add_argument("--outdir",  default=r".\out")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    # 1) 적용약가 로드 & 스냅샷(제품코드별 최신 1행)
    apdf_full = read_excel_all_sheets(args.applied, dtype=str)

    # 컬럼 매핑
    c_prod = pick(apdf_full, ["제품코드","품목기준코드","product_code"]) or "제품코드"
    c_name = pick(apdf_full, ["제품명","품명","품목명","product_name"]) or "제품명"
    c_subs = pick(apdf_full, ["주성분코드","성분코드","substance_code"]) or "주성분코드"
    # 보조 컬럼(있으면 보존)
    c_company = pick(apdf_full, ["업체명","회사명","제조사"])
    c_form    = pick(apdf_full, ["제형","성상","제형명"])
    c_route   = pick(apdf_full, ["투여경로","투여"])
    c_spec    = pick(apdf_full, ["규격"])
    c_unit    = pick(apdf_full, ["단위"])
    c_price   = pick(apdf_full, ["상한금액","상한가","약가"])

    # 표준화
    apdf = apdf_full.rename(columns={
        c_prod:"제품코드", c_name:"제품명", c_subs:"주성분코드",
        (c_company or "업체명"):"업체명",
        (c_form or "제형"):"제형",
        (c_route or "투여경로"):"투여경로",
        (c_spec or "규격"):"규격",
        (c_unit or "단위"):"단위",
        (c_price or "상한금액"):"상한금액",
    })
    for col in ["제품코드","제품명","주성분코드","업체명","제형","투여경로","규격","단위","상한금액"]:
        if col not in apdf.columns: apdf[col]=""
    apdf["제품코드"] = apdf["제품코드"].map(to_text)
    apdf["제품명"]   = apdf["제품명"].map(to_text)
    apdf["주성분코드"] = apdf["주성분코드"].map(to_text)

    # 최신행 선택
    apdf_latest = choose_latest_per_code(apdf, code_col="제품코드")

    # 2) 보조 매핑 선집계
    atc_df  = aggregate_atc(read_csv_any(args.atc, dtype=str))
    subs_df = aggregate_substances(read_csv_any(args.subs, dtype=str))

    # 3) 좌조인(행수 불변)
    base = apdf_latest.merge(atc_df, on="제품코드", how="left")
    base = base.merge(subs_df, on="주성분코드", how="left")

    # 4) 정제 컬럼 생성
    base["품명_정제"]   = base["제품명"].map(extract_pumyeong)
    parsed_comp        = base["제품명"].map(components_from_name)
    base["성분_정제"]   = base.apply(lambda r: to_text(r.get("성분명_KO","")) if to_text(r.get("성분명_KO","")) else parsed_comp.loc[r.name], axis=1)
    base["성분명_EN"]   = base.get("성분명_EN","").astype(str)

    # 5) 산출 ①: 정제된 테이블
    cols_out = ["제품코드","제품명","품명_정제","주성분코드","성분명_KO","성분명_EN","성분_정제",
                "ATC코드","ATC코드 명칭","제형","투여경로","규격","단위","상한금액","업체명"]
    for c in cols_out:
        if c not in base.columns: base[c] = ""
    enriched = base[cols_out].copy()
    write_csv(enriched, str(outdir/"01_applied_price_enriched.csv"))

    # 6) 산출 ②: 유의어 사전용 정제 약제종합
    rows = []
    for _, r in enriched.iterrows():
        code = to_text(r["제품코드"])
        canonical = to_text(r["품명_정제"]) or extract_pumyeong(to_text(r["제품명"])) or to_text(r["제품명"])

        surfaces = set()

        def add_surface(x):
            s = to_text(x)
            if s and s != canonical:
                surfaces.add(s)

        # 기본/브랜드
        add_surface(r["제품명"])
        for ename in export_names_from_product(to_text(r["제품명"])):
            add_surface(ename)

        # 성분
        add_surface(r.get("성분명_KO", ""))
        add_surface(r.get("성분_정제", ""))
        for tok in to_text(r.get("성분명_EN", "")).split("·"):
            add_surface(tok)

        # 변형판 추가
        more = set()
        for s in list(surfaces):
            for v in generate_variants(s):
                add_surface(v)

        # 정렬 시 타입충돌 방지 + 안정적 정렬
        surfaces = sorted({to_text(s) for s in surfaces if to_text(s)}, key=lambda z: z.lower())

        for s in surfaces:
            rows.append({
                "lemma_id": code,
                "canonical": canonical,
                "surface": s,
                "surface_type": "auto",
                "source": "applied/atc/subs/parse",
                "boost": 1,
            })

    syn_df = pd.DataFrame(rows)
    write_csv(syn_df, str(outdir / "02_yakjejonghap_for_syn.csv"))

    # 7) 산출 ③: 규칙 TXT
    # synonyms.txt
    syn_lines = []
    for code, g in syn_df.groupby("lemma_id"):
        canonical = to_text(g["canonical"].iloc[0])
        surfs = sorted({to_text(s) for s in g["surface"].tolist() if to_text(s) and to_text(s) != canonical},
                       key=lambda z: z.lower())
        if not canonical or not surfs:
            continue
        syn_lines.append(f"{canonical} => {', '.join(surfs)}")
    Path(outdir / "03_rules_synonyms.txt").write_text("\n".join(syn_lines), encoding="utf-8")

    # proper nouns (canonical + surface 전부)
    pn = set()
    for _, r in enriched.iterrows():
        cano = to_text(r.get("품명_정제", "")) or extract_pumyeong(to_text(r.get("제품명", ""))) or to_text(r.get("제품명", ""))
        if cano:
            pn.add(cano)
        for s in export_names_from_product(to_text(r.get("제품명", ""))):
            if to_text(s):
                pn.add(to_text(s))
        # 성분/영문 성분도 추가
        for t in to_text(r.get("성분명_KO", "")).split("·"):
            if to_text(t):
                pn.add(to_text(t))
        for t in to_text(r.get("성분명_EN", "")).split("·"):
            if to_text(t):
                pn.add(to_text(t))

    pn_lines = [f"{w}\tNNP" for w in sorted(pn, key=lambda z: z.lower())]
    Path(outdir / "03_rules_proper_nouns.txt").write_text("\n".join(pn_lines), encoding="utf-8")

    # 8) 간단 QA 출력
    n_codes = enriched["제품코드"].nunique()
    print(f"[OK] enriched rows: {len(enriched):,} (unique 제품코드={n_codes:,})")
    print(f"[OK] files saved in: {outdir.resolve()}")
    print(" - 01_applied_price_enriched.csv")
    print(" - 02_yakjejonghap_for_syn.csv")
    print(" - 03_rules_synonyms.txt")
    print(" - 03_rules_proper_nouns.txt")

if __name__ == "__main__":
    main()

# 기본값 경로 그대로 쓸 때
# python .\build_applied_price_bundle.py

# 또는 명시적으로
# python .\build_applied_price_bundle.py `
#   --applied "C:\Jimin\pharmaLex_unity\data\20220901_20250901 적용약가파일_8.28.수정.xlsx" `
#   --atc     "C:\Jimin\pharmaLex_unity\data\건강보험심사평가원_ATC코드 매핑 목록_20240630.csv" `
#   --subs    "C:\Jimin\pharmaLex_unity\data\건강보험심사평가원_약가마스터_의약품주성분_20241014.csv" `
#   --outdir  ".\out"
