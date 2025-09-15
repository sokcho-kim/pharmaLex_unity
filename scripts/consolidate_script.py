import re
import sys

# 파일 읽기
with open('C:/Jimin/pharmaLex_unity/pharma_unidirectional_dict_submission.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 각 줄을 파싱
entries = {}
for line in lines:
    line = line.strip()
    if ' => ' in line:
        left, right = line.split(' => ', 1)
        entries[right] = left

# 염 형태를 제거하여 기본 성분명을 추출하는 함수
def get_base_component(component):
    component = component.lower()
    
    patterns = [
        r'hydrochloride.*$',
        r'hcl.*$', 
        r'hydrobromide.*$',
        r'hbr.*$',
        r'sulfate.*$',
        r'황산.*$',
        r'acetate.*$',
        r'아세테이트.*$',
        r'dihydrochloride.*$',
        r'monohydrochloride.*$',
        r'bisulfate.*$',
        r'tartrate.*$',
        r'maleate.*$',
        r'succinate.*$',
        r'phosphate.*$',
        r'nitrate.*$',
        r'citrate.*$',
        r'fumarate.*$',
        r'mesylate.*$',
        r'besylate.*$',
        r'tosylate.*$',
        r'hemisulfate.*$',
        r'monosulfate.*$',
        r'disulfate.*$',
        r'malate.*$',
    ]
    
    for pattern in patterns:
        component = re.sub(pattern, '', component)
    
    return component.strip()

# 기본 성분명과 원래 항목들 매핑
base_to_entries = {}
for representative, synonyms in entries.items():
    base = get_base_component(representative)
    if base not in base_to_entries:
        base_to_entries[base] = {}
    base_to_entries[base][representative] = synonyms

# 통합된 결과 생성
consolidated_entries = {}

for base, items in base_to_entries.items():
    if len(items) == 1:
        # 통합이 불필요한 경우 그대로 유지
        rep, syns = list(items.items())[0]
        consolidated_entries[rep] = syns
    else:
        # 통합이 필요한 경우
        # 1. 기본 성분명을 대표값으로 선택 (가장 간단한 형태)
        representatives = list(items.keys())
        
        # 기본형 우선 선택 (염이 없는 것)
        base_form = None
        for rep in representatives:
            if get_base_component(rep) == rep.lower():
                base_form = rep.lower()
                break
        
        if base_form is None:
            # 기본형이 없으면 가장 짧은 것 선택
            base_form = min(representatives, key=len).lower()
        
        # 2. 모든 유사값들을 합치기
        all_synonyms = []
        for rep, syns in items.items():
            all_synonyms.extend(syns.split(', '))
            # 원래 대표값도 유사값에 포함 (기본형이 아닌 경우)
            if rep.lower() != base_form:
                all_synonyms.append(rep)
        
        # 중복 제거하고 정렬
        unique_synonyms = sorted(list(set(all_synonyms)))
        
        consolidated_entries[base_form] = ', '.join(unique_synonyms)

# 결과를 파일로 저장
with open('C:/Jimin/pharmaLex_unity/pharma_unidirectional_dict_ultimate.txt', 'w', encoding='utf-8') as f:
    for i, (representative, synonyms) in enumerate(sorted(consolidated_entries.items()), 1):
        f.write(f"{synonyms} => {representative}\n")

print(f"통합 완료! 총 {len(consolidated_entries)}개 항목으로 정리되었습니다.")

# 통합 결과 요약 출력
print("\n=== 통합된 항목들 요약 ===")
for base, items in sorted(base_to_entries.items()):
    if len(items) > 1:
        representatives = list(items.keys())
        base_form = None
        for rep in representatives:
            if get_base_component(rep) == rep.lower():
                base_form = rep.lower()
                break
        if base_form is None:
            base_form = min(representatives, key=len).lower()
        
        print(f"[{base}] {representatives} => {base_form}")