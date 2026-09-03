import streamlit as st
import pandas as pd

# 페이지 기본 설정
st.set_page_config(
    page_title="한국형 마법공식 대시보드",
    page_icon="🧙‍♂️",
    layout="wide"
)

# 타이틀 및 설명
st.title("🧙‍♂️ 한국형 마법공식(Magic Formula) 스크리너")
st.markdown("""
조엘 그린블라트의 **마법공식**을 적용하여, **돈을 잘 벌면서(ROE) 주가가 저평가된(PER)** 한국 시장의 우량 종목을 추출한 대시보드입니다.
""")

# CSV 데이터 로드 함수
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("magic_formula_top.csv")
        return df
    except FileNotFoundError:
        return None

df = load_data()

if df is None:
    st.error("⚠️ 'magic_formula_top.csv' 파일을 찾을 수 없습니다. 먼저 `python collect.py`를 실행해서 데이터를 수집해 주세요.")
else:
    # 사이드바 설정 (필터링 옵션)
    st.sidebar.header("🔍 필터 옵션")
    
    # 1. 시장 선택 필터
    markets = ["전체"] + list(df["Market"].unique())
    selected_market = st.sidebar.selectbox("시장 선택", markets)
    
    # 2. 보여줄 종목 수 슬라이더
    top_n = st.sidebar.slider("상위 종목 출력 개수", min_value=10, max_value=len(df), value=30, step=10)
    
    # 데이터 필터링 적용
    filtered_df = df.copy()
    if selected_market != "전체":
        filtered_df = filtered_df[filtered_df["Market"] == selected_market]
        
    filtered_df = filtered_df.head(top_n)
    
    # 요약 메트릭 카드 표시
    col1, col2, col3 = st.columns(3)
    col1.metric("분석 대상 종목 수", f"{len(df)}개")
    col2.metric("현재 화면 출력 종목 수", f"{len(filtered_df)}개")
    col3.metric("최우수 1위 종목", filtered_df.iloc[0]["Name"] if len(filtered_df) > 0 else "N/A")
    
    st.divider()
    
    # 결과 테이블 표시
    st.subheader(f"📊 마법공식 TOP {top_n} 리스트")
    
    # 테이블 컬럼 이름 정리 및 재배치
    display_df = filtered_df[['Magic_Score', 'Name', 'Code', 'Market', 'PER', 'ROE', 'PER_Rank', 'ROE_Rank']].copy()
    display_df.columns = ['순위 스코어', '종목명', '종목코드', '시장', 'PER', 'ROE', 'PER순위', 'ROE순위']
    
    # 화면에 포맷팅된 데이터프레임 출력
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # 데이터 다운로드 버튼 제공
    csv_data = filtered_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 현재 결과 CSV 다운로드",
        data=csv_data,
        file_name="magic_formula_filtered.csv",
        mime="text/csv"
    )
