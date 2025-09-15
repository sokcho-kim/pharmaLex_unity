#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import unicodedata
from collections import defaultdict

def normalize_text(text):
    """텍스트 정규화 함수"""
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
    
    # 용량/단위 제거 (더 포괄적으로)
    units_pattern = r'\b\d*\.?\d+\s*(mg|g|kg|㎍|mcg|μg|ug|iu|i\.u|ki\.u|%|ppm|ml|l|cc|units?|unit)\b'
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
    """화합물의 기본 형태 추출 (염 형태 제거)"""
    if not text:
        return text
        
    # 염 형태 패턴들
    salt_patterns = [
        r'hcl\b', r'hydrochloride\b', r'hydrochlorate\b',
        r'hbr\b', r'hydrobromide\b',
        r'succinate\b', r'tartrate\b', r'sulfate\b', r'sulphate\b',
        r'phosphate\b', r'acetate\b', r'citrate\b', r'fumarate\b',
        r'maleate\b', r'oxalate\b', r'lactate\b', r'gluconate\b',
        r'stearate\b', r'palmitate\b', r'benzoate\b', r'salicylate\b',
        r'sodium\b', r'potassium\b', r'calcium\b', r'magnesium\b',
        r'aluminum\b', r'zinc\b', r'iron\b', r'chloride\b',
        r'bromide\b', r'iodide\b', r'fluoride\b', r'oxide\b',
        r'hydroxide\b', r'carbonate\b', r'bicarbonate\b',
        r'mesylate\b', r'tosylate\b', r'besylate\b', r'esylate\b',
        r'disodium\b', r'dipotassium\b', r'dihydrochloride\b',
        r'monohydrate\b', r'dihydrate\b', r'trihydrate\b', r'anhydrous\b'
    ]
    
    base = text
    for pattern in salt_patterns:
        base = re.sub(pattern, '', base, flags=re.IGNORECASE)
    
    # 공백 정리
    base = re.sub(r'\s+', ' ', base).strip()
    return base

def process_pharma_dict(input_file, output_file):
    """의약품 사전 처리 메인 함수"""
    print("파일 읽기 시작...")
    
    # 파일 읽기
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    original_count = len(lines)
    print(f"처리 전 라인 수: {original_count}")
    
    # 데이터 파싱 및 정규화
    compound_groups = defaultdict(set)  # 기본 성분명 -> 모든 변형들
    representative_map = {}  # 기본 성분명 -> 대표값
    
    print("데이터 파싱 및 정규화 중...")
    
    for i, line in enumerate(lines):
        if i % 500 == 0:
            print(f"처리 중... {i}/{original_count}")
            
        line = line.strip()
        if not line or '=>' not in line:
            continue
        
        try:
            # 라인 분석
            parts = line.split('=>')
            if len(parts) != 2:
                continue
            
            similar_values_str = parts[0].strip()
            representative = parts[1].strip()
            
            # 유사값들 파싱 (한글 제품명 등)
            similar_values = [v.strip() for v in similar_values_str.split(',') if v.strip()]
            
            # 대표값 정규화
            normalized_rep = normalize_text(representative)
            if not normalized_rep:
                continue
            
            # 기본 화합물명 추출 (염 제거)
            base_compound = get_base_compound(normalized_rep)
            if not base_compound:
                base_compound = normalized_rep
            
            # 대표값 설정 (더 간단한 것을 선호)
            if base_compound not in representative_map:
                representative_map[base_compound] = normalized_rep
            else:
                # 더 짧고 간단한 것을 대표값으로
                current = representative_map[base_compound]
                if len(normalized_rep) < len(current) or (len(normalized_rep) == len(current) and normalized_rep < current):
                    representative_map[base_compound] = normalized_rep
            
            # 유사값들 추가
            compound_groups[base_compound].update(similar_values)
            compound_groups[base_compound].add(representative)
            
            # 정규화된 대표값도 추가
            if normalized_rep != representative:
                compound_groups[base_compound].add(normalized_rep)
            
            # 염 형태들도 유사값에 추가
            variations = set()
            
            # 하이픈 처리
            if '-' in normalized_rep:
                variations.add(normalized_rep.replace('-', ''))
                variations.add(normalized_rep.replace('-', ' '))
            
            # 괄호 처리 (원본에 괄호가 있다면)
            if '(' in representative and ')' in representative:
                no_paren = re.sub(r'\([^)]*\)', '', representative).strip()
                if no_paren:
                    variations.add(no_paren.lower())
            
            # 공통 염 형태들 추가
            base_for_salts = base_compound if base_compound else normalized_rep
            salt_forms = [
                f"{base_for_salts}hcl",
                f"{base_for_salts}hydrochloride",
                f"{base_for_salts} hcl",
                f"{base_for_salts} hydrochloride",
                f"{base_for_salts}hbr",
                f"{base_for_salts}hydrobromide",
                f"{base_for_salts} hbr",
                f"{base_for_salts} hydrobromide"
            ]
            
            for salt_form in salt_forms:
                if salt_form != base_compound:
                    variations.add(salt_form)
            
            compound_groups[base_compound].update(variations)
            
        except Exception as e:
            print(f"라인 {i+1} 처리 중 오류: {e}")
            continue
    
    print("중복 제거 및 정리 중...")
    
    # 최종 결과 생성
    final_results = []
    processed_compounds = set()
    
    for base_compound in sorted(compound_groups.keys()):
        if base_compound in processed_compounds:
            continue
        
        representative = representative_map[base_compound]
        all_similar = compound_groups[base_compound]
        
        # 대표값을 유사값에서 제외
        similar_values = set()
        for val in all_similar:
            normalized_val = normalize_text(val) if val != val.lower() else val
            if normalized_val != representative:
                similar_values.add(val)
        
        # 빈 값들 제거
        similar_values = {v for v in similar_values if v and v.strip()}
        
        if similar_values:
            similar_list = sorted(similar_values)
            result_line = f"{', '.join(similar_list)} => {representative}"
            final_results.append(result_line)
            processed_compounds.add(base_compound)
    
    # 결과 저장
    print("결과 저장 중...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in final_results:
            f.write(result + '\n')
    
    final_count = len(final_results)
    print(f"처리 후 라인 수: {final_count}")
    
    # 통계 정보
    print("\n=== 처리 완료 ===")
    print(f"처리 전 라인 수: {original_count}")
    print(f"처리 후 라인 수: {final_count}")
    print(f"감소된 라인 수: {original_count - final_count}")
    
    # 예시 출력
    print("\n=== 통합된 대표값 예시 5개 ===")
    for i, result in enumerate(final_results[:5]):
        parts = result.split(' => ')
        if len(parts) == 2:
            print(f"{i+1}. {parts[1]} (통합된 유사값 수: {len(parts[0].split(', '))}개)")
    
    print("\n=== 정규화 적용 예시 5개 ===")
    normalization_examples = []
    for result in final_results[:20]:  # 처음 20개에서 찾기
        parts = result.split(' => ')
        if len(parts) == 2:
            similar_vals = parts[0].split(', ')
            representative = parts[1]
            
            for val in similar_vals:
                if any(char in val for char in ['α', 'β', 'γ', 'δ']) or 'mg' in val.lower() or 'hcl' in val.lower():
                    original = val
                    normalized = normalize_text(val) if val != representative else representative
                    normalization_examples.append(f"{original} → {normalized}")
                    break
            
            if len(normalization_examples) >= 5:
                break
    
    for i, example in enumerate(normalization_examples[:5]):
        print(f"{i+1}. {example}")
    
    return final_count

if __name__ == "__main__":
    input_file = "C:\\Jimin\\pharmaLex_unity\\pharma_dict_final_merged.txt"
    output_file = "C:\\Jimin\\pharmaLex_unity\\pharma_dict_submission_ready.txt"
    
    try:
        process_pharma_dict(input_file, output_file)
        print(f"\n처리 완료! 결과 파일: {output_file}")
    except Exception as e:
        print(f"오류 발생: {e}")