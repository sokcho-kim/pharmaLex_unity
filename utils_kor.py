# -*- coding: utf-8 -*-
# utils_kor.py
import re
import pandas as pd
from pathlib import Path

def ensure_dir(p: str | Path) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p

def read_korean_csv(path: str | Path, dtype=str) -> pd.DataFrame:
    """국내 공공 CSV 인코딩 대응"""
    path = Path(path)
    last_err = None
    for enc in ["cp949", "euc-kr", "utf-16", "utf-8", "latin1"]:
        try:
            return pd.read_csv(path, encoding=enc, dtype=dtype)
        except Exception as e:
            last_err = e
    raise last_err

def norm_text(s: str | None) -> str | None:
    if s is None:
        return None
    s = str(s).strip()
    s = re.sub(r'[\u3000\s]+', ' ', s)             # 공백 정리
    s = s.replace('（','(').replace('）',')')       # 전각괄호→반각
    return s

# 괄호 토큰 추출 필터
_UNIT_TOKENS = set("회 병 매 정 캡슐 펌프 회분 팩 튜브 스틱 패취 패치 포".split())
_UNIT_RX = r'(mg|g|mL|mcg|µg|㎖|㎎|%|U\b|정\b|캡슐\b|병\b|회\b)'

def _is_bad_paren_term(t: str) -> bool:
    t = t.strip()
    if len(t) <= 1:
        return True
    # 숫자(+단위)만 있는 경우 제외
    if re.fullmatch(r'\d+(\.\d+)?\s*([A-Za-z가-힣%㎖㎎µgUu]+)?', t):
        return True
    # 단순 포장/단위 토큰 제외
    if any(t.endswith(u) for u in _UNIT_TOKENS):
        return True
    # 용량/단위 패턴 포함 시 제외
    if re.search(_UNIT_RX, t, flags=re.IGNORECASE):
        return True
    return False

def extract_paren_terms_refined(name: str) -> list[str]:
    """제품명 내 괄호 (…)에서 성분/염 등만 골라내기(용량/단위/포장은 제외)"""
    if not isinstance(name, str):
        return []
    terms = re.findall(r'\(([^)]+)\)', name)
    return [t.strip() for t in terms if not _is_bad_paren_term(t)]
