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
    text = unicodedata.normalize('NFKC', text)
    
    # 소문자 변환
    text = text.lower()
    
    # 그리스 문자 치환
    greek_map = {
        'α': 'alfa', 'alpha': 'alfa',
        'β': 'beta', 'beta': 'beta', 
        'γ': 'gamma', 'gamma': 'gamma',
        'δ': 'delta', 'delta': 'delta'
    }
    
    for greek, latin in greek_map.items():
        text = text.replace(greek, latin)
    
    # 용량/단위 제거 패턴
    # 숫자 + 단위 패턴
    text = re.sub(r'\d+\.?\d*\s*(mg|g|mcg|㎍|iu|i\.u|ki\.u|%|ml|l|ppm|단위|호)\b', '', text, flags=re.IGNORECASE)
    
    # 비율 제거 (4:1, 1:2 등)
    text = re.sub(r'\d+:\d+', '', text)
    
    # 단위/용량 토큰 제거
    units_pattern = r'\b(w/w|v/v|w/v|ki\.u|i\.u|iu|ext\.?|mg|g|mcg|㎍|%|ml|l|ppm)\b'
    text = re.sub(units_pattern, '', text, flags=re.IGNORECASE)
    
    # 특수문자 제거
    text = re.sub(r'[/&]', ' ', text)
    
    # 다중 공백을 단일 공백으로
    text = re.sub(r'\s+', ' ', text)
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    return text

def extract_base_component(text):
    """염 형태에서 기본 성분명 추출"""
    # 염 형태 패턴들
    salt_patterns = [
        r'\s+hcl$', r'\s+hydrochloride$',
        r'\s+hbr$', r'\s+hydrobromide$', 
        r'\s+sulfate$', r'\s+sulphate$',
        r'\s+acetate$', r'\s+besylate$',
        r'\s+mesylate$', r'\s+tartrate$',
        r'\s+citrate$', r'\s+maleate$',
        r'\s+fumarate$', r'\s+succinate$',
        r'\s+phosphate$', r'\s+sodium$',
        r'\s+potassium$', r'\s+calcium$',
        r'\s+magnesium$', r'\s+valerate$',
        r'\s+propionate$', r'\s+butyrate$',
        r'\s+palmitate$', r'\s+adipate$',
        r'\s+oxalate$'
    ]
    
    base_text = text.lower().strip()
    
    for pattern in salt_patterns:
        base_text = re.sub(pattern, '', base_text, flags=re.IGNORECASE)
    
    return base_text.strip()

def generate_variations(text):
    """텍스트의 다양한 변형 생성"""
    variations = set()
    variations.add(text)
    
    # 괄호 처리
    if '(' in text and ')' in text:
        # 괄호 제거 버전
        no_paren = re.sub(r'\([^)]*\)', '', text)
        no_paren = re.sub(r'\s+', ' ', no_paren).strip()
        if no_paren:
            variations.add(no_paren)
    
    # 하이픈 처리
    if '-' in text:
        # 하이픈 제거 버전
        no_hyphen = text.replace('-', '')
        variations.add(no_hyphen)
        
        # 하이픈을 공백으로 치환
        space_hyphen = text.replace('-', ' ')
        space_hyphen = re.sub(r'\s+', ' ', space_hyphen).strip()
        variations.add(space_hyphen)
    
    return list(variations)

def process_pharma_dict(input_file, output_file):
    """약품 유의어 사전 전처리 및 통합"""
    
    print(f"파일 읽기: {input_file}")
    
    # 데이터 로드
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"입력 라인 수: {len(lines)}")
    
    # 그룹화를 위한 딕셔너리
    grouped_data = defaultdict(set)
    
    processed_count = 0
    
    for line in lines:
        line = line.strip()
        if not line or '=>' not in line:
            continue
            
        try:
            # 유사값과 대표값 분리
            parts = line.split('=>')
            if len(parts) != 2:
                continue
                
            similar_values = parts[0].strip()
            current_representative = parts[1].strip()
            
            # 대표값 정규화
            normalized_rep = normalize_text(current_representative)
            
            # 기본 성분명 추출
            base_component = extract_base_component(normalized_rep)
            
            # 유사값들 처리
            similar_list = [s.strip() for s in similar_values.split(',')]
            
            for similar in similar_list:
                if not similar:
                    continue
                    
                # 유사값 정규화
                normalized_similar = normalize_text(similar)
                
                # 변형 버전들 생성
                variations = generate_variations(normalized_similar)
                
                for var in variations:
                    if var:
                        grouped_data[base_component].add(var)
                
                # 원본 유사값도 추가
                original_variations = generate_variations(similar)
                for var in original_variations:
                    if var:
                        grouped_data[base_component].add(var)
            
            # 현재 대표값도 유사값에 추가
            rep_variations = generate_variations(current_representative)
            for var in rep_variations:
                if var:
                    grouped_data[base_component].add(var)
            
            # 정규화된 대표값도 추가
            norm_rep_variations = generate_variations(normalized_rep)
            for var in norm_rep_variations:
                if var:
                    grouped_data[base_component].add(var)
            
            processed_count += 1
            
        except Exception as e:
            print(f"처리 오류: {line[:50]}... - {str(e)}")
            continue
    
    print(f"처리된 라인 수: {processed_count}")
    
    # 결과 출력
    output_lines = []
    
    for representative, similar_set in sorted(grouped_data.items()):
        if not representative:
            continue
            
        # 중복 제거 및 정렬
        similar_list = sorted(list(similar_set))
        
        # 빈 문자열 제거
        similar_list = [s for s in similar_list if s.strip()]
        
        if similar_list:
            similar_str = ', '.join(similar_list)
            output_line = f"{similar_str} => {representative}"
            output_lines.append(output_line)
    
    # 파일 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in output_lines:
            f.write(line + '\n')
    
    print(f"출력 라인 수: {len(output_lines)}")
    print(f"결과 저장: {output_file}")
    
    # 통합 예시 출력
    print("\n통합된 대표값 예시 5개:")
    for i, line in enumerate(output_lines[:5]):
        parts = line.split(' => ')
        if len(parts) == 2:
            rep_value = parts[1]
            similar_count = len(parts[0].split(', '))
            print(f"{i+1}. {rep_value} (유사값 {similar_count}개)")
    
    return len(lines), len(output_lines)

if __name__ == "__main__":
    input_file = "C:/Jimin/pharmaLex_unity/pharma_dict_submission_ready.txt"
    output_file = "C:/Jimin/pharmaLex_unity/pharma_dict_final_processed.txt"
    
    try:
        original_count, final_count = process_pharma_dict(input_file, output_file)
        print(f"\n=== 처리 완료 ===")
        print(f"원본: {original_count}개")
        print(f"최종: {final_count}개")
        print(f"통합: {original_count - final_count}개")
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")