import re

def clean_text(text):
    """텍스트를 엄격한 기준에 맞게 정리"""
    original_text = text
    
    # 1. 용량/단위/비율 완전 제거
    # 숫자+단위 제거 (다양한 단위 패턴)
    patterns_to_remove = [
        r'\d+\.?\d*\s*(?:mg|mcg|㎍|g|kg|ml|mL|l|IU|단위|호|%|㎎|㎖|㎞|㎝|mm|cm|km|마이크로그람|그람|밀리그람)',
        r'\d+\s*:\s*\d+',  # 비율
        r'\d+\.?\d*%',     # 퍼센트
        r'\d+\.?\d*$',     # 끝에 오는 숫자
        r'\d+\.?\d*(?=\s)',  # 공백 앞의 숫자
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # 2. 불필요 토큰 완전 제거
    text = text.replace('ext.', '')
    text = text.replace('.', '')
    text = text.replace('/', '')
    text = text.replace('&', '')
    
    # 3. 그리스 문자 치환
    text = re.sub(r'α|alpha', 'alfa', text, flags=re.IGNORECASE)
    text = re.sub(r'β|beta', 'beta', text, flags=re.IGNORECASE)  
    text = re.sub(r'γ|gamma', 'gamma', text, flags=re.IGNORECASE)
    
    # 공백 정리
    text = re.sub(r'\s+', '', text)
    text = text.strip()
    
    return text

def clean_text_keep_hyphen(text):
    """하이픈을 유지하면서 텍스트 정리"""
    # 1. 용량/단위/비율 완전 제거
    patterns_to_remove = [
        r'\d+\.?\d*\s*(?:mg|mcg|㎍|g|kg|ml|mL|l|IU|단위|호|%|㎎|㎖|㎞|㎝|mm|cm|km|마이크로그람|그람|밀리그람)',
        r'\d+\s*:\s*\d+',
        r'\d+\.?\d*%',
        r'\d+\.?\d*$',
        r'\d+\.?\d*(?=\s)',
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # 2. 불필요 토큰 제거 (하이픈 제외)
    text = text.replace('ext.', '')
    text = text.replace('.', '')
    text = text.replace('/', '')
    text = text.replace('&', '')
    
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
    similar_values = [val.strip() for val in left_part.split(',')]
    
    # 각 유사값을 정리
    cleaned_similar_values = set()  # 중복 제거를 위해 set 사용
    
    for val in similar_values:
        if not val:
            continue
            
        # 기본 정리 - 하이픈 제거
        cleaned = clean_text(val)
        if cleaned:
            cleaned_similar_values.add(cleaned)
        
        # 괄호 처리 - 괄호 있는 버전과 없는 버전 둘 다 추가
        if '(' in val and ')' in val:
            no_brackets = re.sub(r'\([^)]*\)', '', val).strip()
            if no_brackets:
                no_brackets_cleaned = clean_text(no_brackets)
                if no_brackets_cleaned:
                    cleaned_similar_values.add(no_brackets_cleaned)
        
        # 하이픈 처리 - 하이픈 있는 버전과 없는 버전 둘 다 추가
        if '-' in val:
            # 하이픈 유지 버전
            with_hyphen_cleaned = clean_text_keep_hyphen(val)
            if with_hyphen_cleaned:
                cleaned_similar_values.add(with_hyphen_cleaned)
                
            # 괄호가 있으면서 하이픈도 있는 경우
            if '(' in val and ')' in val:
                no_brackets_with_hyphen = re.sub(r'\([^)]*\)', '', val).strip()
                if no_brackets_with_hyphen:
                    no_brackets_with_hyphen_cleaned = clean_text_keep_hyphen(no_brackets_with_hyphen)
                    if no_brackets_with_hyphen_cleaned:
                        cleaned_similar_values.add(no_brackets_with_hyphen_cleaned)
    
    # 오른쪽 부분 (대표값) 처리
    representative_value = clean_text(right_part)
    
    # 괄호 제거 버전을 대표값으로 사용
    if '(' in right_part and ')' in right_part:
        no_brackets = re.sub(r'\([^)]*\)', '', right_part).strip()
        if no_brackets:
            representative_value = clean_text(no_brackets)
    
    # 빈 값들 제거하고 대표값과 다른 것들만 남김
    cleaned_similar_values = [val for val in cleaned_similar_values if val and val != representative_value]
    
    if not cleaned_similar_values or not representative_value:
        return None
    
    # 정렬하여 일관성 유지
    cleaned_similar_values.sort()
    
    return f"{', '.join(cleaned_similar_values)} => {representative_value}"

# 파일 처리
input_file = r'C:\Jimin\pharmaLex_unity\pharma_unidirectional_dict_cleaned.txt'
output_file = r'C:\Jimin\pharmaLex_unity\pharma_unidirectional_dict_final.txt'

processed_lines = []
seen_mappings = set()  # 중복 제거용
line_count = 0

print("Processing pharmaceutical dictionary...")

with open(input_file, 'r', encoding='utf-8') as f:
    for line_num, line in enumerate(f, 1):
        line_count += 1
        try:
            processed = process_line(line)
            if processed and processed not in seen_mappings:
                processed_lines.append(processed)
                seen_mappings.add(processed)
                if line_count % 100 == 0:
                    print(f"Processed {line_count} lines, kept {len(processed_lines)} unique entries...")
        except Exception as e:
            print(f"Error processing line {line_num}: {e}")
            continue

print(f"\nTotal input lines: {line_count}")
print(f"Total processed lines: {len(processed_lines)}")

# 결과 저장
with open(output_file, 'w', encoding='utf-8') as f:
    for line in processed_lines:
        f.write(line + '\n')

print(f"Results saved to: {output_file}")

# 처리 결과 샘플 출력
print("\nSample results:")
for i, line in enumerate(processed_lines[:10]):
    print(f"{i+1}: {line}")