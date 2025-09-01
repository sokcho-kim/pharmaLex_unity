# -*- coding: utf-8 -*-
# cleanup_pumyeong_tail.py
import re
import argparse
import pandas as pd
from pathlib import Path

# 단위/포장 패턴 (한글 '밀리그람/그람' 포함)
# UNIT = r'(?:mg|g|mcg|μg|㎍|㎎|mL|ml|U|IU|%|밀리그램|밀리그람|그램|그람|마이크로그램|밀리리터|밀리그램|300mg|100밀리그램|25밀리그램|50밀리그램|)'
UNIT = r'(?:mg|g|mcg|μg|㎍|㎎|mL|ml|U|IU|%|밀리그램|밀리그람|그램|그람|마이크로그램|밀리리터|밀리그램)'
PACK = r'(?:정|캡슐|캅셀|병|회|스틱|패치|패취|vial|앰플|포|mL|ml|회분|펌프|스프레이)'
DOSE1 = rf'\d+(?:\.\d+)?\s*{UNIT}'
DOSE2 = rf'\d+\s*/\s*\d+\s*(?:{UNIT}|{PACK})?'
TAIL  = rf'(?:{DOSE1}(?:\s*/\s*\d+(?:\.\d+)?\s*(?:{PACK}|{UNIT}))?|{DOSE2}|{DOSE1}|(?:\d+\s*{PACK}))'

DOSE_TOKEN = rf'(?<!\w)\d+(?:\.\d+)?\s*{UNIT}(?!\w)'  # 숫자 + (선택적 공백) + 단위

def drop_trailing_dose(s: str) -> str:
    if not isinstance(s, str):
        return s
    prev = None
    out = s
    # 꼬리 용량/포장 덩어리 반복 제거
    while prev != out:
        prev = out
        out = re.sub(rf'(?:\s*{TAIL})+$', '', out, flags=re.IGNORECASE)
    out = re.sub(r'\d+\s*주$', '', out)  # “…주” 꼬리
    # 남은 밑줄/구분기호 정리
    out = out.rstrip(' _,-/')
    return out

def read_korean_csv(p):
    last=None
    for enc in ("utf-8-sig","cp949","euc-kr","utf-16","utf-8","latin1"):
        try:
            return pd.read_csv(p, dtype=str, encoding=enc)
        except Exception as e:
            last=e
    raise last

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input",  required=True, help="입력 CSV")
    ap.add_argument("--column", default="품명_정제", help="정제 대상 컬럼명 (기본: 품명_정제)")
    ap.add_argument("--output", required=True, help="출력 CSV")
    ap.add_argument("--encoding", default="utf-8-sig", help="출력 인코딩 (기본: utf-8-sig)")
    args = ap.parse_args()

    df = read_korean_csv(args.input)
    if args.column not in df.columns:
        raise SystemExit(f"[ERR] 컬럼없음: {args.column} / 실제 컬럼: {list(df.columns)[:10]} ...")

    df[args.column] = df[args.column].map(drop_trailing_dose)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, encoding=args.encoding)
    print(f"[OK] {len(df):,} rows → {args.output}")

if __name__ == "__main__":
    main()
