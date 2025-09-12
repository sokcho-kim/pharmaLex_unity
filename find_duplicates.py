#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from collections import defaultdict

def get_base_compound(text):
    """화합물의 기본 형태 추출"""
    if not text:
        return text
        
    # 염 형태 패턴들
    salt_patterns = [
        r'hcl$', r'hydrochloride$', r'hydrochlorate$',
        r'hbr$', r'hydrobromide$', r'hyrobromide$',  # 오타도 포함
        r'succinate$', r'tartrate$', r'sulfate$', r'sulphate$',
        r'phosphate$', r'acetate$', r'citrate$', r'fumarate$',
        r'maleate$', r'oxalate$', r'lactate$', r'gluconate$',
        r'stearate$', r'palmitate$', r'benzoate$', r'salicylate$',
        r'sodium$', r'potassium$', r'calcium$', r'magnesium$',
        r'aluminum$', r'zinc$', r'iron$', r'chloride$',
        r'bromide$', r'iodide$', r'fluoride$', r'oxide$',
        r'hydroxide$', r'carbonate$', r'bicarbonate$',
        r'mesylate$', r'tosylate$', r'besylate$', r'esylate$',
        r'disodium$', r'dipotassium$', r'dihydrochloride$',
        r'monohydrate$', r'dihydrate$', r'trihydrate$', r'anhydrous$'
    ]
    
    base = text.lower()
    for pattern in salt_patterns:
        base = re.sub(pattern, '', base, flags=re.IGNORECASE)
    
    return base.strip()

def find_duplicates():
    """중복 성분 찾기"""
    input_file = "C:\\Jimin\\pharmaLex_unity\\pharma_dict_final_merged.txt"
    
    base_to_entries = defaultdict(list)
    
    print("파일 분석 중...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line or '=>' not in line:
                continue
            
            try:
                parts = line.split('=>')
                if len(parts) != 2:
                    continue
                
                similar_values_str = parts[0].strip()
                representative = parts[1].strip()
                
                # 기본 화합물명 추출
                base_compound = get_base_compound(representative)
                
                base_to_entries[base_compound].append((representative, similar_values_str, i+1))
                
            except Exception as e:
                continue
    
    print("중복 성분 찾기...")
    duplicates_found = 0
    
    for base_compound in sorted(base_to_entries.keys()):
        entries = base_to_entries[base_compound]
        if len(entries) > 1:
            duplicates_found += 1
            print(f"\n{duplicates_found}. 기본 성분: {base_compound}")
            print(f"  총 {len(entries)}개 엔트리:")
            for rep, sim_vals, line_num in entries:
                print(f"    라인 {line_num}: {rep}")
                print(f"      유사값: {sim_vals[:100]}...")
    
    print(f"\n총 {duplicates_found}개의 중복 성분 발견")
    return base_to_entries

if __name__ == "__main__":
    base_to_entries = find_duplicates()