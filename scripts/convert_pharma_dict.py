import re
import unicodedata

def normalize_text(text):
    """텍스트 정규화 및 변환 규칙 적용"""
    # 유니코드 정규화
    text = unicodedata.normalize('NFKC', text)
    
    # 그리스 문자 치환 (더 포괄적으로)
    text = text.replace('α', 'alfa').replace('alpha', 'alfa').replace('Alpha', 'alfa')
    text = text.replace('β', 'beta').replace('Beta', 'beta')
    text = text.replace('γ', 'gamma').replace('Gamma', 'gamma')
    text = text.replace('δ', 'delta').replace('Delta', 'delta')
    text = text.replace('ε', 'epsilon').replace('Epsilon', 'epsilon')
    text = text.replace('ζ', 'zeta').replace('Zeta', 'zeta')
    text = text.replace('η', 'eta').replace('Eta', 'eta')
    text = text.replace('θ', 'theta').replace('Theta', 'theta')
    
    # 용량 제거 (더 포괄적인 패턴)
    # 숫자+단위 패턴들
    text = re.sub(r'\s*\d+(?:\.\d+)?\s*(?:㎍|㎎|㎖|㎘|mg|ug|μg|ml|mL|g|kg|IU|KI\.U|w/w|v/v|%|ppm|ppb|U|unit|units)\b', '', text, flags=re.IGNORECASE)
    
    # 비율 제거 (예: 4:1, 1:4 등)
    text = re.sub(r'\s*\d+:\d+\s*', '', text)
    
    # 단위/용량 토큰 제거 (더 포괄적)
    units = ['w/w', 'v/v', 'w/v', 'v/w', 'KI.U', 'KI.u', 'IU', 'i.u.', 'ext.', 'ext', 
             'mg', 'ug', 'μg', 'ml', 'mL', 'g', 'kg', 'ppm', 'ppb', 'unit', 'units', 'U']
    for unit in units:
        text = re.sub(r'\b' + re.escape(unit) + r'\b', '', text, flags=re.IGNORECASE)
    
    # "/" 와 "&" 제거
    text = text.replace('/', ' ').replace('&', ' ')
    
    # 괄호 안의 내용이 용량이나 비율인 경우만 제거 (화학명 괄호는 보존)
    # 숫자+단위가 포함된 괄호만 제거
    text = re.sub(r'\([^)]*\d+\s*(?:mg|ug|μg|ml|mL|g|kg|IU|KI\.U|w/w|v/v|%|ppm|ppb|U|unit|units)[^)]*\)', '', text, flags=re.IGNORECASE)
    
    # 연속된 공백, 탭, 줄바꿈 정리
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def process_line(line):
    """각 라인을 처리하여 유의어 사전 형태로 변환"""
    line = line.strip()
    if not line:
        return None
    
    # 라인에서 숫자→주성분명: 약품명들 파싱
    
    # Try to match: number followed by separator, then component name, then colon and drug names
    # First check if line has the expected structure
    if ':' not in line:
        return None
    
    # Split by colon first
    parts = line.split(':', 1)
    if len(parts) != 2:
        return None
    
    left_part = parts[0].strip()
    drug_names = parts[1].strip()
    
    # Extract component name
    # Two patterns: "number-component" or just "component"
    if re.match(r'^\d+', left_part):
        # Pattern: digits + separator + component name
        match = re.match(r'^\d+[\→\-\s]*(.+)', left_part)
        if not match:
            return None
        main_component = match.group(1).strip()
    else:
        # Pattern: just component name
        main_component = left_part.strip()
    
    # 약품명들을 콤마로 분리
    drug_list = [name.strip() for name in drug_names.split(',') if name.strip()]
    
    if not drug_list:
        return None
    
    # 각 약품명에 정규화 규칙 적용
    normalized_drugs = []
    
    for drug in drug_list:
        # 원본과 괄호 제거 버전 모두 추가
        normalized_drugs.append(normalize_text(drug))
        
        # 괄호가 있으면 괄호 제거 버전도 추가
        if '(' in drug and ')' in drug:
            no_parentheses = re.sub(r'\([^)]*\)', '', drug).strip()
            if no_parentheses and no_parentheses != drug:
                normalized_drugs.append(normalize_text(no_parentheses))
    
    # 중복 제거 및 빈 문자열 제거
    unique_drugs = []
    seen = set()
    for drug in normalized_drugs:
        if drug and drug not in seen:
            unique_drugs.append(drug)
            seen.add(drug)
    
    if not unique_drugs:
        return None
    
    # 주성분명도 정규화
    normalized_main = normalize_text(main_component)
    
    # 결과 포맷: 유사값1, 유사값2, ... => 대표값
    return f"{', '.join(unique_drugs)} => {normalized_main}"

def main():
    input_file = r"C:\Jimin\pharmaLex_unity\phases\phase2_4to5\output\5_주성분별약품그룹_from_4.txt"
    output_file = r"C:\Jimin\pharmaLex_unity\pharma_unidirectional_dict.txt"
    
    results = []
    
    # Read as binary and try to decode with different encodings
    try:
        with open(input_file, 'rb') as f:
            raw_data = f.read()
    except Exception as e:
        print(f"Error reading binary file: {e}")
        return
    
    encodings = ['cp949', 'euc-kr', 'utf-8', 'utf-8-sig']
    file_content = None
    
    for encoding in encodings:
        try:
            decoded_text = raw_data.decode(encoding)
            lines = decoded_text.splitlines()
            if lines:
                # Just use the first encoding that works, even if Korean is not in first line
                file_content = [line + '\n' for line in lines]
                print(f"Successfully decoded with encoding: {encoding}")
                print(f"First line preview: {lines[0][:100]}")
                # Check for Korean in any of the first 10 lines
                has_korean = any('가' <= char <= '힣' for line in lines[:10] for char in line)
                if has_korean:
                    print("Korean characters detected in file")
                break
        except UnicodeDecodeError as e:
            print(f"Encoding {encoding} failed with error: {e}")
            continue
    
    if file_content is None:
        print("Could not read file with any encoding")
        return
    
    try:
        total_lines = len(file_content)
        print(f"Processing {total_lines} lines...")
        
        for line_num, line in enumerate(file_content, 1):
            try:
                result = process_line(line)
                if result:
                    results.append(result)
                
                # Progress indicator
                if line_num % 500 == 0:
                    print(f"Processed {line_num}/{total_lines} lines, {len(results)} results so far")
                    
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                continue
    except Exception as e:
        print(f"Error reading input file: {e}")
        return
    
    # 결과 저장
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(result + '\n')
    except Exception as e:
        print(f"Error writing output file: {e}")
        return
    
    print(f"Conversion completed: {len(results)} items generated.")
    print(f"Output file: {output_file}")
    
    # 처음 10개 결과 미리보기
    print("\nFirst 10 items preview:")
    for i, result in enumerate(results[:10], 1):
        print(f"{i:2d}: {result}")
        
    if len(results) > 10:
        print(f"... and {len(results) - 10} more items")

if __name__ == "__main__":
    main()