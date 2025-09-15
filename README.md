# PharmaLex Unity Project

한국 의약품 용어 표준화 및 데이터 통합 프로젝트

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Pandas](https://img.shields.io/badge/Pandas-2.0+-green.svg)](https://pandas.pydata.org)
[![License](https://img.shields.io/badge/License-Private-red.svg)](LICENSE)

## 📋 프로젝트 개요

한국 의약품 데이터의 표준화와 통합을 목표로 하는 **의약품 데이터 통합 시스템**입니다. 건강보험심사평가원의 공식 데이터를 기반으로 54,000여 개의 의약품 레코드를 통합하여, 포괄적인 의약품 데이터베이스를 구축합니다.

### 🎯 프로젝트 목표

1. **의약품 용어 표준화**: 다양한 의약품 표기법 통일
2. **데이터 통합**: 여러 기관의 의약품 데이터베이스 통합
3. **ATC 코드 매핑**: WHO ATC 분류체계와 연계
4. **품질 관리**: 중복 제거 및 데이터 정제

## 🚀 주요 성과

### ✅ 데이터 통합 결과
- **총 레코드**: 1,805,523개 (약 180만건)
- **총 컬럼**: 44개  
- **파일 크기**: 3.5GB
- **약가마스터 매핑률**: 100.0%
- **ATC 매핑률**: 99.1%

### ✅ 데이터 품질
- 의성분코드 기준 매핑 성공
- 시계열 데이터 보존
- 제조사별 정보 유지
- ATC 분류체계 연계

## 📊 통합 데이터 현황

| 구분 | 레코드 수 | 컬럼 수 | 매핑률 |
|------|----------|---------|--------|
| **적용약가파일** | 54,757개 | 30개 | - |
| **ATC매핑파일** | 23,027개 | 7개 | 99.1% |
| **약가마스터** | 58,576개 | 8개 | 100.0% |
| **통합 결과** | 1,805,523개 | 44개 | - |

## 🛠 기술 스택

- **언어**: Python 3.8+
- **데이터 처리**: pandas, numpy
- **텍스트 처리**: 정규표현식, 자연어 처리
- **인코딩**: CP949, UTF-8 다국어 지원
- **데이터 구조**: defaultdict, set을 활용한 효율적 메모리 관리

## 📁 프로젝트 구조

```
C:\Jimin\pharmaLex_unity\
├── README.md                       # 프로젝트 메인 문서
├── data/                           # 원본 데이터 파일들
│   ├── 20220901_20250901 적용약가파일_8.28.수정.xlsx
│   ├── 건강보험심사평가원_ATC코드 매핑 목록_20240630.csv
│   └── 건강보험심사평가원_약가마스터_의약품주성분_20241014.csv
├── merged_data/                    # 데이터 통합 결과
│   ├── merge_pharma_data.py        # 통합 스크립트
│   ├── merged_pharma_data_20250915_102415.csv  # 통합된 데이터
│   └── MERGE_ANALYSIS_REPORT.md    # 통합 분석 보고서
├── scripts/                        # Python 스크립트들
│   ├── consolidate_script.py       # 데이터 통합 스크립트
│   ├── convert_pharma_dict.py      # 사전 변환 스크립트
│   ├── create_final_dict.py        # 최종 사전 생성
│   ├── final_consolidate_script.py # 최종 통합 스크립트
│   ├── final_pharma_processor.py   # 최종 처리기
│   ├── find_duplicates.py          # 중복 찾기
│   ├── generate_final_report.py    # 최종 보고서 생성
│   ├── pharma_preprocessor.py      # 전처리기
│   ├── process_pharma_dict.py      # 사전 처리 (기본)
│   ├── process_pharma_dict_final.py    # 사전 처리 (최종)
│   ├── process_pharma_dict_improved.py # 사전 처리 (개선)
│   ├── simple_pharma_processor.py  # 단순 처리기
│   └── strict_pharma_processor.py  # 엄격 처리기
├── reports/                        # 분석 보고서들
│   └── HISTORY.md                  # 프로젝트 이력
├── archive/                        # 과거 결과물들
│   ├── pharma_dict_final_merged.txt
│   ├── pharma_dict_final_processed.txt
│   ├── pharma_dict_submission_ready.txt
│   ├── pharma_unidirectional_dict.txt
│   ├── pharma_unidirectional_dict_cleaned.txt
│   ├── pharma_unidirectional_dict_final.txt
│   ├── pharma_unidirectional_dict_submission.txt
│   ├── pharma_unidirectional_dict_ultimate.txt
│   ├── representative_values.txt
│   └── representative_values_count.txt
├── phases/                         # 단계별 작업 폴더
├── back/                          # 백업 폴더
└── solution/                      # 솔루션 폴더
```

## 🔄 주요 작업 단계

### Phase 1: 데이터 분석 및 준비
- 원본 데이터 구조 분석
- 매핑 키 식별 (의성분코드)
- 커버리지 분석

### Phase 2: 데이터 통합
- 의성분코드 기준 LEFT JOIN
- 99.3% 커버리지 달성
- 1,805,523개 레코드 생성

### Phase 3: 품질 관리
- 중복 패턴 분석
- 데이터 검증
- 최종 정제

## 🚀 사용 방법

### 1. 데이터 통합 실행
```bash
cd merged_data
python merge_pharma_data.py
```

### 2. 개별 스크립트 실행
```bash
cd scripts
python [스크립트명].py
```

### 3. 보고서 확인
- `merged_data/MERGE_ANALYSIS_REPORT.md`: 통합 분석 보고서
- `reports/HISTORY.md`: 프로젝트 이력

## ⚠️ 주의사항

1. **대용량 파일**: 통합 결과물이 3.5GB로 대용량
2. **Excel 제한**: 104만행 초과로 Excel 저장 불가
3. **메모리 사용**: 처리 시 충분한 메모리 필요
4. **인코딩**: CP949 인코딩 사용 (한글 파일명)

## 📈 향후 계획

1. **실시간 업데이트**: 정기적 데이터 갱신 체계
2. **API 개발**: 데이터 조회 API 구축  
3. **웹 인터페이스**: 사용자 친화적 인터페이스
4. **품질 모니터링**: 자동화된 품질 검증

## 📝 참고 문서

- [데이터 통합 분석 보고서](merged_data/MERGE_ANALYSIS_REPORT.md)
- [프로젝트 이력](reports/HISTORY.md)

## 👨‍💻 개발자 정보

**프로젝트 관리자**: Jimin  
**개발 기간**: 2025년 9월 1일  
**기술 스택**: Python, 자연어 처리, 대용량 데이터 처리  
**도메인**: 의료 정보학, 건강보험 시스템

---

> 💡 **프로젝트 특징**  
> 본 프로젝트는 **대용량 의료 데이터 처리**와 **자연어 처리** 기술을 활용하여, 실제 의료 현장에서 필요한 동의어 사전 구축을 시도한 프로젝트입니다. 건강보험심사평가원 공식 데이터를 기반으로 하여, 요양급여 업무 담당자들의 검색 효율성 개선에 기여하고자 했습니다.