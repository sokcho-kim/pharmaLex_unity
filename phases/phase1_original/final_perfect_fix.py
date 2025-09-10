# -*- coding: utf-8 -*-
"""
의약품 데이터 최종 처리 스크립트
- 고유명사사전 괄호 오류 및 중복 문자열 정리
- 주성분코드 매핑에서 괄호 문제 해결
- 한영 성분명 매핑을 개발 요구사항에 맞게 조정
"""

import pandas as pd
import re
from pathlib import Path
from collections import defaultdict

def to_text(x) -> str:
    if x is None or pd.isna(x):
        return ""
    s = str(x).strip()
    if s.lower() in {"nan", "none", "null", ""}:
        return ""
    return s

def fix_brackets_and_repetition(text: str) -> str:
    """텍스트에서 잘못된 괄호와 중복 문자열 정리"""
    if not text:
        return ""
    
    fixed = text.strip()
    
    # 특수한 반복 패턴 처리 (예: "selumetinib )selumetinib )" 같은 형태)
    fixed = re.sub(r'(.+?)\s*\)\1(\s*\)\1)*', r'\1', fixed)
    
    # 연속된 동일 단어 제거
    words = fixed.split()
    if len(words) > 1:
        cleaned_words = []
        prev_word = ""
        for word in words:
            clean_word = word.strip(' ()')
            if clean_word and clean_word != prev_word:
                cleaned_words.append(word)
                prev_word = clean_word
        fixed = ' '.join(cleaned_words)
    
    # 특정 문제 패턴 수정
    fixed = re.sub(r'aldesleukin\(rhIL-2,?', 'aldesleukin', fixed)
    fixed = re.sub(r'\(rh[A-Z]+-?\d*,?', '', fixed)
    fixed = re.sub(r'\(as\s+[^)]*\)', '', fixed)  
    
    # 불완전한 괄호 제거
    fixed = re.sub(r'\([^)]*:$', '', fixed)
    fixed = re.sub(r'\([^)]*:\s*$', '', fixed)
    fixed = re.sub(r'\([^)]*,$', '', fixed)
    fixed = re.sub(r'\([^)]*,\s*$', '', fixed)
    fixed = re.sub(r'\([^)]*$', '', fixed)
    
    # 용량/수량 정보 제거
    fixed = re.sub(r'\d+(?:\.\d+)?\s*(?:mg|g|ml|mL|L|%)', '', fixed)
    fixed = re.sub(r'\((?:dried|micronized|enteric coated|f\.)\)', '', fixed)
    
    # 공백 정리 및 불필요한 문자 제거
    fixed = re.sub(r'\s+', ' ', fixed)
    fixed = fixed.strip(' ,()')
    
    return fixed

def extract_korean_ingredients_enhanced():
    """주성분 마스터 파일에서 한글 성분명 추출"""
    try:
        subs_df = pd.read_csv(
            r"C:\Jimin\pharmaLex_unity\data\건강보험심사평가원_약가마스터_의약품주성분_20241014.csv",
            encoding='cp949', dtype=str
        )
        subs_df.columns = ['주성분코드', '약효분류코드', '제형', '일반명', '분류번호', '투여경로', '함량', '단위']
        
        korean_map = {}
        for _, row in subs_df.iterrows():
            code = to_text(row['주성분코드'])
            ingredient = to_text(row['일반명'])
            if code and ingredient and re.search(r'[가-힣]', ingredient):
                korean_map[code] = fix_brackets_and_repetition(ingredient)
                
        return korean_map
    except Exception as e:
        print(f"한글 성분명 추출 실패: {e}")
        return {}

def normalize_ingredient_for_grouping(ingredient: str) -> str:
    """성분명을 그룹핑을 위한 표준 형식으로 변환"""
    if not ingredient:
        return ""
    normalized = ingredient.lower()
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized

def clean_brand_name(name: str) -> str:
    if not name:
        return ""
    clean = re.sub(r'\([^)]*\)', '', name)
    clean = re.sub(r'\d+(?:\.\d+)?\s*(?:mg|g|ml|mL|L|%)', '', clean)
    clean = re.sub(r'_.*$', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def generate_korean_variants(korean_name: str) -> list:
    """한글 성분명의 다양한 표기 변형 생성"""
    if not korean_name:
        return []
    
    variants = [korean_name]
    
    # 공백 제거한 형태
    no_space = korean_name.replace(' ', '')
    if no_space != korean_name:
        variants.append(no_space)
    
    # 하이픈을 공백으로 바꾼 형태
    if '-' in korean_name:
        variants.append(korean_name.replace('-', ' '))
    
    # 하이픈 제거한 형태
    if '-' in korean_name:
        variants.append(korean_name.replace('-', ''))
        
    return list(set(variants))

def final_perfect_fix():
    """의약품 데이터 최종 처리 메인 함수"""
    print("=== 의약품 데이터 최종 처리 시작 ===")
    
    input_file = Path("solution/fixed_out/01_fixed_applied_price_enriched.csv")
    df = pd.read_csv(input_file)
    
    output_dir = Path("solution/developer_output_perfect")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 한글 성분명 데이터 로드
    korean_ingredients = extract_korean_ingredients_enhanced()
    print(f"한글 성분명: {len(korean_ingredients):,}개")
    
    # 성분명별로 관련 정보를 그룹핑
    ingredient_groups = defaultdict(lambda: {
        'codes': set(),
        'ko_names': set(),
        'en_names': set(),
        'brands': set(),
        'companies': set()
    })
    
    print("데이터 처리 중...")
    for idx, row in df.iterrows():
        if idx % 10000 == 0:
            print(f"  진행: {idx:,}/{len(df):,}")
            
        substance_code = to_text(row['주성분코드'])
        product_name = to_text(row['제품명'])
        brand_name = to_text(row['품명_정제'])
        ingredient_ko = to_text(row['성분명_KO'])
        ingredient_en = to_text(row['성분명_EN'])
        company_name = to_text(row['업체명'])
        
        if not substance_code:
            continue
            
        # 성분명 정리 및 오류 수정
        ko_ingredient = fix_brackets_and_repetition(ingredient_ko or korean_ingredients.get(substance_code, ""))
        en_ingredient = fix_brackets_and_repetition(ingredient_en)
        
        # 그룹핑용 키 생성 (영문명을 우선 사용)
        grouping_key = ""
        if en_ingredient:
            grouping_key = normalize_ingredient_for_grouping(en_ingredient)
        elif ko_ingredient:
            grouping_key = normalize_ingredient_for_grouping(ko_ingredient)
            
        if not grouping_key:
            continue
            
        group = ingredient_groups[grouping_key]
        group['codes'].add(substance_code)
        if ko_ingredient:
            group['ko_names'].add(ko_ingredient)
        if en_ingredient:
            group['en_names'].add(en_ingredient)
            
        clean_brand = clean_brand_name(brand_name or product_name)
        if clean_brand:
            group['brands'].add(clean_brand)
        if company_name:
            group['companies'].add(company_name)
    
    print("최종 파일 생성...")
    
    # 1. 고유명사 사전 생성
    all_proper_nouns = set()
    for group in ingredient_groups.values():
        all_proper_nouns.update(group['ko_names'])
        all_proper_nouns.update(group['en_names'])
        all_proper_nouns.update(group['companies'])
    
    with open(output_dir / "1_고유명사사전_perfect.txt", "w", encoding="utf-8") as f:
        for noun in sorted(all_proper_nouns):
            if len(noun.strip()) > 1:
                fixed_noun = fix_brackets_and_repetition(noun)
                if fixed_noun and not re.search(r'\)[^)]*\)', fixed_noun):
                    f.write(f"{fixed_noun}\n")
    
    # 2. 주성분코드 매핑 생성
    with open(output_dir / "2_주성분코드매핑_perfect.txt", "w", encoding="utf-8") as f:
        for group_key, group in sorted(ingredient_groups.items()):
            representative_en = list(group['en_names'])[0] if group['en_names'] else ""
            representative_ko = list(group['ko_names'])[0] if group['ko_names'] else ""
            
            all_names = []
            if representative_ko:
                all_names.append(fix_brackets_and_repetition(representative_ko))
            if representative_en:
                all_names.append(fix_brackets_and_repetition(representative_en))
            
            brands = sorted(group['brands'])[:10]
            all_names.extend([fix_brackets_and_repetition(b) for b in brands])
            
            codes_str = ", ".join(sorted(group['codes'])[:3])
            if all_names:
                names_str = ", ".join([n for n in all_names if n and not re.search(r'\)[^)]*\)', n)])
                f.write(f"{codes_str} => {names_str}\n")
    
    # 3. 성분 한글/영문 매핑 (영문, 한글 변형들)
    with open(output_dir / "3_성분한글영문_perfect.txt", "w", encoding="utf-8") as f:
        for group_key, group in sorted(ingredient_groups.items()):
            representative_en = list(group['en_names'])[0] if group['en_names'] else ""
            representative_ko = list(group['ko_names'])[0] if group['ko_names'] else ""
            
            if representative_en and representative_ko:
                en_fixed = fix_brackets_and_repetition(representative_en)
                ko_fixed = fix_brackets_and_repetition(representative_ko)
                
                if en_fixed and ko_fixed and not re.search(r'\)[^)]*\)', en_fixed + ko_fixed):
                    # 한글명의 다양한 변형 생성
                    ko_variants = generate_korean_variants(ko_fixed)
                    
                    # 영문명과 한글 변형 2개까지 결합
                    parts = [en_fixed] + ko_variants[:2]
                    
                    if len(parts) >= 2:
                        f.write(f"{', '.join(parts)}\n")
            elif representative_en:
                en_fixed = fix_brackets_and_repetition(representative_en)
                if en_fixed and not re.search(r'\)[^)]*\)', en_fixed):
                    f.write(f"{en_fixed}\n")
            elif representative_ko:
                ko_fixed = fix_brackets_and_repetition(representative_ko)
                if ko_fixed and not re.search(r'\)[^)]*\)', ko_fixed):
                    ko_variants = generate_korean_variants(ko_fixed)
                    if ko_variants:
                        f.write(f"{', '.join(ko_variants[:3])}\n")
    
    # 4. 검색용 유의어사전 생성
    with open(output_dir / "4_검색기용유의어사전_perfect.txt", "w", encoding="utf-8") as f:
        for group_key, group in sorted(ingredient_groups.items()):
            all_terms = set()
            all_terms.update(group['ko_names'])
            all_terms.update(group['en_names'])
            all_terms.update(group['brands'])
            
            if len(all_terms) > 1:
                fixed_terms = [fix_brackets_and_repetition(t) for t in sorted(all_terms)]
                fixed_terms = [t for t in fixed_terms if t and not re.search(r'\)[^)]*\)', t)][:15]
                if len(fixed_terms) > 1:
                    f.write(f"{', '.join(fixed_terms)}\n")
    
    # 5. 주성분별 약품그룹 생성
    with open(output_dir / "5_주성분별약품그룹_perfect.txt", "w", encoding="utf-8") as f:
        for group_key, group in sorted(ingredient_groups.items()):
            if len(group['brands']) > 1:
                representative = (list(group['ko_names'])[0] if group['ko_names'] else 
                                list(group['en_names'])[0] if group['en_names'] else 
                                list(group['brands'])[0])
                
                fixed_representative = fix_brackets_and_repetition(representative)
                all_brands = sorted(group['brands'])
                fixed_brands = [fix_brackets_and_repetition(b) for b in all_brands]
                fixed_brands = [b for b in fixed_brands if b and not re.search(r'\)[^)]*\)', b)]
                
                if fixed_representative and fixed_brands and not re.search(r'\)[^)]*\)', fixed_representative):
                    f.write(f"{fixed_representative}: {', '.join(fixed_brands)}\n")
    
    print(f"\n=== 의약품 데이터 최종 처리 완료 ===")
    print(f"결과 저장: {output_dir.resolve()}")
    print("완료: 괄호 오류 및 중복 문자열 처리")
    print("완료: 한영 성분명 매핑 형식 조정")
    print("완료: 데이터 품질 문제 해결")
    
    # 결과 검증
    print(f"\n파일별 결과:")
    for file in output_dir.glob("*.txt"):
        with open(file, 'r', encoding='utf-8') as f:
            lines = len(f.readlines())
        print(f"- {file.name}: {lines:,}개")

if __name__ == "__main__":
    final_perfect_fix()