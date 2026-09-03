import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random

print("1. 전체 상장 종목 리스트 불러오는 중...")
krx = fdr.StockListing("KRX")

# 스팩, 우선주, ETF/ETN 제거
krx = krx[~krx['Name'].str.contains('스팩|우|ETF|ETN', na=False)]
krx = krx[krx['Market'].isin(['KOSPI', 'KOSDAQ'])]

# 금융업 제외
if 'Sector' in krx.columns:
    krx = krx[~krx['Sector'].str.contains('금융|은행|증권|보험', na=False)]

# 시가총액 상위 2,000개 선별
if 'Marcap' in krx.columns:
    krx = krx.sort_values(by='Marcap', ascending=False).reset_index(drop=True)

target_krx = krx.head(2000).copy()
print(f"-> 최종 크롤링 대상 종목 수: {len(target_krx)}개")

def fetch_fundamental(row_data):
    code = row_data['Code']
    url = f"https://finance.naver.com/item/main.naver?code={code}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://finance.naver.com/'
    }
    
    time.sleep(random.uniform(0.05, 0.15))
    
    for attempt in range(2):
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # 1. 현재 주가
                price_elem = soup.select_one("p.no_today span.blind")
                price = int(price_elem.text.replace(',', '')) if price_elem else None

                # 2. 실시간 PER
                per_elem = soup.select_one("#_per")
                per = float(per_elem.text.replace(',', '')) if per_elem and per_elem.text != 'N/A' else None
                
                # 3. 최신 확정 ROE (개별 종목 기업실적분석 cop_analysis 테이블에서 수집)
                roe = None
                finance_table = soup.select_one("div.section.cop_analysis table")
                
                if finance_table:
                    rows = finance_table.select("tbody tr")
                    for tr in rows:
                        th = tr.select_one("th")
                        if th and "ROE" in th.text:
                            tds = tr.select("td")
                            # 오른쪽(최신 실적)부터 역순 탐색하며 확정 숫자를 파싱
                            for td in reversed(tds):
                                val = td.text.strip().replace(',', '')
                                if val and val != 'N/A' and '(E)' not in val:
                                    try:
                                        roe = float(val)
                                        break
                                    except ValueError:
                                        continue
                            break
                        
                return {'Code': code, 'Price': price, 'PER': per, 'ROE': roe}
        except Exception:
            time.sleep(0.5)
            
    return {'Code': code, 'Price': None, 'PER': None, 'ROE': None}

print("\n2. 크롤링 진행 중 (네이버 금융)...")
results = []

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(fetch_fundamental, row) for _, row in target_krx.iterrows()]
    
    completed = 0
    total = len(futures)
    for future in as_completed(futures):
        results.append(future.result())
        completed += 1
        if completed % 200 == 0 or completed == total:
            print(f"  - [{completed}/{total}] 종목 수집 완료...")

# 데이터 병합 및 정제
df_fetched = pd.DataFrame(results)
target_krx = pd.merge(target_krx, df_fetched, on='Code', how='inner')

df_valid = target_krx.dropna(subset=['PER', 'ROE', 'Price']).copy()
df_valid = df_valid[df_valid['PER'] > 0]

# 마법공식 스코어링
df_valid['PER_Rank'] = df_valid['PER'].rank(ascending=True)
df_valid['ROE_Rank'] = df_valid['ROE'].rank(ascending=False)
df_valid['Magic_Score'] = df_valid['PER_Rank'] + df_valid['ROE_Rank']

df_result = df_valid.sort_values(by='Magic_Score').reset_index(drop=True)
df_result.to_csv("magic_formula_top.csv", index=False, encoding="utf-8-sig")

print(f"\n-> 유효 종목 {len(df_result)}개 수집 및 'magic_formula_top.csv' 저장 완료!")
