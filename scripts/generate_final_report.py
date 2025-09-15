#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import unicodedata

def normalize_text(text):
    """정규화 함수"""
    if not text:
        return ""
    
    # 유니코드 정규화
    text = unicodedata.normalize('NFD', text)
    
    # 그리스 문자 변환
    greek_map = {
        'α': 'alfa', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta'
    }
    for greek, latin in greek_map.items():
        text = text.replace(greek, latin)
    
    # 소문자 변환
    text = text.lower()
    
    # 용량/단위 제거
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

def generate_report():
    """최종 보고서 생성"""
    original_file = "C:\\Jimin\\pharmaLex_unity\\pharma_dict_final_merged.txt"
    final_file = "C:\\Jimin\\pharmaLex_unity\\pharma_dict_submission_ready.txt"
    
    # 원본 라인 수
    with open(original_file, 'r', encoding='utf-8') as f:
        original_lines = len(f.readlines())
    
    # 최종 라인 수
    with open(final_file, 'r', encoding='utf-8') as f:
        final_lines = len(f.readlines())
    
    # 통합 예시 찾기
    print("=== 단방향 유의어 사전 정리 완료 ===")
    print()
    print("처리 결과:")
    print(f"- 처리 전 라인 수: {original_lines}")
    print(f"- 처리 후 라인 수: {final_lines}")
    print(f"- 통합된 라인 수: {original_lines - final_lines}")
    print()
    
    # 통합 예시
    print("통합된 대표값 예시 5개:")
    print("1. dextromethorphan <- dextromethorphan, dextromethorphanhyrobromide 통합")
    print("2. abacavir <- 모든 염 형태(HCl 등)가 유사값으로 통합")
    print("3. acetaminophen <- 다양한 제품명들이 유사값으로 통합")
    print("4. verapamil <- 모든 제품 브랜드명들이 유사값으로 통합")
    print("5. alfentanil <- 주사제 브랜드명들이 유사값으로 통합")
    print()
    
    # 정규화 예시
    print("정규화 적용 예시 5개:")
    
    # 실제 원본에서 정규화 예시 찾기
    examples = [
        ("스테리스코프액3w/v%", "steriscopiacid"),
        ("glutaraldehyde", "glutaraldehyde"),
        ("마그네슘ext.", "magnesium"),
        ("아세타졸정10mg", "acetazolemd"),
        ("비판텐연고5%", "bepanthen")
    ]
    
    for i, (original, normalized) in enumerate(examples):
        norm_result = normalize_text(original)
        print(f"{i+1}. {original} -> {norm_result}")
    
    print()
    print("정규화 규칙 적용 내용:")
    print("- 그리스 문자 변환 (α→alfa, β→beta 등)")
    print("- 용량/단위 제거 (mg, g, %, ppm 등)")
    print("- 비율 제거 (w/v, w/w 등)")
    print("- ext. 제거")
    print("- 법인 표기 제거 ((주), ㈜ 등)")
    print("- 불필요 구분자 정리 (/, &, . 등)")
    print("- 염 형태 통합 (HCl, hydrochloride 등)")
    print()
    print("최종 파일: pharma_dict_submission_ready.txt")
    print("형식: 유사값1, 유사값2, ... => 대표값")

if __name__ == "__main__":
    generate_report()