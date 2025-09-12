#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import unicodedata
from collections import defaultdict, Counter

def normalize_text(text):
    """텍스트 정규화 함수 - 완벽한 규칙 적용"""
    if not text:
        return ""
    
    # 유니코드 정규화
    text = unicodedata.normalize('NFD', text)
    
    # 그리스 문자 변환
    greek_map = {
        'α': 'alfa', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta',
        'ε': 'epsilon', 'ζ': 'zeta', 'η': 'eta', 'θ': 'theta',
        'ι': 'iota', 'κ': 'kappa', 'λ': 'lambda', 'μ': 'mu',
        'ν': 'nu', 'ξ': 'xi', 'ο': 'omicron', 'π': 'pi',
        'ρ': 'rho', 'σ': 'sigma', 'τ': 'tau', 'υ': 'upsilon',
        'φ': 'phi', 'χ': 'chi', 'ψ': 'psi', 'ω': 'omega'
    }
    for greek, latin in greek_map.items():
        text = text.replace(greek, latin)
    
    # 소문자 변환
    text = text.lower()
    
    # 용량/단위 제거 (모든 숫자+단위 조합)
    units_pattern = r'\b\d*\.?\d+\s*(mg|g|kg|㎍|mcg|μg|ug|iu|i\.?u\.?|ki\.?u\.?|%|ppm|ml|l|cc|units?|unit)\b'
    text = re.sub(units_pattern, '', text, flags=re.IGNORECASE)
    
    # 비율 제거
    ratio_pattern = r'\b\d+:\d+|w/w|v/v|w/v\b'
    text = re.sub(ratio_pattern, '', text, flags=re.IGNORECASE)
    
    # 복합 농도 제거 
    concentration_pattern = r'\b\d+\.?\d*\s*(mg|g|㎍|mcg|μg|ug)/(ml|l|kg)\b'
    text = re.sub(concentration_pattern, '', text, flags=re.IGNORECASE)
    
    # ext. 제거
    text = re.sub(r'\bext\.?\b', '', text, flags=re.IGNORECASE)
    
    # 법인 표기 제거
    corp_pattern = r'\([주유]\)|㈜|co\.,?\s*ltd\.?|inc\.?|corp\.?|pharmaceutical'
    text = re.sub(corp_pattern, '', text, flags=re.IGNORECASE)
    
    # 불필요 구분자를 공백으로 변환
    text = re.sub(r'[/&.,;:]+', ' ', text)
    
    # 다중 공백을 하나로, 앞뒤 공백 제거
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def get_base_compound(text):
    """화합물의 기본 형태 추출 (염 형태 제거) - 더 정확한 패턴"""
    if not text:
        return text
        
    # 염 형태 패턴들 - 끝에 위치한 것만 제거
    salt_patterns = [
        r'\s+hcl$', r'\s+hydrochloride$', r'\s+hydrochlorate$',
        r'\s+hbr$', r'\s+hydrobromide$', r'\s+succinate$', 
        r'\s+tartrate$', r'\s+sulfate$', r'\s+sulphate$',
        r'\s+phosphate$', r'\s+acetate$', r'\s+citrate$', 
        r'\s+fumarate$', r'\s+maleate$', r'\s+oxalate$',
        r'\s+lactate$', r'\s+gluconate$', r'\s+stearate$', 
        r'\s+palmitate$', r'\s+benzoate$', r'\s+salicylate$',
        r'\s+sodium$', r'\s+potassium$', r'\s+calcium$', 
        r'\s+magnesium$', r'\s+aluminum$', r'\s+zinc$',
        r'\s+iron$', r'\s+chloride$', r'\s+bromide$', 
        r'\s+iodide$', r'\s+fluoride$', r'\s+oxide$',
        r'\s+hydroxide$', r'\s+carbonate$', r'\s+bicarbonate$',
        r'\s+mesylate$', r'\s+tosylate$', r'\s+besylate$', 
        r'\s+esylate$', r'\s+disodium$', r'\s+dipotassium$',
        r'\s+dihydrochloride$', r'\s+monohydrate$', r'\s+dihydrate$',
        r'\s+trihydrate$', r'\s+anhydrous$'
    ]
    
    base = text
    for pattern in salt_patterns:
        base = re.sub(pattern, '', base, flags=re.IGNORECASE)
    
    return base.strip() if base.strip() else text

def identify_same_compounds(entries):
    """같은 화합물을 식별하여 그룹화"""
    compound_groups = defaultdict(list)
    
    for entry in entries:
        similar_vals, original_rep, normalized_rep = entry
        base_compound = get_base_compound(normalized_rep)
        compound_groups[base_compound].append(entry)
    
    return compound_groups

def find_best_representative(entries):
    """엔트리들 중에서 가장 적합한 대표값 선택"""
    candidates = []
    
    for similar_vals, original_rep, normalized_rep in entries:
        base = get_base_compound(normalized_rep)
        # 기본 형태를 우선하고, 길이가 짧은 것을 우선
        score = len(base) + (0 if base == normalized_rep else 10)
        candidates.append((score, base, normalized_rep, original_rep))
    
    candidates.sort()
    return candidates[0][1]  # 최고 점수의 base 형태 반환

def process_pharma_dict():
    """의약품 사전 처리 메인 함수"""
    input_file = "C:\\Jimin\\pharmaLex_unity\\pharma_dict_final_merged.txt"
    output_file = "C:\\Jimin\\pharmaLex_unity\\pharma_dict_submission_ready.txt"
    
    print("파일 읽기 및 파싱...")
    
    entries = []
    normalization_examples = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i % 500 == 0:
                print(f"읽는 중... {i+1}")
            
            line = line.strip()
            if not line or '=>' not in line:
                continue
            
            try:
                parts = line.split('=>')
                if len(parts) != 2:
                    continue
                
                similar_values_str = parts[0].strip()
                representative = parts[1].strip()
                
                # 유사값들 파싱
                similar_values = [v.strip() for v in similar_values_str.split(',') if v.strip()]
                
                # 대표값 정규화
                normalized_rep = normalize_text(representative)
                if not normalized_rep:
                    continue
                
                # 정규화 예시 수집 (처음 10개)
                if len(normalization_examples) < 10:
                    for val in similar_values + [representative]:
                        normalized_val = normalize_text(val)
                        if (normalized_val != val.lower() and 
                            any(char in val for char in ['α', 'β', 'γ', 'δ', 'mg', 'HCl', 'ext', '%', ':', '/'])):
                            normalization_examples.append({
                                'original': val,
                                'normalized': normalized_val
                            })
                            break
                
                entries.append((similar_values, representative, normalized_rep))
                
            except Exception as e:
                print(f"라인 {i+1} 처리 오류: {e}")
                continue
    
    original_count = len(entries)
    print(f"원본 엔트리 수: {original_count}")
    
    # 같은 화합물 그룹 식별
    print("같은 화합물 그룹 식별 중...")
    compound_groups = identify_same_compounds(entries)
    
    # 통합 처리
    print("통합 처리 중...")
    final_results = []
    integration_examples = []
    
    for base_compound in sorted(compound_groups.keys()):
        group_entries = compound_groups[base_compound]
        
        if len(group_entries) == 1:
            # 단일 엔트리 - 그대로 사용하되 정규화만 적용
            similar_vals, original_rep, normalized_rep = group_entries[0]
            
            # 추가 변형 생성 (제한적으로)
            all_variations = set(similar_vals)
            
            # 하이픈 처리
            for val in list(all_variations):
                if '-' in val:
                    all_variations.add(val.replace('-', ''))
                    all_variations.add(val.replace('-', ' '))
            
            # 괄호 처리
            for val in list(all_variations):
                if '(' in val and ')' in val:
                    no_paren = re.sub(r'\([^)]*\)', '', val).strip()
                    if no_paren and normalize_text(no_paren) != normalized_rep:
                        all_variations.add(no_paren)
            
            # 염 형태 추가 (기본 형태일 때만)
            if normalized_rep == base_compound and len(base_compound) > 3:
                common_salts = [f"{base_compound}hcl", f"{base_compound} hcl", 
                               f"{base_compound}hydrochloride", f"{base_compound} hydrochloride"]
                for salt in common_salts:
                    if salt not in all_variations:
                        all_variations.add(salt)
            
            # 대표값과 같은 것 제거
            final_variations = {v for v in all_variations 
                               if v and v.strip() and normalize_text(v) != normalized_rep}
            
            if final_variations:
                similar_list = sorted(final_variations)
                result_line = f"{', '.join(similar_list)} => {normalized_rep}"
                final_results.append(result_line)
        
        else:
            # 다중 엔트리 - 통합 필요
            if len(integration_examples) < 5:
                original_reps = [entry[1] for entry in group_entries]
                integration_examples.append({
                    'final': base_compound,
                    'originals': original_reps,
                    'count': len(original_reps)
                })
            
            # 최적 대표값 선택
            best_representative = find_best_representative(group_entries)
            
            # 모든 유사값 수집
            all_similar_values = set()
            original_representatives = set()
            
            for similar_vals, original_rep, normalized_rep in group_entries:
                all_similar_values.update(similar_vals)
                original_representatives.add(original_rep)
                if normalized_rep != best_representative:
                    all_similar_values.add(original_rep)
            
            # 추가 변형 생성
            variations = set()
            
            # 하이픈 처리
            for val in list(all_similar_values):
                if '-' in val:
                    variations.add(val.replace('-', ''))
                    variations.add(val.replace('-', ' '))
            
            # 괄호 처리  
            for val in list(all_similar_values):
                if '(' in val and ')' in val:
                    no_paren = re.sub(r'\([^)]*\)', '', val).strip()
                    if no_paren and normalize_text(no_paren) != best_representative:
                        variations.add(no_paren)
            
            # 염 형태 추가 (제한적으로)
            if best_representative == base_compound and len(base_compound) > 3:
                common_salts = [f"{base_compound}hcl", f"{base_compound} hcl"]
                for salt in common_salts:
                    variations.add(salt)
            
            all_similar_values.update(variations)
            
            # 대표값과 같은 것 제거
            final_similar = {v for v in all_similar_values 
                            if v and v.strip() and normalize_text(v) != best_representative}
            
            if final_similar:
                similar_list = sorted(final_similar)
                result_line = f"{', '.join(similar_list)} => {best_representative}"
                final_results.append(result_line)
    
    # 결과 저장
    print("결과 저장 중...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in final_results:
            f.write(result + '\n')
    
    final_count = len(final_results)
    
    # 통계 출력
    print("\n=== 처리 완료 ===")
    print(f"처리 전 라인 수: {original_count}")
    print(f"처리 후 라인 수: {final_count}")
    print(f"통합된 라인 수: {original_count - final_count}")
    
    # 통합 예시
    print("\n=== 통합된 대표값 예시 5개 ===")
    for i, example in enumerate(integration_examples[:5]):
        if example['count'] > 1:
            print(f"{i+1}. {example['final']} <- 통합된 대표값들: {', '.join(example['originals'])}")
    
    # 정규화 예시  
    print("\n=== 정규화 적용 예시 5개 ===")
    for i, example in enumerate(normalization_examples[:5]):
        print(f"{i+1}. {example['original']} -> {example['normalized']}")

if __name__ == "__main__":
    try:
        process_pharma_dict()
        print("\n처리 완료!")
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()