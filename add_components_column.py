# -*- coding: utf-8 -*-
# add_components_column.py
import re, argparse, pandas as pd
from pathlib import Path

def read_kor_csv(p, dtype=str):
    last=None
    for enc in ("utf-8-sig","cp949","euc-kr","utf-16","utf-8","latin1"):
        try: return pd.read_csv(p, encoding=enc, dtype=dtype)
        except Exception as e: last=e
    raise last

BRMAP=str.maketrans({"（":"(","［":"(","｛":"(", "{":"(", "[":"(",
                      "）":")","］":")","｝":")", "}":")", "]":")"})
def unify(s): return s.translate(BRMAP)
def normsp(s):
    s=s.replace("\ufeff","")
    s=re.sub(r'[\u3000\s]+',' ',s)
    s=s.replace("→","->").replace("ᆞ","·").replace("ㆍ","·").replace("，",",")
    return s.strip()

def unit_regex(keep_percent:bool):
    units=[r"mg",r"g",r"mcg",r"μg",r"㎍",r"㎎",r"mL",r"ml",r"U",r"IU",r"I\.?U\.?",
           r"밀리그램",r"밀리그람",r"그램",r"그람",r"마이크로그램",r"밀리리터"]
    if not keep_percent: units.append(r"%")
    return "(?:"+"|".join(units)+")"

PACK=r'(?:정|캡슐|캅셀|병|회|스틱|패치|패취|vial|앰플|포|mL|ml|회분|펌프|스프레이)'

def drop_dose_anywhere(text:str, keep_percent:bool)->str:
    if not isinstance(text,str): return text
    U=unit_regex(keep_percent)
    pat=re.compile(rf'\d+(?:\.\d+)?\s*{U}', re.IGNORECASE)
    out=pat.sub('', text)
    out=re.sub(r'\s*,\s*,+',', ',out).strip(' ,-/')
    out=re.sub(r'\s{2,}',' ',out)
    return out

DOSAGE_FORMS={"정","서방정","발포정","츄어블정","캡슐","캅셀","연질캡슐","경질캡슐",
              "현탁","현탁용분말","시럽","시럽용","시럽제","점안","점안액","주","주사","주사용",
              "크림","겔","겔제","액","액제","스프레이","패치","패취","좌제","분무",
              "흡입","흡입용분말","분말","용액","현탁액","농축액","시럽용현탁용분말","프리필드"}

def has_form(t:str)->bool:
    z=t.replace(' ','')
    return any(f in z for f in DOSAGE_FORMS)

SEP_RX=re.compile(r'\s*[\,/]\s*|[·ᆞㆍ]')
def split_comps(seg:str):
    return [p for p in SEP_RX.split(seg) if p]

def is_pure_dose(tok:str, keep_percent:bool)->bool:
    U=unit_regex(keep_percent)
    return bool(re.fullmatch(
        rf'\(?\s*\d+(?:\.\d+)?\s*(?:{U}|{PACK})(?:\s*/\s*\d+(?:\.\d+)?\s*(?:{U}|{PACK}))?\s*\)?',
        tok, flags=re.IGNORECASE))

def extract_components(raw:str, keep_percent:bool)->str:
    if not isinstance(raw,str) or not raw.strip(): return ""
    s=normsp(unify(raw))
    comps=[]
    for m in re.finditer(r'\(([^()]*)\)', s):
        seg=m.group(1).strip()
        if not seg or seg.startswith("수출명"): continue
        seg=drop_dose_anywhere(seg, keep_percent)  # 용량/단위 제거
        seg=seg.strip(' _,-/')
        if not seg or is_pure_dose(seg, keep_percent): continue
        for tok in split_comps(seg):
            t=tok.strip()
            if not t or is_pure_dose(t, keep_percent): continue
            if has_form(t):
                t2=re.sub(r'^(시럽용|주사용|점안|흡입용|경구용|좌제용|현탁용|외용|주사)\s*','',t)
                if not t2 or has_form(t2): continue
                t=t2
            if t: comps.append(t)
    seen=set(); out=[]
    for t in comps:
        if t not in seen:
            seen.add(t); out.append(t)
    return '·'.join(out) if out else ""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="입력 CSV")
    ap.add_argument("--col", default="제품명", help="원문 제품명 컬럼명")
    ap.add_argument("--output", required=True, help="출력 CSV")
    ap.add_argument("--comp-col", default="성분_정제", help="신규 성분 컬럼명")
    ap.add_argument("--encoding", default="utf-8-sig")
    ap.add_argument("--keep-percent", action="store_true", help="성분 내 %는 보존")
    a=ap.parse_args()

    df=read_kor_csv(a.input, dtype=str)
    if a.col not in df.columns:
        raise SystemExit(f"[ERR] 입력 컬럼 '{a.col}' 없음. 실제: {list(df.columns)[:12]} ...")
    df[a.comp_col]=df[a.col].apply(lambda x: extract_components(x, keep_percent=a.keep_percent))
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.output, index=False, encoding=a.encoding)
    print(f"[OK] rows={len(df):,} -> {a.output}  (new col: {a.comp_col})")
if __name__=="__main__": main()
