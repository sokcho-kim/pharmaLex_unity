# -*- coding: utf-8 -*-
"""
normalize_drug_csv.py  (v4)

핵심 기능
- '제품명' → 품명_정제  : 괄호 앞 기본명 + (꼬리/중간) 숫자+단위 제거 + 고아단위 제거
- '제품명'(괄호) → 성분_정제 : 중첩괄호 보존, '수출명:' 무시, 순수비율/단위/제형/포장토큰 제거, 다성분 '·' 연결
- '일반명' → 성분_EN   : 순수 영문만 보관(소문자, '·' 연결)
- 주성분코드 단위 보간 : 일반명(정규화 최빈) → 성분_정제(최빈) 우선순위로 보완
- 안전 저장 : CSV(전필드 인용/구분자 선택) + 선택 XLSX 동시 저장(Excel 열이동/자동형변환 방지)
- (신규) 그룹핑 병합 : --group-by로 지정한 키 기준 1행으로 병합(성분/영문 성분은 유니크 병합)

사용 예
  python normalize_drug_csv.py --input 약제종합.csv --output out/약제종합_FIXED.csv --keep-percent \
      --excel-out out/약제종합_FIXED.xlsx --csv-quote-all --group-by 제품코드 --expect-rows 54717
"""

import re
import csv
import argparse
import pandas as pd
from pathlib import Path
from collections import Counter

# ----------------- CSV 로더 -----------------
def read_korean_csv(p: str | Path, dtype=str) -> pd.DataFrame:
    last = None
    for enc in ("utf-8-sig","cp949","euc-kr","utf-16","utf-8","latin1"):
        try:
            return pd.read_csv(p, encoding=enc, dtype=dtype, keep_default_na=False, na_values=[])
        except Exception as e:
            last = e
    raise last

# ----------------- 전처리 유틸 -----------------
BRMAP = str.maketrans({
    "（":"(", "［":"(", "｛":"(", "{":"(", "[":"(", "【":"(", "〔":"(",
    "）":")", "］":")", "｝":")", "}":")", "]":")", "】":")", "〕":")"
})

def unify_brackets(s: str) -> str:
    return s.translate(BRMAP)

def norm_spaces(s: str) -> str:
    s = s.replace("\ufeff","")
    s = re.sub(r'[\u3000\s]+',' ', s)
    s = s.replace("→","->").replace("ᆞ","·").replace("ㆍ","·").replace("，",",")
    return s.strip()

# ----------------- 단위/포장 규칙 -----------------
def unit_regex(keep_percent: bool) -> str:
    # IU 변형(KIU, K.I.U 등), L/ℓ/리터 추가
    iu = r'(?:IU|I\.?U\.?|I\s?U|KIU|K\.?I\.?U\.?|K\s?I\s?U|kIU|k\.?I\.?U\.?|k\s?I\s?U|U)'
    units = [
        r"mg", r"g", r"mcg", r"μg", r"㎍", r"㎎",
        r"L", r"ℓ", r"mL", r"ml",
        iu,
        r"밀리그램", r"밀리그람", r"그램", r"그람", r"마이크로그램", r"리터", r"밀리리터",
    ]
    if not keep_percent:
        units.append(r"%")
    return r"(?:%s)" % "|".join(units)

# 포장/용기 토큰(괄호 안에서 쓰이는 '백', bag 등)
PACK_WORDS = {"병","회","스틱","패치","패취","vial","앰플","포","회분","펌프","스프레이","프리필드","백","bag"}

PACK = r'(?:정|캡슐|캅셀|병|회|스틱|패치|패취|vial|앰플|포|mL|ml|회분|펌프|스프레이|백|bag)'

def drop_pack_tokens(text: str) -> str:
    if not isinstance(text,str) or not text.strip():
        return text
    # 경계 기반으로 포장 단어 제거
    pattern = r'(?:(?<=^)|(?<=[\s,;/·ᆞㆍ\(\)-]))(?:' + "|".join(map(re.escape, PACK_WORDS)) + r')(?:(?=$)|(?=[\s,;/·ᆞㆍ\(\)-]))'
    out = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
    return re.sub(r'\s{2,}',' ', out).strip(' ,;/·ᆞㆍ-()')

def drop_dose_anywhere(text: str, keep_percent: bool) -> str:
    """문장 어디든 숫자(+공백)+단위 토큰 제거 (붙여쓴/띄어쓴 모두)"""
    if not isinstance(text, str):
        return text
    U = unit_regex(keep_percent)
    out = re.sub(rf'\d+(?:\.\d+)?\s*{U}', '', text, flags=re.IGNORECASE)
    out = re.sub(r'\s*,\s*,+', ', ', out).strip(' ,-/')
    out = re.sub(r'\s{2,}',' ', out)
    return out

def drop_trailing_dose(text: str, keep_percent: bool) -> str:
    """문장 끝의 용량/포장 꼬리(300mg/1정, 1병 등) 반복 제거 (공백 없어도 매치)"""
    if not isinstance(text, str):
        return text
    U = unit_regex(keep_percent)
    DOSE1 = rf'\d+(?:\.\d+)?\s*{U}'
    DOSE2 = rf'\d+\s*/\s*\d+\s*(?:{U}|{PACK})?'
    TAIL  = rf'(?:{DOSE1}(?:\s*/\s*\d+(?:\.\d+)?\s*(?:{PACK}|{U}))?|{DOSE2}|{DOSE1}|(?:\d+\s*{PACK}))'
    out, prev = text, None
    while prev != out:
        prev = out
        out = re.sub(rf'(?:{TAIL})+\s*$', '', out, flags=re.IGNORECASE)
    out = re.sub(r'\d+\s*주$', '', out)  # "...주" 꼬리
    return out.rstrip(' _,-/')

def drop_orphan_units(text: str, keep_percent: bool) -> str:
    """숫자 없이 남은 단위 토큰 제거 (예: 'mg', 'mL', '밀리그램' 단독)"""
    if not isinstance(text, str) or not text.strip():
        return text
    U_core = [
        r"mg", r"g", r"mcg", r"μg", r"㎍", r"㎎",
        r"L", r"ℓ", r"mL", r"ml",
        r"IU", r"I\.?U\.?", r"I\s?U",
        r"KIU", r"K\.?I\.?U\.?", r"K\s?I\s?U",
        r"kIU", r"k\.?I\.?U\.?", r"k\s?I\s?U",
        r"U",
        r"밀리그램", r"밀리그람", r"그램", r"그람", r"마이크로그램", r"리터", r"밀리리터",
    ]
    pattern = r'(?:(?<=^)|(?<=[\s,;/·ᆞㆍ\(\)-]))(?:' + '|'.join(U_core) + r')(?:(?=$)|(?=[\s,;/·ᆞㆍ\(\)-]))'
    out = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
    out = re.sub(r'\s{2,}', ' ', out).strip(' ,;/·ᆞㆍ-()')
    return out

# ----------------- 괄호/분할 -----------------
def unify_all(s: str) -> str:
    return norm_spaces(unify_brackets(s or ""))

def outer_paren_segments(text: str) -> list[str]:
    """바깥 괄호 레벨의 세그먼트(중첩 보존)"""
    if not isinstance(text, str) or not text:
        return []
    segs, buf, depth = [], [], 0
    for ch in text:
        if ch == '(':
            if depth > 0: buf.append(ch)
            depth += 1
            continue
        if ch == ')':
            depth -= 1
            if depth < 0: depth = 0
            if depth == 0:
                seg = ''.join(buf).strip()
                if seg: segs.append(seg)
                buf = []
            else:
                buf.append(ch)
            continue
        if depth > 0:
            buf.append(ch)
    return segs

def split_outside_parens(text: str) -> list[str]:
    """괄호 밖에서만 , / · 로 분할"""
    if not isinstance(text, str) or not text:
        return []
    parts, buf, depth = [], [], 0
    for ch in text:
        if ch == '(':
            depth += 1; buf.append(ch); continue
        if ch == ')':
            if depth > 0: depth -= 1
            buf.append(ch); continue
        if ch in [',','/','·','ᆞ','ㆍ'] and depth == 0:
            tok = ''.join(buf).strip()
            if tok: parts.append(tok)
            buf = []
        else:
            buf.append(ch)
    tok = ''.join(buf).strip()
    if tok: parts.append(tok)
    return parts

# ----------------- 필터/판별 -----------------
DOSAGE_FORMS = {
    "정","서방정","발포정","츄어블정","캡슐","캅셀","연질캡슐","경질캡슐",
    "현탁","현탁용분말","시럽","시럽용","시럽제","점안","점안액","주","주사","주사용",
    "크림","겔","겔제","액","액제","스프레이","패치","패취","좌제","분무",
    "흡입","흡입용분말","분말","용액","현탁액","농축액","시럽용현탁용분말","프리필드"
}
def has_form(token: str) -> bool:
    t = (token or "").replace(' ','')
    return any(f in t for f in DOSAGE_FORMS)

def is_pure_dose(token: str, keep_percent: bool) -> bool:
    U = unit_regex(keep_percent)
    return bool(re.fullmatch(
        rf'\(?\s*\d+(?:\.\d+)?\s*(?:{U}|{PACK})(?:\s*/\s*\d+(?:\.\d+)?\s*(?:{U}|{PACK}))?\s*\)?',
        token or "", flags=re.IGNORECASE))

def is_ratio_only(s: str) -> bool:
    """순수 비율/범위만: 4:1, 3.5->1, 1->8~10 등(문자 섞이면 False)"""
    if not isinstance(s, str) or not s.strip():
        return False
    t = s.strip()
    if t.startswith('(') and t.endswith(')'):
        t = t[1:-1].strip()
    return bool(re.fullmatch(r'[0-9\.\s:>\-~→/]+', t)) and not re.search(r'[A-Za-z가-힣]', t)

# ----------------- 품명/성분 추출 -----------------
def extract_pumyeong(raw: str, keep_percent: bool) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return ""
    s = unify_all(raw)
    base = s.split('(', 1)[0]
    base = drop_trailing_dose(base, keep_percent=keep_percent)
    base = drop_dose_anywhere(base, keep_percent=keep_percent)   # 중간 단위 제거
    base = drop_orphan_units(base, keep_percent=keep_percent)    # 고아 단위 제거
    return base

def extract_components_from_name(raw: str, keep_percent: bool) -> str:
    """제품명에서 성분을 추출 (괄호 내부만, 규칙 적용)"""
    if not isinstance(raw, str) or not raw.strip():
        return ""
    s = unify_all(raw)
    comps = []
    for seg in outer_paren_segments(s):
        if not seg or seg.startswith("수출명"):
            continue
        if is_ratio_only(seg):
            continue
        # 숫자+단위/포장 토큰 제거
        seg_clean = drop_dose_anywhere(seg, keep_percent=keep_percent).strip(' _,-/')
        seg_clean = drop_pack_tokens(seg_clean)
        seg_clean = drop_orphan_units(seg_clean, keep_percent=keep_percent)
        if not seg_clean or is_pure_dose(seg_clean, keep_percent):
            continue
        # 괄호 밖에서만 분할
        for tok in split_outside_parens(seg_clean):
            t = tok.strip()
            if not t or is_pure_dose(t, keep_percent):
                continue
            # 제형 제거(접두어형)
            if has_form(t):
                t2 = re.sub(r'^(시럽용|주사용|점안|흡입용|경구용|좌제용|현탁용|외용|주사)\s*', '', t)
                if not t2 or has_form(t2):
                    continue
                t = t2
            # 내부 괄호가 '순수 비율'만이면 제거
            t = re.sub(r'\((?:\s*[0-9\.\s:>\-~→/]+\s*)\)', '', t).strip()
            t = drop_orphan_units(t, keep_percent=keep_percent)
            if t:
                comps.append(t)
    # 중복 제거(순서 유지)
    seen, out = set(), []
    for t in comps:
        if t not in seen:
            seen.add(t); out.append(t)
    return '·'.join(out) if out else ""

def normalize_general_name(gen: str, keep_percent: bool) -> str:
    """일반명 정규화: 비율-only/용량·포장 토큰 제거, 구분자 통일"""
    if not isinstance(gen, str) or not gen.strip():
        return ""
    s = unify_all(gen)
    s = re.sub(r'\((?:\s*[0-9\.\s:>\-~→/]+\s*)\)', '', s)  # 괄호 속 순수 비율 삭제
    s = drop_dose_anywhere(s, keep_percent=keep_percent)
    s = drop_pack_tokens(s)
    s = drop_orphan_units(s, keep_percent=keep_percent)
    parts = [p.strip() for p in re.split(r'\s*[,/]\s*|[·ᆞㆍ]', s) if p.strip()]
    parts2 = []
    for t in parts:
        if has_form(t) or is_ratio_only(t) or is_pure_dose(t, keep_percent):
            continue
        parts2.append(t)
    # 중복 제거
    seen, out = set(), []
    for t in parts2:
        if t not in seen:
            seen.add(t); out.append(t)
    return '·'.join(out) if out else ""

def english_name(gen: str) -> str:
    """영문 일반명만 보관 (있을 때)"""
    if not isinstance(gen, str) or not gen.strip():
        return ""
    if re.search(r'[A-Za-z]', gen) and not re.search(r'[가-힣]', gen):
        parts = [p.strip().lower() for p in re.split(r'[,/·ᆞㆍ]+', gen) if p.strip()]
        return '·'.join(parts)
    return ""

# ----------------- 대표값/보간 -----------------
def is_invalid_comp(s: str) -> bool:
    """보간이 필요한 성분 값인지 판단"""
    if not isinstance(s, str) or not s.strip():
        return True
    t = s.strip()
    if t == "미분화":
        return True
    if is_ratio_only(t):
        return True
    return False

def representative_by_code(df: pd.DataFrame, code_col: str, comp_col: str, gen_col: str, keep_percent: bool):
    """주성분코드 단위 대표 KO/EN 계산"""
    reps = {}
    for code, g in df.groupby(code_col):
        # 후보 1: 일반명 정규화 최빈
        norm_gens = [normalize_general_name(x, keep_percent) for x in g[gen_col].tolist() if x]
        norm_gens = [x for x in norm_gens if x]
        rep_ko = ""
        if norm_gens:
            rep_ko = Counter(norm_gens).most_common(1)[0][0]
        # 후보 2: 성분_정제 최빈
        if not rep_ko:
            comps = [x for x in g[comp_col].tolist() if x and not is_invalid_comp(x)]
            if comps:
                rep_ko = Counter(comps).most_common(1)[0][0]
        # 영문 대표
        ens = [english_name(x) for x in g[gen_col].tolist() if x]
        ens = [x for x in ens if x]
        rep_en = Counter(ens).most_common(1)[0][0] if ens else ""
        reps[code] = (rep_ko, rep_en)
    return reps

def apply_fallbacks(df: pd.DataFrame, code_col: str, comp_col: str, reps: dict):
    filled = 0
    for i, row in df.iterrows():
        val = row.get(comp_col, "")
        if is_invalid_comp(val):
            rep = reps.get(row.get(code_col, ""), ("",""))[0]
            if rep:
                df.at[i, comp_col] = rep
                filled += 1
    return filled

# ----------------- 그룹 병합 -----------------
def first_nonempty(series: pd.Series) -> str:
    for v in series:
        if isinstance(v, str) and v.strip():
            return v
    return ""

def merge_tokens(series: pd.Series) -> str:
    toks = []
    for v in series:
        if not isinstance(v, str) or not v.strip():
            continue
        for t in re.split(r'[·,]+', v):
            t = t.strip()
            if t:
                toks.append(t)
    seen, out = set(), []
    for t in toks:
        if t not in seen:
            seen.add(t); out.append(t)
    return '·'.join(out)

def maybe_group(df: pd.DataFrame, group_cols: list[str], comp_col: str, comp_en_col: str) -> pd.DataFrame:
    if not group_cols:
        return df
    agg = {}
    for c in df.columns:
        if c in group_cols:
            continue
        if c == comp_col or c == comp_en_col:
            agg[c] = merge_tokens
        elif c == "품명_정제" or c == "제품명":
            agg[c] = first_nonempty
        else:
            agg[c] = "first"
    return df.groupby(group_cols, as_index=False).agg(agg)

# ----------------- 메인 -----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="입력 CSV")
    ap.add_argument("--output", required=True, help="출력 CSV")
    ap.add_argument("--col-name", default="제품명", help="제품명 컬럼명 (기본: 제품명)")
    ap.add_argument("--gen-name", default="일반명", help="일반명 컬럼명 (기본: 일반명)")
    ap.add_argument("--substance-col", default="주성분코드", help="주성분코드 컬럼명 (기본: 주성분코드)")
    ap.add_argument("--new-pum", default="품명_정제", help="결과 품명 컬럼명 (기본: 품명_정제)")
    ap.add_argument("--new-comp", default="성분_정제", help="결과 성분 컬럼명 (기본: 성분_정제)")
    ap.add_argument("--new-comp-en", default="성분_EN", help="결과 영문 성분 컬럼명 (기본: 성분_EN)")
    ap.add_argument("--keep-percent", action="store_true", help="% 단위 유지(기본은 삭제)")
    # 안전 저장 옵션
    ap.add_argument("--excel-out", default=None, help="동시에 XLSX도 저장 (경로 지정)")
    ap.add_argument("--csv-sep", default=",", help="CSV 구분자 (기본 ,)")
    ap.add_argument("--csv-quote-all", action="store_true", help="CSV 모든 필드 인용")
    # 그룹핑/검증
    ap.add_argument("--group-by", default=None, help="그룹 키(콤마구분, 예: 제품코드 또는 HIRA제품코드)")
    ap.add_argument("--expect-rows", type=int, default=None, help="기대 행수(불일치시 경고)")
    args = ap.parse_args()

    df = read_korean_csv(args.input, dtype=str)

    # 존재 확인
    for col in [args.col_name, args.gen_name, args.substance_col]:
        if col not in df.columns:
            raise SystemExit(f"[ERR] 입력 컬럼 '{col}' 없음. 실제: {list(df.columns)[:18]} ...")

    keep_percent = args.keep_percent

    before_rows = len(df)

    # 1) 품명
    df[args.new_pum] = df[args.col_name].apply(lambda x: extract_pumyeong(x, keep_percent=keep_percent))
    # 품명 NaN/빈값 보호: 원본 값으로 폴백
    df[args.new_pum] = df.apply(lambda r: r[args.new_pum] if isinstance(r[args.new_pum], str) and r[args.new_pum].strip() else (r[args.col_name] or ""), axis=1)

    # 2) 성분(제품명 기반)
    df[args.new_comp] = df[args.col_name].apply(lambda x: extract_components_from_name(x, keep_percent=keep_percent))

    # 3) 영문 일반명
    df[args.new_comp_en] = df[args.gen_name].apply(english_name)

    # 4) 대표값 산정 및 보간
    reps = representative_by_code(
        df, code_col=args.substance_col, comp_col=args.new_comp, gen_col=args.gen_name, keep_percent=keep_percent
    )
    filled = apply_fallbacks(df, code_col=args.substance_col, comp_col=args.new_comp, reps=reps)

    # 5) 그룹 병합(선택)  — 예: --group-by 제품코드  → 중복행 1행으로
    group_cols = [c.strip() for c in (args.group_by.split(",") if args.group_by else []) if c.strip()]
    df2 = maybe_group(df, group_cols, comp_col=args.new_comp, comp_en_col=args.new_comp_en)

    after_rows = len(df2)

    # 6) 저장 (CSV + 옵션 XLSX)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    quoting = csv.QUOTE_ALL if args.csv_quote_all else csv.QUOTE_MINIMAL
    df2.fillna("", inplace=True)  # NaN 방지
    df2.to_csv(out, index=False, encoding="utf-8-sig", sep=args.csv_sep, quoting=quoting)
    print(f"[OK] CSV saved → {out}")

    if args.excel_out:
        xout = Path(args.excel_out)
        xout.parent.mkdir(parents=True, exist_ok=True)
        try:
            with pd.ExcelWriter(xout, engine="openpyxl") as w:
                df2.astype(str).to_excel(w, index=False, sheet_name="data")
            print(f"[OK] XLSX saved → {xout}")
        except Exception as e:
            print(f"[WARN] XLSX 저장 실패: {e}  (pip install openpyxl 필요)")

    # 7) QA 리포트
    def count_num_unit(series: pd.Series) -> int:
        U = unit_regex(keep_percent)
        return series.fillna('').str.contains(rf'\d+(?:\.\d+)?\s*{U}', case=False, regex=True).sum()
    def count_orphan(series: pd.Series) -> int:
        return series.fillna('').str.contains(r'(?:^|[\s,;/·ᆞㆍ\(\)-])(mg|mL|ml|L|ℓ|밀리그램|그램|리터)(?:$|[\s,;/·ᆞㆍ\(\)-])', case=False, regex=True).sum()
    invalid_after = df2[args.new_comp].apply(is_invalid_comp).sum()
    num_unit_pum = count_num_unit(df2[args.new_pum])
    num_unit_comp = count_num_unit(df2[args.new_comp])
    orphan_pum = count_orphan(df2[args.new_pum])
    orphan_comp = count_orphan(df2[args.new_comp])

    print(f"[QA] 입력행: {before_rows:,}  → 출력행: {after_rows:,}" + (f"  (기대={args.expect_rows:,})" if args.expect_rows else ""))
    if args.expect_rows and after_rows != args.expect_rows:
        print("[WARN] 출력 행수가 기대값과 다릅니다. --group-by 키/원본 중복 여부 확인 요망.")
    print(f"[QA] 성분_정제 이상치(빈값/비율-only/미분화-only): {invalid_after:,}")
    print(f"[QA] 품명_정제 숫자+단위: {num_unit_pum:,} / 고아단위: {orphan_pum:,}")
    print(f"[QA] 성분_정제 숫자+단위: {num_unit_comp:,} / 고아단위: {orphan_comp:,}")

if __name__ == "__main__":
    main()


# 퍼센트(%)는 남기고, 제품코드 기준으로 1행으로 병합, 기대 행수 체크(54717)
# python .\final_normalize_drug_csv.py `
#   --input ".\약제종합.csv" `
#   --output ".\out\약제종합_FIXED_v4.csv" `
#   --excel-out ".\out\약제종합_FIXED_v4.xlsx" `
#   --csv-quote-all `
#   --keep-percent `
#   --group-by "제품코드" `
#   --expect-rows 54717
