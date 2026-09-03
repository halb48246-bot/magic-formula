import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

print("1. 전체 상장 종목 리스트 불러오는 중...")
# 1. 전체 종목 리스트 가져오기
krx = fdr.StockListing("KRX")

# 스팩, 우선주, ETF/ETN 제거
krx = krx[~krx['Name'].str.contains('스팩|우|ETF|ETN', na=False)]
krx = krx[krx['Market'].isin(['KOSPI', 'KOSDAQ'])]

# 금융업 종목 제외
if 'Sector' in krx.columns:
    krx = krx[~krx['Sector'].str.contains('금융|은행|증권|보험', na=False)]

print(f"-> 대상 종목 수: {len(krx)}개")

# 네이버 금융에서 PER, ROE 긁어오는 함수
def get_naver_fundamental(code):
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # PER 가져오기
        per_elem = soup.select_one("#_per")
        per = float(per_elem.text.replace(',', '')) if per_elem and per_elem.text != 'N/A' else None
        
        # ROE 가져오기 (주요재무제표 테이블의 ROE 위치 파악)
        # 네이버 금융 우측 펀더멘털 영역의 ROE 파싱
        roe = None
        em_list = soup.select("div.section.trade_compare table tbody tr")
        for tr in em_list:
            if "ROE" in tr.text:
                tds = tr.select("td")
                if tds:
                    val = tds[-1].text.strip().replace(',', '')
                    if val != 'N/A' and val != '':
                        roe = float(val)
                break
                
        return per, roe
    except Exception:
        return None, None

print("\n2. 네이버 금융 기반 펀더멘털(PER, ROE) 데이터 크롤링 중...")
print("(안정적인 처리를 위해 상위 300개 종목을 대상으로 1차 테스트를 진행합니다)")

# 테스트 및 속도를 위해 시가총액 상위 종목으로 우선 선별 (크롤링 시간 절약)
if 'Marcap' in krx.columns:
    krx = krx.sort_values(by='Marcap', ascending=False).reset_index(drop=True)

# 일단 빠른 테스트를 위해 상위 300개로 진행 (나중에 숫자 늘릴 수 있음)
target_krx = krx.head(300).copy()

pers = []
roes = []

for idx, row in target_krx.iterrows():
    code = row['Code']
    name = row['Name']
    
    per, roe = get_naver_fundamental(code)
    pers.append(per)
    roes.append(roe)
    
    # 50개마다 진행 상황 출력
    if (idx + 1) % 50 == 0:
        print(f"  - [{idx+1}/{len(target_krx)}] 종목 데이터 수집 완료...")
    time.sleep(0.05) # 서버 매너 대기 시간

target_krx['PER'] = pers
target_krx['ROE'] = roes

# 데이터 정제 (PER, ROE가 유효하고 PER > 0 인 적자 제외 기업만)
df_valid = target_krx.dropna(subset=['PER', 'ROE']).copy()
df_valid = df_valid[df_valid['PER'] > 0]

print(f"\n-> 유효 종목 수: {len(df_valid)}개")

# 3. 마법공식 순위 계산
df_valid['PER_Rank'] = df_valid['PER'].rank(ascending=True)      # PER 낮을수록 1위
df_valid['ROE_Rank'] = df_valid['ROE'].rank(ascending=False)     # ROE 높을수록 1위
df_valid['Magic_Score'] = df_valid['PER_Rank'] + df_valid['ROE_Rank']

# 정렬 후 저장
df_result = df_valid.sort_values(by='Magic_Score').reset_index(drop=True)
df_result.to_csv("magic_formula_top.csv", index=False, encoding="utf-8-sig")

print("\n=== 🧙‍♂️ 마법공식 상위 TOP 10 ===")
print(df_result[['Name', 'Code', 'Market', 'PER', 'ROE', 'Magic_Score']].head(10))
print("\n-> 'magic_formula_top.csv' 저장 완료!")
