import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="한국형 마법공식 대시보드",
    page_icon="🧙‍♂️",
    layout="wide"
)

st.title("🧙‍♂️ 한국형 마법공식(Magic Formula) 스크리너")
st.markdown("""
조엘 그린블라트의 **마법공식**을 적용하여, **돈을 잘 벌면서(ROE) 주가가 저평가된(PER)** 한국 시장의 우량 종목을 추출한 대시보드입니다.
""")

@st.cache_data
def load_data():
    try:
        df = pd.read_csv("magic_formula_top.csv")
        return df
    except FileNotFoundError:
        return None

df = load_data()

if df is None:
    st.error("⚠️ 'magic_formula_top.csv' 파일을 찾을 수 없습니다. 먼저 `python collect.py`를 실행해 주세요.")
else:
    st.sidebar.header("🔍 필터 옵션")
    
    markets = ["전체"] + list(df["Market"].unique())
    selected_market = st.sidebar.selectbox("시장 선택", markets)
    
    top_n = st.sidebar.slider("상위 종목 출력 개수", min_value=10, max_value=len(df), value=30, step=10)
    
    filtered_df = df.copy()
    if selected_market != "전체":
        filtered_df = filtered_df[filtered_df["Market"] == selected_market]
        
    filtered_df = filtered_df.head(top_n)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("분석 대상 유효 종목 수", f"{len(df)}개")
    col2.metric("현재 화면 출력 종목 수", f"{len(filtered_df)}개")
    col3.metric("최우수 1위 종목", filtered_df.iloc[0]["Name"] if len(filtered_df) > 0 else "N/A")
    
    st.divider()
    
    st.subheader(f"📊 마법공식 TOP {top_n} 리스트")
    
    display_df = filtered_df[['Magic_Score', 'Name', 'Code', 'Market', 'PER', 'ROE', 'PER_Rank', 'ROE_Rank', 'Price']].copy()
    display_df.columns = ['순위 스코어', '종목명', '종목코드', '시장', 'PER', 'ROE', 'PER순위', 'ROE순위', '현재주가']
    
    # 주가 포맷팅 (원화 콤마 추가)
    display_df['현재주가'] = display_df['현재주가'].apply(lambda x: f"{int(x):,}원" if pd.notnull(x) else "-")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    csv_data = filtered_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 현재 결과 CSV 다운로드",
        data=csv_data,
        file_name="magic_formula_filtered.csv",
        mime="text/csv"
    )
