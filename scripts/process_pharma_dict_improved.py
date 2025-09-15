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
        
    # 염 형태 패턴들 (더 정확하게)
    salt_patterns = [
        r'\s*hcl$', r'\s*hydrochloride$', r'\s*hydrochlorate$',
        r'\s*hbr$', r'\s*hydrobromide$',
        r'\s*succinate$', r'\s*tartrate$', r'\s*sulfate$', r'\s*sulphate$',
        r'\s*phosphate$', r'\s*acetate$', r'\s*citrate$', r'\s*fumarate$',
        r'\s*maleate$', r'\s*oxalate$', r'\s*lactate$', r'\s*gluconate$',
        r'\s*stearate$', r'\s*palmitate$', r'\s*benzoate$', r'\s*salicylate$',
        r'\s*sodium$', r'\s*potassium$', r'\s*calcium$', r'\s*magnesium$',
        r'\s*aluminum$', r'\s*zinc$', r'\s*iron$', r'\s*chloride$',
        r'\s*bromide$', r'\s*iodide$', r'\s*fluoride$', r'\s*oxide$',
        r'\s*hydroxide$', r'\s*carbonate$', r'\s*bicarbonate$',
        r'\s*mesylate$', r'\s*tosylate$', r'\s*besylate$', r'\s*esylate$',
        r'\s*disodium$', r'\s*dipotassium$', r'\s*dihydrochloride$',
        r'\s*monohydrate$', r'\s*dihydrate$', r'\s*trihydrate$', r'\s*anhydrous$'
    ]
    
    base = text
    for pattern in salt_patterns:
        base = re.sub(pattern, '', base, flags=re.IGNORECASE)
    
    # 공백 정리
    base = re.sub(r'\s+', ' ', base).strip()
    return base if base else text

def process_pharma_dict(input_file, output_file):
    """의약품 사전 처리 메인 함수"""
    print("파일 읽기 시작...")
    
    # 파일 읽기
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    original_count = len(lines)
    print(f"처리 전 라인 수: {original_count}")
    
    # 데이터 파싱 및 정규화
    base_to_entries = defaultdict(list)  # 기본 성분명 -> [(유사값들, 원래대표값)]
    
    print("데이터 파싱 중...")
    
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
            
            # 유사값들 파싱
            similar_values = [v.strip() for v in similar_values_str.split(',') if v.strip()]
            
            # 대표값 정규화
            normalized_rep = normalize_text(representative)
            if not normalized_rep:
                continue
            
            # 기본 화합물명 추출 (염 제거)
            base_compound = get_base_compound(normalized_rep)
            if not base_compound:
                base_compound = normalized_rep
            
            # 엔트리 저장
            base_to_entries[base_compound].append((similar_values, representative, normalized_rep))
            
        except Exception as e:
            print(f"라인 {i+1} 처리 중 오류: {e}")
            continue
    
    print("통합 처리 중...")
    
    # 각 기본 성분별로 통합 처리
    final_results = []
    integration_examples = []
    normalization_examples = []
    
    for base_compound in sorted(base_to_entries.keys()):
        entries = base_to_entries[base_compound]
        
        # 대표값 선택 (가장 짧고 간단한 것)
        best_rep = None
        best_normalized = None
        min_length = float('inf')
        
        for similar_values, orig_rep, norm_rep in entries:
            if len(norm_rep) < min_length or (len(norm_rep) == min_length and norm_rep < (best_normalized or "")):
                best_rep = orig_rep
                best_normalized = norm_rep
                min_length = len(norm_rep)
        
        # 모든 유사값들 수집
        all_similar_values = set()
        original_representatives = set()
        
        for similar_values, orig_rep, norm_rep in entries:
            all_similar_values.update(similar_values)
            original_representatives.add(orig_rep)
            if norm_rep != best_normalized:
                all_similar_values.add(orig_rep)
        
        # 대표값을 유사값에서 제거
        if best_rep in all_similar_values:
            all_similar_values.remove(best_rep)
        
        # 추가 변형 생성
        variations = set()
        
        # 하이픈 처리
        for val in list(all_similar_values) + [best_normalized]:
            if '-' in val:
                variations.add(val.replace('-', ''))
                variations.add(val.replace('-', ' '))
        
        # 괄호 처리
        for val in list(all_similar_values):
            if '(' in val and ')' in val:
                no_paren = re.sub(r'\([^)]*\)', '', val).strip()
                if no_paren and no_paren != best_normalized:
                    variations.add(no_paren)
        
        # 염 형태들 추가 (대표값이 기본 형태라면)
        if best_normalized == base_compound:
            salt_forms = [
                f"{base_compound}hcl",
                f"{base_compound}hydrochloride", 
                f"{base_compound} hcl",
                f"{base_compound} hydrochloride",
                f"{base_compound}hbr",
                f"{base_compound}hydrobromide",
                f"{base_compound} hbr", 
                f"{base_compound} hydrobromide"
            ]
            for salt in salt_forms:
                if salt not in all_similar_values and salt != best_normalized:
                    variations.add(salt)
        
        all_similar_values.update(variations)
        
        # 최종 대표값과 같은 것들 제거
        final_similar = {v for v in all_similar_values if v and v.strip() and normalize_text(v) != best_normalized}
        
        if final_similar:
            # 통합 예시 기록 (여러 대표값이 통합된 경우)
            if len(original_representatives) > 1 and len(integration_examples) < 5:
                integration_examples.append({
                    'final': best_normalized,
                    'originals': list(original_representatives),
                    'count': len(original_representatives)
                })
            
            # 정규화 예시 기록
            for val in final_similar:
                if len(normalization_examples) < 5:
                    if (any(char in val for char in ['α', 'β', 'γ', 'δ', 'mg', 'HCl', 'Hcl', '%']) or
                        val.lower() != val or 
                        'ext.' in val.lower()):
                        normalization_examples.append({
                            'original': val,
                            'normalized': normalize_text(val) if normalize_text(val) != val else val
                        })
            
            # 결과 생성
            similar_list = sorted(final_similar)
            result_line = f"{', '.join(similar_list)} => {best_normalized}"
            final_results.append(result_line)
    
    # 결과 저장
    print("결과 저장 중...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in final_results:
            f.write(result + '\n')
    
    final_count = len(final_results)
    
    # 통계 정보 출력
    print("\n=== 처리 완료 ===")
    print(f"처리 전 라인 수: {original_count}")
    print(f"처리 후 라인 수: {final_count}")
    print(f"감소된 라인 수: {original_count - final_count}")
    
    # 통합된 대표값 예시
    print("\n=== 통합된 대표값 예시 5개 ===")
    for i, example in enumerate(integration_examples[:5]):
        print(f"{i+1}. {example['final']} <- 통합된 원래 대표값들: {', '.join(example['originals'])}")
    
    # 정규화 적용 예시
    print("\n=== 정규화 적용 예시 5개 ===")
    for i, example in enumerate(normalization_examples[:5]):
        if example['original'] != example['normalized']:
            print(f"{i+1}. {example['original']} -> {example['normalized']}")
    
    return final_count

if __name__ == "__main__":
    input_file = "C:\\Jimin\\pharmaLex_unity\\pharma_dict_final_merged.txt"
    output_file = "C:\\Jimin\\pharmaLex_unity\\pharma_dict_submission_ready.txt"
    
    try:
        process_pharma_dict(input_file, output_file)
        print(f"\n처리 완료! 결과 파일: {output_file}")
    except Exception as e:
        print(f"오류 발생: {e}")