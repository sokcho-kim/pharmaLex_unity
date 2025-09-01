# normalize_drug_name.py
# -*- coding: utf-8 -*-
import re
import sys

# ---- 1) 문자/구두점 정리
BRACKET_MAP = str.maketrans({
    "（":"(", "［":"(", "｛":"(", "{":"(", "[":"(",
    "）":")", "］":")", "｝":")", "}":")", "]":")",
})
def unify_brackets(s: str) -> str:
    return s.translate(BRACKET_MAP)

def normalize_spaces(s: str) -> str:
    s = re.sub(r'[\u3000\s]+', ' ', s)
    s = s.replace("→", "->").replace("ᆞ", "·").replace("ㆍ", "·").replace("，", ",")
    return s.strip()

# ---- 2) 용량/포장 패턴 (밖/괄호 안 공통 제거)
UNIT = r'(?:mg|g|mcg|μg|㎍|㎎|mL|ml|U|IU|%|밀리그램|그램|마이크로그램|밀리리터)'
PACK = r'(?:정|캡슐|캅셀|병|회|스틱|패치|패취|vial|앰플|포|병|mL|ml)'
DOSE1 = rf'\d+(?:\.\d+)?\s*{UNIT}'
DOSE2 = rf'\d+\s*/\s*\d+\s*(?:{UNIT}|{PACK})?'
TAIL_DOSE = rf'(?:{DOSE1}(?:\s*/\s*\d+(?:\.\d+)?\s*(?:{PACK}|{UNIT}))?|{DOSE2}|{DOSE1}|(?:\d+\s*{PACK}))'

# ---- 3) 토큰 헬퍼
def drop_trailing_dose(s: str) -> str:
    # 접미 용량/포장 덩어리 제거(여러 번 반복)
    prev = None
    while prev != s:
        prev = s
        s = re.sub(rf'(?:\s*{TAIL_DOSE})+$', '', s)
    # 숫자 뒤 접미 '주' 같은 꼬리 제거
    s = re.sub(r'\d+\s*주$', '', s)
    return s.strip(' ,-/')

def split_kor_eng_combo(s: str) -> list[str]:
    # 한글뒤 영문이 바로 붙은 수출명 분해: '오스부톤정OSBUTONEtablet' -> ['오스부톤정','OSBUTONEtablet']
    return re.findall(r'[가-힣0-9A-Za-z\.\-]+', s)

def is_pure_dose(token: str) -> bool:
    t = token.strip()
    # 용량/포장만 있거나 숫자/단위 조합만이면 제거
    if re.fullmatch(rf'(?:{TAIL_DOSE}|\d+(?:\.\d+)?\s*(?:{PACK}))', t):
        return True
    # 괄호 안에 용량/포장만 있는 경우
    if re.fullmatch(rf'\(?\s*{TAIL_DOSE}\s*\)?', t):
        return True
    return False

def clean_export_name(s: str) -> list[str]:
    # '수출명: ...' -> 토큰 리스트
    s = s.split(':',1)[1] if ':' in s else s
    s = s.strip().strip('()[]{}').strip()
    s = re.sub(r'[;·,]+', ' ', s)
    s = s.rstrip('.')
    parts = split_kor_eng_combo(s)
    return [p for p in parts if p]

def normalize_composition(seg: str) -> str | None:
    """
    성분/제형/설명 세그먼트 정리:
    - 용량 꼬리 제거
    - 다성분 구분자는 '·'로 통일
    - 불필요한 괄호 속 '순수 비율'(예: (20->1))은 제거
    """
    txt = seg.strip().strip('()')
    # 불필요 비율 괄호 제거(숫자/기호만)
    txt = re.sub(r'\((?:\s*[\d\.]+(?:\s*(?:->|:|~)\s*[\d\.]+)+\s*)\)', '', txt)
    # 용량 꼬리 제거
    txt = re.sub(rf'\s*{TAIL_DOSE}\s*$', '', txt, flags=re.IGNORECASE)
    # 다성분 구분 통일: ',', '/', ' , ' 등을 '·'로
    parts = re.split(r'\s*[,\+/]\s*', txt)
    parts = [p for p in parts if p]
    if not parts:
        return None
    # 단일 성분/표현은 그대로, 복수는 '·'로 연결
    joined = '·'.join(parts)
    joined = re.sub(r'\s+', '', joined)  # 성분 사이 공백 제거(예: 아목시실린 · 클라불란산 → 아목시실린·클라불란산)
    return joined if joined and not is_pure_dose(joined) else None

# ---- 4) 메인 정규화
KEEP_FORM_TERMS = {'프리필드','시럽용현탁용분말'}  # 필요시 확장
def normalize_product_line(line: str) -> list[str]:
    s = normalize_spaces(unify_brackets(line.replace('\ufeff','')))
    # 1) 브랜드(괄호 앞) 추출 + 접미 용량 제거
    base = s.split('(',1)[0]
    base = drop_trailing_dose(base)
    tokens = []
    if base: tokens.append(base)

    # 2) 괄호 세그먼트 순회
    for m in re.finditer(r'\(([^()]*)\)', s):
        seg = m.group(1).strip()
        if not seg:
            continue
        # 수출명
        if seg.startswith('수출명'):
            tokens.extend(clean_export_name(seg))
            continue
        # 제형/표지키워드
        if seg in KEEP_FORM_TERMS:
            tokens.append(seg)
            continue
        # 성분/설명 후보
        comp = normalize_composition(seg)
        if comp:
            tokens.append(comp if '·' in comp or '(' in comp else comp)  # 복수성분이면 그대로, 단일도 그대로
        # 그 외 (예: [수출명:…] 같은 대괄호로 들어온 경우는 이미 통일됨)

    # 3) 중복/노이즈 제거
    dedup = []
    seen = set()
    for t in tokens:
        t = t.strip().strip(',').rstrip('.')
        if not t or is_pure_dose(t):
            continue
        if t not in seen:
            dedup.append(t); seen.add(t)
    return dedup

# ---- 5) CLI: 파일 또는 표준입력
def main():
    if len(sys.argv) >= 2:
        lines = [l.rstrip('\n') for l in open(sys.argv[1], 'r', encoding='utf-8')]
    else:
        lines = [l.rstrip('\n') for l in sys.stdin]
    for l in lines:
        toks = normalize_product_line(l)
        print(', '.join(toks))

if __name__ == "__main__":
    main()
