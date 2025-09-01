# fix_parens.py
# -*- coding: utf-8 -*-
import argparse, csv, re, os
from typing import List, Tuple

BRACKET_MAP = {"（":"(", "［":"(", "｢":"(", "「":"(", "『":"(", "【":"(", "〔":"(", "〈":"(", "《":"(",
               "）":")", "］":")", "｣":")", "」":")", "』":")", "】":")", "〕":")", "〉":")", "》":")",
               "｛":"(", "｝":")", "{":"(", "}":")", "[":"(", "]":")"}

def normalize_brackets(s:str)->str:
    return "".join(BRACKET_MAP.get(ch, ch) for ch in s or "")

def fix_unbalanced(s:str)->str:
    if s is None: return s
    s = normalize_brackets(s.replace("\ufeff",""))
    while s.startswith(")"): s = s[1:]          # 선행 닫는 괄호 제거
    out, d = [], 0
    for ch in s:                                # 고아 ')' 제거 + 깊이 추적
        if ch == "(": d += 1; out.append(ch)
        elif ch == ")":
            if d>0: d -= 1; out.append(ch)
        else: out.append(ch)
    if d>0: out.append(")"*d)                   # 남은 '(' 만큼 보충
    return re.sub(r"\s+", " ", "".join(out)).strip()

def split_outside_parens(text:str, sep=",")->List[str]:
    parts, buf, d = [], [], 0
    for ch in text:
        if ch=="(": d+=1
        elif ch==")" and d>0: d-=1
        if ch==sep and d==0: parts.append("".join(buf).strip()); buf=[]
        else: buf.append(ch)
    parts.append("".join(buf).strip())
    return [p for p in parts if p]

def process_dict(inp, outp)->Tuple[int,int]:
    bad=tot=0
    with open(inp, "r", encoding="utf-8") as fin, open(outp,"w",encoding="utf-8") as fout:
        for line in fin:
            line=line.rstrip("\n"); tot+=1
            fixed=fix_unbalanced(line)
            if fixed!=line: bad+=1
            if fixed: fout.write(fixed+"\n")
    return bad, tot

def process_synonyms(inp, outp)->Tuple[int,int]:
    bad=tot=0
    with open(inp,"r",encoding="utf-8") as fin, open(outp,"w",encoding="utf-8") as fout:
        for raw in fin:
            line=raw.rstrip("\n"); tot+=1
            if "=>" in line:
                left, right = line.split("=>",1)
                items = [fix_unbalanced(x) for x in split_outside_parens(left)]
                fixed = ", ".join(items) + " => " + fix_unbalanced(right.strip())
            else:
                fixed = fix_unbalanced(line)
            if fixed!=line: bad+=1
            if fixed: fout.write(fixed+"\n")
    return bad, tot

def process_csv(inp, outp)->Tuple[int,int]:
    bad=tot=0
    with open(inp,"r",encoding="utf-8-sig",newline="") as fin, open(outp,"w",encoding="utf-8-sig",newline="") as fout:
        rdr=csv.DictReader(fin); fns=rdr.fieldnames; assert fns
        w=csv.DictWriter(fout, fieldnames=fns, quoting=csv.QUOTE_MINIMAL); w.writeheader()
        for row in rdr:
            tot+=1; changed=False
            for col in ["preferred_label_ko","preferred_label_en","representative_label"]:
                if col in row and row[col]:
                    fx=fix_unbalanced(row[col])
                    if fx!=row[col]: row[col]=fx; changed=True
            w.writerow(row)
            if changed: bad+=1
    return bad, tot

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dict"); ap.add_argument("--syn"); ap.add_argument("--csv")
    ap.add_argument("--outdir", default=".")
    a=ap.parse_args(); os.makedirs(a.outdir, exist_ok=True)
    if a.dict:
        b,t=process_dict(a.dict, os.path.join(a.outdir,"proper_nouns_dictionary.fixed.txt"))
        print(f"[DICT] changed {b}/{t} lines -> proper_nouns_dictionary.fixed.txt")
    if a.syn:
        b,t=process_synonyms(a.syn, os.path.join(a.outdir,"opensearch_synonyms_substance.fixed.txt"))
        print(f"[SYN ] changed {b}/{t} lines -> opensearch_synonyms_substance.fixed.txt")
    if a.csv:
        b,t=process_csv(a.csv, os.path.join(a.outdir,"code_to_label_substance.fixed.csv"))
        print(f"[CSV ] changed {b}/{t} rows  -> code_to_label_substance.fixed.csv")
if __name__=="__main__": main()
