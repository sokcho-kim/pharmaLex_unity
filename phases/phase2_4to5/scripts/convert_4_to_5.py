#!/usr/bin/env python3
"""
Phase 2: Convert file 4 (검색기용유의어사전) to file 5 (주성분별약품그룹) format

Input format:  성분명, 약품명1, 약품명2, ...
Output format: 성분명: 약품명1, 약품명2, ...

변환 규칙:
- 첫 번째 콤마를 콜론(:)으로 변경
- 나머지 구조는 동일하게 유지
- 줄 번호 형식 유지 (number→content)
"""

import os

def convert_file4_to_file5(input_file, output_file):
    """Convert file 4 format to file 5 format"""
    
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        return
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    converted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Extract line number and content
        if '→' in line:
            line_num_part, content = line.split('→', 1)
        else:
            line_num_part = ""
            content = line
            
        # Convert comma after first component to colon
        if ', ' in content:
            # Find first comma that separates component from drug names
            first_comma_idx = content.find(', ')
            if first_comma_idx != -1:
                component_name = content[:first_comma_idx]
                drug_names = content[first_comma_idx + 2:]  # Skip ', '
                converted_content = f"{component_name}: {drug_names}"
            else:
                converted_content = content
        else:
            # Handle lines with only component name (no drugs)
            converted_content = content
            
        # Reconstruct the line with line number if it existed
        if line_num_part:
            converted_line = f"{line_num_part}→{converted_content}"
        else:
            converted_line = converted_content
            
        converted_lines.append(converted_line)
    
    # Write output file
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in converted_lines:
            f.write(f"{line}\n")
    
    print(f"Conversion completed!")
    print(f"- Processed {len(converted_lines)} lines")
    print(f"- Output saved to: {output_file}")

def main():
    # File paths
    input_file = "../input/4_검색기용유의어사전_perfect.txt"
    output_file = "../output/5_주성분별약품그룹_from_4.txt"
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Convert file
    convert_file4_to_file5(input_file, output_file)

if __name__ == "__main__":
    main()