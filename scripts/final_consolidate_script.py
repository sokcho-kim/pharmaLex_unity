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

# 염 형태를 제거하여 기본 성분명을 추출하는 함수 (더 정교하게)
def get_base_component(component):
    original = component
    component = component.lower()
    
    # 매우 구체적인 염 패턴들
    salt_patterns = [
        # HCl 형태들
        (r'hydrochloride.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'hcl.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'dihydrochloride.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'monohydrochloride.*?(?:hydrate)?(?:·.*)?$', ''),
        
        # HBr 형태들  
        (r'hydrobromide.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'hbr.*?(?:hydrate)?(?:·.*)?$', ''),
        
        # 기타 염들
        (r'sulfate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'황산.*?(?:수화물)?(?:·.*)?$', ''),
        (r'bisulfate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'hemisulfate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'monosulfate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'disulfate.*?(?:hydrate)?(?:·.*)?$', ''),
        
        (r'acetate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'아세테이트.*?(?:수화물)?(?:·.*)?$', ''),
        
        (r'tartrate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'maleate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'succinate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'phosphate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'nitrate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'citrate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'fumarate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'mesylate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'besylate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'besylatel.*?(?:hydrate)?(?:·.*)?$', ''),  # 오타 포함
        (r'tosylate.*?(?:hydrate)?(?:·.*)?$', ''),
        (r'malate.*?(?:hydrate)?(?:·.*)?$', ''),
    ]
    
    for pattern, replacement in salt_patterns:
        component = re.sub(pattern, replacement, component)
    
    return component.strip()

# 알려진 통합 매핑 (수동으로 지정)
known_consolidations = {
    # 기본 성분명: [통합될 대표값들]
    'alkyldiaminoethylglycin': ['alkyldiaminoethylglycin', 'alkyldiaminoethylglycinhydrochloridesolution'],
    'calcium': ['calciumacetate', 'calciumcitrate', 'calciumcitratemalate'], 
    'cefepime': ['cefepime', 'cefepimehydrochloridehydrate·larginine'],
    'chondroitin': ['chondroitin', 'chondroitinsulfateironcomplex'],
    'cisatracurium': ['cisatracurium', 'cisatracuriumbesylatel'],
    'desvenlafaxine': ['desvenlafaxine', 'desvenlafaxinesuccinate'],
    'doxapram': ['doxapramhcl', 'doxapramhydrochloride'],
    'formoterol': ['formoterol', 'formoterolfumarate'],
    'mosapride': ['mosapride', 'mosapridecitrate'],
    'ondansetron': ['ondansetron', 'ondansetronhydrochloride'],
    'sitagliptin': ['sitagliptin', 'sitagliptinphosphate'],
    'teneligliptin': ['teneligliptin', 'teneligliptinhydrobromide'],
    'tenofoviralafenamide': ['tenofoviralafenamidehemi', 'tenofoviralafenamidehemimalate']
}

# 통합될 항목들의 집합 생성
items_to_consolidate = set()
for base, reps in known_consolidations.items():
    items_to_consolidate.update(reps)

# 통합된 결과 생성
consolidated_entries = {}

# 먼저 통합이 필요한 항목들 처리
for base_name, representatives in known_consolidations.items():
    all_synonyms = []
    target_base = base_name  # 기본 성분명 사용
    
    # 각 대표값의 유사값들을 수집
    for rep in representatives:
        if rep in entries:
            all_synonyms.extend(entries[rep].split(', '))
            # 기본 형태가 아닌 대표값은 유사값에 추가
            if rep != target_base:
                all_synonyms.append(rep)
    
    # 중복 제거하고 정렬
    unique_synonyms = sorted(list(set(all_synonyms)))
    consolidated_entries[target_base] = ', '.join(unique_synonyms)

# 통합되지 않는 나머지 항목들 추가
for representative, synonyms in entries.items():
    if representative not in items_to_consolidate:
        consolidated_entries[representative] = synonyms

# 결과를 파일로 저장
with open('C:/Jimin/pharmaLex_unity/pharma_unidirectional_dict_ultimate.txt', 'w', encoding='utf-8') as f:
    for i, (representative, synonyms) in enumerate(sorted(consolidated_entries.items()), 1):
        f.write(f"{synonyms} => {representative}\n")

print(f"통합 완료! 총 {len(consolidated_entries)}개 항목으로 정리되었습니다.")
print(f"원본: {len(entries)}개 => 최종: {len(consolidated_entries)}개")
print(f"통합된 항목 수: {len(entries) - len(consolidated_entries)}개")

print("\n=== 통합된 항목들 ===")
for base_name, representatives in known_consolidations.items():
    print(f"[{base_name}] {representatives} => {base_name}")