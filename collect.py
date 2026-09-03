import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

print("1. 전체 상장 종목 리스트 불러오는 중...")
krx = fdr.StockListing("KRX")

# 스팩, 우선주, ETF/ETN 제거
krx = krx[~krx['Name'].str.contains('스팩|우|ETF|ETN', na=False)]
krx = krx[krx['Market'].isin(['KOSPI', 'KOSDAQ'])]

# 금융업 종목 제외
if 'Sector' in krx.columns:
    krx = krx[~krx['Sector'].str.contains('금융|은행|증권|보험', na=False)]

# 시가총액 순 정렬 후 상위 2000개 추출
if 'Marcap' in krx.columns:
    krx = krx.sort_values(by='Marcap', ascending=False).reset_index(drop=True)

target_krx = krx.head(2000).copy()
print(f"-> 최종 분석 대상 종목 수: {len(target_krx)}개")

# 개별 종목 크롤링 함수
def fetch_fundamental(row_data):
    code = row_data['Code']
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. 현재 주가
        price_elem = soup.select_one("p.no_today span.blind")
        price = int(price_elem.text.replace(',', '')) if price_elem else None

        # 2. PER
        per_elem = soup.select_one("#_per")
        per = float(per_elem.text.replace(',', '')) if per_elem and per_elem.text != 'N/A' else None
        
        # 3. ROE
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
                
        return {'Code': code, 'Price': price, 'PER': per, 'ROE': roe}
    except Exception:
        return {'Code': code, 'Price': None, 'PER': None, 'ROE': None}

print("\n2. 네이버 금융 데이터(주가, PER, ROE) 멀티스레드 크롤링 중...")
results = []

# 병렬 처리 (10개 스레드로 속도 향상)
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(fetch_fundamental, row) for _, row in target_krx.iterrows()]
    
    completed = 0
    total = len(futures)
    for future in as_completed(futures):
        results.append(future.result())
        completed += 1
        if completed % 200 == 0 or completed == total:
            print(f"  - [{completed}/{total}] 종목 수집 완료...")

# 결과 병합
df_fetched = pd.DataFrame(results)
target_krx = pd.merge(target_krx, df_fetched, on='Code', how='inner')

# 데이터 정제 (유효 데이터 & 적자 제외)
df_valid = target_krx.dropna(subset=['PER', 'ROE', 'Price']).copy()
df_valid = df_valid[df_valid['PER'] > 0]

print(f"\n-> 적자 기업 및 유효 지표 미제공 기업 제외 후 유효 종목 수: {len(df_valid)}개")

# 3. 마법공식 순위 계산
df_valid['PER_Rank'] = df_valid['PER'].rank(ascending=True)
df_valid['ROE_Rank'] = df_valid['ROE'].rank(ascending=False)
df_valid['Magic_Score'] = df_valid['PER_Rank'] + df_valid['ROE_Rank']

# 정렬 후 CSV 저장
df_result = df_valid.sort_values(by='Magic_Score').reset_index(drop=True)
df_result.to_csv("magic_formula_top.csv", index=False, encoding="utf-8-sig")

print("\n=== 🧙‍♂️ 마법공식 TOP 10 ===")
print(df_result[['Name', 'Code', 'Market', 'Price', 'PER', 'ROE', 'Magic_Score']].head(10))
print("\n-> 'magic_formula_top.csv' 저장 완료!")
