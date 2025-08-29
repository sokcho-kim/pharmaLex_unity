# -*- coding: utf-8 -*-
"""
CSV의 제품명(원문)에서:
- '품명'만 추출해 새 컬럼(기본: 품명_정제)에 저장
- (옵션) 문장 어디든 숫자+단위 토큰 제거
- (옵션) 괄호 속 '성분'을 추출해 새 컬럼(기본: 성분_정제)에 저장

CLI 옵션 요약
  --col                : 입력 컬럼명 (기본: 제품명)
  --new-col            : 품명 결과 컬럼명 (기본: 품명_정제)
  --extract-components : 성분 컬럼 생성 활성화
  --comp-col           : 성분 결과 컬럼명 (기본: 성분_정제)
  --drop-dose-anywhere : 문장 어디든 '숫자+단위' 토큰 삭제(예: 300mg, 100 밀리그램)
  --attached-only      : (위 옵션과 함께) 붙여쓴 것만 삭제(예: 300mg / 100밀리그램)
  --keep-percent       : % 단위는 유지(기본은 %도 삭제)
  --encoding           : 출력 인코딩(기본: utf-8-sig)
"""

import re
import argparse
import pandas as pd
from pathlib import Path
from typing import Optional, List

# ---------- CSV 로더 ----------
def read_korean_csv(p: str | Path, dtype=str) -> pd.DataFrame:
    last = None
    for enc in ("utf-8-sig","cp949","euc-kr","utf-16","utf-8","latin1"):
        try:
            return pd.read_csv(p, encoding=enc, dtype=dtype)
        except Exception as e:
            last = e
    raise last

# ---------- 전처리 유틸 ----------
BRACKET_MAP = str.maketrans({
    "（":"(", "［":"(", "｛":"(", "{":"(", "[":"(",
    "）":")", "］":")", "｝":")", "}":")", "]":")",
})
def unify_brackets(s: str) -> str:
    return s.translate(BRACKET_MAP)

def normalize_spaces(s: str) -> str:
    s = s.replace("\ufeff","")
    s = re.sub(r'[\u3000\s]+', ' ', s)  # 공백 정리
    s = s.replace("→","->").replace("ᆞ","·").replace("ㆍ","·").replace("，",",")
    return s.strip()

# ---------- 단위/포장 패턴 ----------
DOSAGE_FORMS = [
    "정","서방정","발포정","츄어블정","캡슐","캅셀","연질캡슐","경질캡슐",
    "현탁","현탁용분말","시럽","시럽용","시럽제","점안","점안액","주","주사","주사용",
    "크림","겔","겔제","액","액제","스프레이","패치","패취","좌제","분무",
    "흡입","흡입용분말","분말","용액","현탁액","농축액","시럽용현탁용분말","프리필드"
]

def unit_regex(keep_percent: bool) -> str:
    units = [
        r"mg", r"g", r"mcg", r"μg", r"㎍", r"㎎",
        r"mL", r"ml", r"U", r"IU", r"I\.?U\.?",
        r"밀리그램", r"밀리그람", r"그램", r"그람", r"마이크로그램", r"밀리리터",
    ]
    if not keep_percent:
        units.append(r"%")
    return r"(?:%s)" % "|".join(units)

PACK = r'(?:정|캡슐|캅셀|병|회|스틱|패치|패취|vial|앰플|포|mL|ml|회분|펌프|스프레이)'

def build_trailing_tail_regex(keep_percent: bool) -> str:
    U = unit_regex(keep_percent)
    DOSE1 = rf'\d+(?:\.\d+)?\s*{U}'
    DOSE2 = rf'\d+\s*/\s*\d+\s*(?:{U}|{PACK})?'
    TAIL  = rf'(?:{DOSE1}(?:\s*/\s*\d+(?:\.\d+)?\s*(?:{PACK}|{U}))?|{DOSE2}|{DOSE1}|(?:\d+\s*{PACK}))'
    return TAIL

def build_anywhere_token_regex(keep_percent: bool, attached_only: bool) -> re.Pattern:
    U = unit_regex(keep_percent)
    if attached_only:
        # 붙여쓴 것만 제거: 300mg, 100밀리그램  (ASCII만 경계로 취급해 한글 앞뒤도 매치)
        pattern = rf'(?<![0-9A-Za-z_])\d+(?:\.\d+)?{U}(?![0-9A-Za-z_])'
    else:
        # 붙여쓴/띄어쓴 모두
        pattern = rf'\d+(?:\.\d+)?\s*{U}'
    return re.compile(pattern, flags=re.IGNORECASE)

# ---------- 공통 정리 ----------
def drop_trailing_dose(text: str, keep_percent: bool) -> str:
    if not isinstance(text, str):
        return text
    TAIL = build_trailing_tail_regex(keep_percent)
    out = text
    prev = None
    while prev != out:
        prev = out
        # 꼬리 덩어리 제거 (공백 없어도 매치되게)
        out = re.sub(rf'(?:{TAIL})+\s*$', '', out, flags=re.IGNORECASE)
    # "...주" 꼬리
    out = re.sub(r'\d+\s*주$', '', out)
    # 남은 구분기호 정리
    return out.rstrip(' _,-/')

def drop_dose_tokens_anywhere(text: str, keep_percent: bool, attached_only: bool) -> str:
    if not isinstance(text, str):
        return text
    rx = build_anywhere_token_regex(keep_percent, attached_only)
    out = rx.sub('', text)
    out = re.sub(r'\s*,\s*,+', ', ', out).strip(' ,-/')
    out = re.sub(r'\s{2,}', ' ', out)
    return out

def contains_dosage_form(token: str) -> bool:
    t = token.replace(' ', '')
    return any(form in t for form in DOSAGE_FORMS)

def is_pure_dose(token: str, keep_percent: bool) -> bool:
    U = unit_regex(keep_percent)
    if re.fullmatch(rf'\(?\s*\d+(?:\.\d+)?\s*(?:{U}|{PACK})\s*(?:/\s*\d+(?:\.\d+)?\s*(?:{U}|{PACK}))?\s*\)?', token, flags=re.IGNORECASE):
        return True
    return False

# ---------- 품명 추출 ----------
def extract_pumyeong(raw: str, keep_percent: bool, drop_anywhere: bool, attached_only: bool) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return ""
    s = normalize_spaces(unify_brackets(raw))
    base = s.split('(', 1)[0]
    base = drop_trailing_dose(base, keep_percent=keep_percent)
    if drop_anywhere:
        base = drop_dose_tokens_anywhere(base, keep_percent=keep_percent, attached_only=attached_only)
    return base

# ---------- 성분 추출 ----------
SEP_RX = re.compile(r'\s*[\,/]\s*|[·ᆞㆍ]')
def split_components(seg: str) -> List[str]:
    return [p for p in SEP_RX.split(seg) if p]

def extract_components(raw: str, keep_percent: bool) -> str:
    """
    괄호 속 세그먼트에서 성분만 추출:
      - '수출명:' 세그먼트 무시
      - 용량/포장/단위 토큰 제거
      - 제형 토큰(정/캡슐/주/시럽/점안…) 제거
      - 여러 성분은 '·'로 연결해 하나의 문자열로 반환
      - '비율/수화물/미분화' 등 설명 괄호는 그대로 보존 (예: 클라불란산칼륨(4:1))
    """
    if not isinstance(raw, str) or not raw.strip():
        return ""
    s = normalize_spaces(unify_brackets(raw))
    comps = []
    for m in re.finditer(r'\(([^()]*)\)', s):
        seg = m.group(1).strip()
        if not seg or seg.startswith("수출명"):
            continue
        # 용량/단위 토큰 제거(띄어쓴/붙여쓴 모두)
        seg_clean = drop_dose_tokens_anywhere(seg, keep_percent=keep_percent, attached_only=False)
        seg_clean = seg_clean.strip(' _,-/')
        if not seg_clean or is_pure_dose(seg_clean, keep_percent):
            continue
        # 분할 후 필터링
        for tok in split_components(seg_clean):
            t = tok.strip()
            if not t or is_pure_dose(t, keep_percent):
                continue
            if contains_dosage_form(t):
                # '시럽용세프라딘' 같은 건 제형 접두어 제거 시도
                t2 = re.sub(r'^(시럽용|주사용|점안|흡입용|경구용|좌제용|현탁용|외용|주사)\s*', '', t)
                # 여전히 제형이면 스킵
                if not t2 or contains_dosage_form(t2):
                    continue
                t = t2
            t = t.strip()
            if t:
                comps.append(t)
    # 중복 제거(순서 보존)
    seen, out = set(), []
    for t in comps:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return '·'.join(out) if out else ""

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input",  required=True, help="입력 CSV 경로")
    ap.add_argument("--col",    default="제품명", help="원문 제품명 컬럼명 (기본: 제품명)")
    ap.add_argument("--new-col", dest="new_col", default="품명_정제", help="품명 결과 컬럼명 (기본: 품명_정제)")
    ap.add_argument("--output", required=True, help="출력 CSV 경로")
    ap.add_argument("--encoding", default=None, help="출력 인코딩 (기본: utf-8-sig)")

    # 용량 토큰 제거 옵션
    ap.add_argument("--drop-dose-anywhere", dest="drop_dose_anywhere", action="store_true",
                    help="문장 어디에 있든 '숫자+단위' 토큰 삭제")
    ap.add_argument("--attached-only", dest="attached_only", action="store_true",
                    help="(drop-dose-anywhere와 함께) 붙여쓴 토큰만 삭제 (예: 300mg, 100밀리그램)")
    ap.add_argument("--keep-percent", dest="keep_percent", action="store_true",
                    help="‘%’ 단위는 유지(기본은 %도 삭제)")

    # 성분 추출 옵션
    ap.add_argument("--extract-components", dest="extract_components", action="store_true",
                    help="괄호 속 성분을 추출해 별도 컬럼 생성")
    ap.add_argument("--comp-col", dest="comp_col", default="성분_정제",
                    help="성분 결과 컬럼명 (기본: 성분_정제)")

    args = ap.parse_args()

    df = read_korean_csv(args.input, dtype=str)
    if args.col not in df.columns:
        raise SystemExit(f"[ERR] 입력 컬럼 '{args.col}' 없음. 실제 컬럼: {list(df.columns)[:12]} ...")

    # 품명 컬럼 생성
    df[args.new_col] = df[args.col].apply(
        lambda x: extract_pumyeong(
            x,
            keep_percent=args.keep_percent,
            drop_anywhere=args.drop_dose_anywhere,
            attached_only=args.attached_only
        )
    )

    # 성분 컬럼 생성 (옵션)
    if args.extract_components:
        df[args.comp_col] = df[args.col].apply(lambda x: extract_components(x, keep_percent=args.keep_percent))

    out_enc = args.encoding or "utf-8-sig"
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, encoding=out_enc)

    print(f"[OK] rows={len(df):,} | input={args.input}")
    print(f"[OK] saved -> {args.output} (encoding={out_enc})")
    print(f"[OK] new column: {args.new_col}" + (f" | component column: {args.comp_col}" if args.extract_components else ""))

if __name__ == "__main__":
    main()
