import re

def remove_dosage_units(text):
    """용량/단위/비율을 엄격하게 제거"""
    if not text:
        return ""
    
    # 숫자+단위 패턴들 (더 포괄적으로)
    patterns = [
        r'\d+\.?\d*\s*(?:mg|mcg|㎍|g|kg|ml|mL|l|L|IU|단위|호|%|㎎|㎖|㎞|㎝|mm|cm|km|아이유)',
        r'\d+\.?\d*\s*(?:마이크로그람|그람|밀리그람)',
        r'\d+\s*:\s*\d+',  # 비율
        r'\d+\.?\d*\s*%',   # 퍼센트
        r'^\d+\.?\d*\s*',   # 시작 부분 숫자
        r'\s*\d+\.?\d*$',   # 끝 부분 숫자
        r'\d+\.?\d*(?=\s)',  # 공백 앞 숫자
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text.strip()

def clean_text(text, keep_hyphen=False):
    """텍스트를 엄격한 기준에 맞게 정리"""
    if not text:
        return ""
    
    # 1. 용량/단위/비율 완전 제거
    text = remove_dosage_units(text)
    
    # 2. 불필요 토큰 완전 제거
    text = text.replace('ext.', '')
    text = text.replace('.', '')
    text = text.replace('/', '')
    text = text.replace('&', '')
    
    if not keep_hyphen:
        text = text.replace('-', '')
    
    # 3. 그리스 문자 치환
    text = re.sub(r'α|alpha', 'alfa', text, flags=re.IGNORECASE)
    text = re.sub(r'β|beta', 'beta', text, flags=re.IGNORECASE)
    text = re.sub(r'γ|gamma', 'gamma', text, flags=re.IGNORECASE)
    
    # 공백 정리
    text = re.sub(r'\s+', '', text)
    text = text.strip()
    
    return text

def process_line(line):
    """한 줄을 처리하여 엄격한 기준에 맞게 변환"""
    line = line.strip()
    if not line or '=>' not in line:
        return None
    
    # 라인 번호 제거
    if '→' in line:
        line = line.split('→', 1)[1]
    
    parts = line.split('=>')
    if len(parts) != 2:
        return None
    
    left_part = parts[0].strip()
    right_part = parts[1].strip()
    
    # 왼쪽 부분 (유사값들) 처리
    similar_values = [val.strip() for val in left_part.split(',') if val.strip()]
    
    # 각 유사값을 정리
    cleaned_similar_values = set()
    
    for val in similar_values:
        if not val:
            continue
            
        # 기본 정리 (하이픈 제거)
        cleaned = clean_text(val, keep_hyphen=False)
        if cleaned and len(cleaned) > 1:  # 길이가 1보다 큰 것만
            cleaned_similar_values.add(cleaned)
        
        # 하이픈이 있는 경우 - 하이픈 유지 버전도 추가
        if '-' in val:
            with_hyphen_cleaned = clean_text(val, keep_hyphen=True)
            if with_hyphen_cleaned and len(with_hyphen_cleaned) > 1:
                cleaned_similar_values.add(with_hyphen_cleaned)
        
        # 괄호가 있는 경우 - 괄호 제거 버전도 추가
        if '(' in val and ')' in val:
            no_brackets = re.sub(r'\([^)]*\)', '', val).strip()
            if no_brackets:
                no_brackets_cleaned = clean_text(no_brackets, keep_hyphen=False)
                if no_brackets_cleaned and len(no_brackets_cleaned) > 1:
                    cleaned_similar_values.add(no_brackets_cleaned)
                    
                # 괄호 제거하고 하이픈도 유지하는 버전
                if '-' in no_brackets:
                    no_brackets_with_hyphen = clean_text(no_brackets, keep_hyphen=True)
                    if no_brackets_with_hyphen and len(no_brackets_with_hyphen) > 1:
                        cleaned_similar_values.add(no_brackets_with_hyphen)
    
    # 오른쪽 부분 (대표값) 처리
    representative_value = right_part
    
    # 괄호 제거 버전을 대표값으로 사용
    if '(' in right_part and ')' in right_part:
        no_brackets = re.sub(r'\([^)]*\)', '', right_part).strip()
        if no_brackets:
            representative_value = no_brackets
    
    # 대표값 정리 (하이픈 제거)
    representative_value = clean_text(representative_value, keep_hyphen=False)
    
    # 빈 값들 제거하고 대표값과 다른 것들만 남김
    cleaned_similar_values = [val for val in cleaned_similar_values 
                             if val and val != representative_value and len(val) > 1]
    
    if not cleaned_similar_values or not representative_value or len(representative_value) <= 1:
        return None
    
    # 정렬하여 일관성 유지
    cleaned_similar_values = sorted(list(set(cleaned_similar_values)))
    
    return f"{', '.join(cleaned_similar_values)} => {representative_value}"

# 파일 처리
input_file = r'C:\Jimin\pharmaLex_unity\pharma_unidirectional_dict_cleaned.txt'
output_file = r'C:\Jimin\pharmaLex_unity\pharma_unidirectional_dict_final.txt'

processed_lines = []
seen_mappings = set()
line_count = 0
skipped_count = 0

print("Processing pharmaceutical dictionary with STRICT criteria...")

with open(input_file, 'r', encoding='utf-8') as f:
    for line_num, line in enumerate(f, 1):
        line_count += 1
        try:
            processed = process_line(line)
            if processed:
                if processed not in seen_mappings:
                    processed_lines.append(processed)
                    seen_mappings.add(processed)
            else:
                skipped_count += 1
                
            if line_count % 500 == 0:
                print(f"Processed {line_count} lines, kept {len(processed_lines)} unique entries, skipped {skipped_count}...")
                
        except Exception as e:
            skipped_count += 1
            print(f"Error processing line {line_num}: {e}")

print(f"\nProcessing completed:")
print(f"Total input lines: {line_count}")
print(f"Total processed lines: {len(processed_lines)}")
print(f"Skipped lines: {skipped_count}")

# 결과 저장
with open(output_file, 'w', encoding='utf-8') as f:
    for line in processed_lines:
        f.write(line + '\n')

print(f"Results saved to: {output_file}")

# 특정 예시들 확인
test_examples = [
    "디칼시연질캅셀0.5마이크로그람",
    "부산대학교2-데옥시-2-플루오로-D-글루코스", 
    "보인-씨.피.디.에이원항응고액",
    "alpha-tocopherol 100IU"
]

print("\nTesting specific examples:")
for example in test_examples:
    cleaned = clean_text(example, keep_hyphen=False)
    cleaned_with_hyphen = clean_text(example, keep_hyphen=True)
    print(f"Original: {example}")
    print(f"Cleaned: {cleaned}")
    print(f"With hyphen: {cleaned_with_hyphen}")
    print()