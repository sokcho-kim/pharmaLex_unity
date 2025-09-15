import pandas as pd
import os
from datetime import datetime

def merge_pharma_data():
    """
    세 개의 의약품 데이터 파일을 의성분코드 기준으로 합치는 함수
    """
    
    # 파일 경로 설정
    base_path = r"C:\Jimin\pharmaLex_unity\data"
    
    excel_file = os.path.join(base_path, "20220901_20250901 적용약가파일_8.28.수정.xlsx")
    atc_file = os.path.join(base_path, "건강보험심사평가원_ATC코드 매핑 목록_20240630.csv")
    master_file = os.path.join(base_path, "건강보험심사평가원_약가마스터_의약품주성분_20241014.csv")
    
    print("데이터 파일 로딩 중...")
    
    # 1. 적용약가파일 로딩 (Excel)
    df_price = pd.read_excel(excel_file)
    print(f"적용약가파일: {len(df_price):,}행 로딩 완료")
    
    # 2. ATC 매핑파일 로딩 (CSV)
    df_atc = pd.read_csv(atc_file, encoding='cp949')
    print(f"ATC매핑파일: {len(df_atc):,}행 로딩 완료")
    
    # 3. 약가마스터파일 로딩 (CSV)
    df_master = pd.read_csv(master_file, encoding='cp949')
    print(f"약가마스터파일: {len(df_master):,}행 로딩 완료")
    
    print("\n데이터 병합 시작...")
    
    # 컬럼명 정리 (인코딩 문제 해결을 위해 인덱스 사용)
    price_component_col = df_price.columns[11]  # 의성분코드
    atc_component_col = df_atc.columns[1]       # 의성분코드
    master_component_col = df_master.columns[0] # 일반명코드
    
    print(f"매핑 키: {price_component_col} ↔ {atc_component_col} ↔ {master_component_col}")
    
    # 1단계: 적용약가 + 약가마스터 매핑 (99.3% 커버리지)
    merged_df = df_price.merge(
        df_master, 
        left_on=price_component_col, 
        right_on=master_component_col, 
        how='left',
        suffixes=('', '_master')
    )
    
    print(f"1단계 병합 완료: {len(merged_df):,}행")
    
    # 2단계: ATC 정보 추가 (50% 커버리지)
    final_df = merged_df.merge(
        df_atc,
        left_on=price_component_col,
        right_on=atc_component_col,
        how='left',
        suffixes=('', '_atc')
    )
    
    print(f"2단계 병합 완료: {len(final_df):,}행")
    
    # 매핑 통계 출력
    total_records = len(final_df)
    master_mapped = final_df[master_component_col].notna().sum()
    atc_mapped = final_df['ATC코드'].notna().sum()
    
    print(f"\n=== 매핑 결과 통계 ===")
    print(f"전체 레코드: {total_records:,}개")
    print(f"약가마스터 매핑: {master_mapped:,}개 ({master_mapped/total_records*100:.1f}%)")
    print(f"ATC 매핑: {atc_mapped:,}개 ({atc_mapped/total_records*100:.1f}%)")
    
    # 결과 저장
    output_path = r"C:\Jimin\pharmaLex_unity\merged_data"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # CSV 저장
    csv_filename = f"merged_pharma_data_{timestamp}.csv"
    csv_path = os.path.join(output_path, csv_filename)
    final_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\nCSV 파일 저장: {csv_filename}")
    
    # Excel 저장 (참고용)
    excel_filename = f"merged_pharma_data_{timestamp}.xlsx"
    excel_path = os.path.join(output_path, excel_filename)
    final_df.to_excel(excel_path, index=False)
    print(f"Excel 파일 저장: {excel_filename}")
    
    # 컬럼 정보 출력
    print(f"\n=== 최종 데이터 구조 ===")
    print(f"총 컬럼 수: {len(final_df.columns)}개")
    print("주요 컬럼:")
    for i, col in enumerate(final_df.columns):
        if i < 10 or 'ATC' in str(col) or '일반명' in str(col) or '성분' in str(col):
            print(f"  {col}")
    
    return final_df, csv_path, excel_path

if __name__ == "__main__":
    try:
        merged_data, csv_file, excel_file = merge_pharma_data()
        print(f"\n병합 완료! 파일 확인:")
        print(f"- CSV: {csv_file}")
        print(f"- Excel: {excel_file}")
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()