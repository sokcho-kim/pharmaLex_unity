# PharmaLex Unity - Phase별 작업 구조

## 프로젝트 개요
의약품 데이터 변환 및 처리를 단계별로 진행하는 프로젝트

## Phase 구조

### Phase 1 - Original (완료된 작업)
- **위치**: `phases/phase1_original/`
- **내용**: 기존 완성된 모든 파일들
  - 1_고유명사사전_perfect.txt
  - 2_주성분코드매핑_perfect.txt  
  - 3_성분한글영문_perfect.txt
  - 4_검색기용유의어사전_perfect.txt
  - 5_주성분별약품그룹_perfect.txt

### Phase 2 - File 4 to File 5 Format Conversion
- **위치**: `phases/phase2_4to5/`
- **목표**: 4번 파일을 5번 파일 형식으로 변환
- **입력 형식**: `성분명, 약품명1, 약품명2, ...` 
- **출력 형식**: `성분명: 약품명1, 약품명2, ...`
- **구조**:
  - `input/`: 입력 파일 (4_검색기용유의어사전_perfect.txt)
  - `output/`: 변환 결과 파일
  - `scripts/`: 변환 스크립트

### Phase 3 - File 5 to File 2 Format Conversion  
- **위치**: `phases/phase3_5to2/`
- **목표**: 5번 파일을 2번 파일 형식으로 변환
- **입력 형식**: `성분명: 약품명1, 약품명2, ...`
- **출력 형식**: `코드 => 성분명, 약품명1, 약품명2, ...`
- **구조**:
  - `input/`: 입력 파일 (Phase 2 결과물)
  - `output/`: 변환 결과 파일  
  - `scripts/`: 변환 스크립트

## 작업 진행 상황
- [x] Phase 1: 완료 (기존 작업)
- [ ] Phase 2: 진행 예정
- [ ] Phase 3: 대기 중