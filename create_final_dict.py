#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import unicodedata
from collections import defaultdict

def normalize_text(text):
    """완벽한 텍스트 정규화"""
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
    
    # 용량/단위 제거 (더 포괄적)
    text = re.sub(r'\b\d*\.?\d+\s*(mg|g|kg|㎍|mcg|μg|ug|iu|i\.?u\.?|ki\.?u\.?|%|ppm|ml|l|cc|units?|unit)\b', '', text, flags=re.IGNORECASE)
    
    # 비율 제거  
    text = re.sub(r'\b\d+:\d+|w/w|v/v|w/v\b', '', text, flags=re.IGNORECASE)
    
    # 복합 농도 제거
    text = re.sub(r'\b\d+\.?\d*\s*(mg|g|㎍|mcg|μg|ug)/(ml|l|kg)\b', '', text, flags=re.IGNORECASE)
    
    # ext. 제거
    text = re.sub(r'\bext\.?\b', '', text, flags=re.IGNORECASE)
    
    # 법인 표기 제거
    text = re.sub(r'\([주유]\)|㈜|co\.,?\s*ltd\.?|inc\.?|corp\.?|pharmaceutical', '', text, flags=re.IGNORECASE)
    
    # 불필요 구분자를 공백으로 변환
    text = re.sub(r'[/&.,;:]+', ' ', text)
    
    # 다중 공백 정리
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def get_base_compound(text):
    """염 형태를 제거한 기본 화합물명 추출"""
    if not text:
        return text
    
    # 오타 수정 먼저
    text = text.replace('hyrobromide', 'hydrobromide')
    
    # 염 형태 패턴들 (끝에서만 제거)
    salt_patterns = [
        r'hcl$', r'hydrochloride$', r'hydrochlorate$',
        r'hbr$', r'hydrobromide$', r'succinate$', 
        r'tartrate$', r'sulfate$', r'sulphate$',
        r'phosphate$', r'acetate$', r'citrate$', 
        r'fumarate$', r'maleate$', r'oxalate$',
        r'lactate$', r'gluconate$', r'stearate$', 
        r'palmitate$', r'benzoate$', r'salicylate$',
        r'sodium$', r'potassium$', r'calcium$', 
        r'magnesium$', r'aluminum$', r'zinc$',
        r'iron$', r'chloride$', r'bromide$', 
        r'iodide$', r'fluoride$', r'oxide$',
        r'hydroxide$', r'carbonate$', r'bicarbonate$',
        r'mesylate$', r'tosylate$', r'besylate$', 
        r'esylate$', r'disodium$', r'dipotassium$',
        r'dihydrochloride$', r'monohydrate$', r'dihydrate$',
        r'trihydrate$', r'anhydrous$'
    ]
    
    base = text.lower()
    for pattern in salt_patterns:
        base = re.sub(pattern, '', base, flags=re.IGNORECASE)
    
    return base.strip() if base.strip() else text

def create_variations(text):
    """텍스트의 자연스러운 변형들 생성"""
    variations = set()
    
    # 하이픈 처리
    if '-' in text:
        variations.add(text.replace('-', ''))
        variations.add(text.replace('-', ' '))
    
    # 괄호 처리
    if '(' in text and ')' in text:
        no_paren = re.sub(r'\([^)]*\)', '', text).strip()
        if no_paren:
            variations.add(no_paren)
    
    return variations

def process_final_dict():
    """최종 의약품 사전 생성"""
    input_file = "C:\\Jimin\\pharmaLex_unity\\pharma_dict_final_merged.txt"
    output_file = "C:\\Jimin\\pharmaLex_unity\\pharma_dict_submission_ready.txt"
    
    print("데이터 읽기 및 분석...")
    
    # 기본 성분별로 그룹화
    base_to_entries = defaultdict(list)
    original_entries = []
    normalization_examples = []
    
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
                
                # 유사값들 파싱
                similar_values = [v.strip() for v in similar_values_str.split(',') if v.strip()]
                
                # 대표값 정규화
                normalized_rep = normalize_text(representative)
                base_compound = get_base_compound(normalized_rep)
                
                # 정규화 예시 수집
                if len(normalization_examples) < 10:
                    for val in [representative] + similar_values[:3]:  # 대표값과 첫 3개 유사값만
                        norm_val = normalize_text(val)
                        if (norm_val != val.lower() and 
                            any(x in val for x in ['α', 'β', 'mg', 'HCl', 'ext', '%', ':', '/', 'HBr'])):
                            normalization_examples.append((val, norm_val))
                            break
                
                entry = {
                    'similar_values': similar_values,
                    'original_rep': representative,
                    'normalized_rep': normalized_rep,
                    'line_num': i + 1
                }
                
                base_to_entries[base_compound].append(entry)
                original_entries.append(entry)
                
            except Exception as e:
                continue
    
    original_count = len(original_entries)
    print(f"원본 엔트리 수: {original_count}")
    
    # 통합 처리
    print("성분별 통합 처리...")
    final_results = []
    integration_examples = []
    
    for base_compound in sorted(base_to_entries.keys()):
        entries = base_to_entries[base_compound]
        
        if len(entries) == 1:
            # 단일 엔트리
            entry = entries[0]
            similar_values = set(entry['similar_values'])
            representative = entry['normalized_rep']
            
            # 추가 변형 생성 (제한적으로)
            for val in list(similar_values):
                similar_values.update(create_variations(val))
            
            # 기본적인 염 형태 추가 (너무 많지 않게)
            if representative == base_compound and len(base_compound) > 3:
                similar_values.add(f"{base_compound}hcl")
                similar_values.add(f"{base_compound} hcl")
            
            # 대표값과 같은 것 제거
            final_similar = {v for v in similar_values 
                            if v and normalize_text(v) != representative}
            
            if final_similar:
                similar_list = sorted(final_similar)
                result_line = f"{', '.join(similar_list)} => {representative}"
                final_results.append(result_line)
        
        else:
            # 다중 엔트리 - 통합 필요
            if len(integration_examples) < 10:
                original_reps = [e['original_rep'] for e in entries]
                integration_examples.append((base_compound, original_reps))
            
            # 가장 적합한 대표값 선택 (가장 짧은 기본 형태)
            best_rep = base_compound
            
            # 모든 유사값 수집
            all_similar = set()
            all_original_reps = set()
            
            for entry in entries:
                all_similar.update(entry['similar_values'])
                all_original_reps.add(entry['original_rep'])
                
                # 대표값이 기본 형태가 아니라면 유사값에 추가
                if entry['normalized_rep'] != best_rep:
                    all_similar.add(entry['original_rep'])
            
            # 추가 변형 생성
            for val in list(all_similar):
                all_similar.update(create_variations(val))
            
            # 기본 염 형태 추가
            if len(base_compound) > 3:
                all_similar.add(f"{base_compound}hcl")
                all_similar.add(f"{base_compound} hcl")
            
            # 대표값과 같은 것 제거
            final_similar = {v for v in all_similar 
                            if v and normalize_text(v) != best_rep}
            
            if final_similar:
                similar_list = sorted(final_similar)
                result_line = f"{', '.join(similar_list)} => {best_rep}"
                final_results.append(result_line)
    
    # 결과 저장
    print("결과 파일 저장...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in final_results:
            f.write(result + '\n')
    
    final_count = len(final_results)
    merged_count = original_count - final_count
    
    # 결과 출력 (인코딩 문제 피하기 위해 영어만)
    print(f"\n=== Processing Complete ===")
    print(f"Original lines: {original_count}")
    print(f"Final lines: {final_count}")
    print(f"Merged lines: {merged_count}")
    
    print(f"\n=== Integration Examples (Top 5) ===")
    for i, (base, originals) in enumerate(integration_examples[:5]):
        if len(originals) > 1:
            print(f"{i+1}. {base} <- Merged from: {', '.join(originals)}")
    
    print(f"\n=== Normalization Examples (Top 5) ===")
    for i, (original, normalized) in enumerate(normalization_examples[:5]):
        print(f"{i+1}. {original} -> {normalized}")
    
    print(f"\nOutput file: {output_file}")
    
    return final_count, merged_count, integration_examples, normalization_examples

if __name__ == "__main__":
    try:
        final_count, merged_count, integrations, normalizations = process_final_dict()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()