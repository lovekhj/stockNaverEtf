import csv
import argparse
import sys
import re
import urllib.request
import json
import urllib.parse
import time
from collections import Counter

# 해외 주식 / 인덱스 예외 Excluded 종목 목록
OVERSEAS_EXCLUDE = {
    'VANGUARD FTSE EMERGING MARKE', 'CHINA CONSTRUCTION BANK-H', 'IND & COMM BK OF CHINA-H',
    'VANGUARD TOT WORLD STK ETF', 'BANK OF CHINA LTD-H', 'STRIVE 1000 DIVIDEND GROWTH',
    'DIREX DAI AV BULL 2X ETF-USD', 'AMPHENOL CORP-CL A', 'JPMORGAN CHASE & CO',
    'NEXTERA ENERGY INC', 'Yes Bank Ltd', 'SUZLON ENERGY LTD', 'IDFC Bank Ltd',
    'NHPC Ltd', 'GMR Airports Limited'
}

# ETF 브랜드 접두사 (ETF-in-ETF 종목 필터링)
ETF_PREFIXES = (
    'KODEX ', 'TIGER ', 'RISE ', 'ACE ', 'SOL ', 'PLUS ', 'HANARO ', 'TIME ',
    'KoAct ', 'WON ', '1Q ', 'IBK ', 'KIWOOM ', 'BNK ', 'DAISHIN ', '아이엠에셋 ', '마이티 '
)

# 종목코드 조회 캐시
CODE_CACHE = {}

def is_valid_stock(name):
    """
    현금, 선물, 채권, 타 ETF 종목명, 해외 종목 등을 제외하고 순수 국내 주식 종목만 검증합니다.
    """
    name = name.strip()
    if not name:
        return False
    
    # 1. 현금 / 예수금 관련 항목 제외
    if name in ('원화현금', '설정현금액', '현금', 'KRW', '예치금', '원화예금', '원화현금액'):
        return False
    
    # 2. 선물 / 옵션 / 파생상품 제외
    if '선물' in name or 'F 20' in name or 'F20' in name or re.search(r'202\d-', name):
        return False
    
    # 3. 타 ETF / ETN 종목 보유분 제외
    if name.startswith(ETF_PREFIXES):
        return False
    
    # 4. 채권 / 통안채 / 국고채 / 특수채 관련 필터
    if re.search(r'\d+이\d+', name) or any(k in name for k in ('국고채', '통안채', '회사채', '특수채', '채권', '금융채', '산은채')):
        return False
    if '은행' in name and any(c in name for c in '0123456789-'):
        return False
    
    # 5. 해외 해외주식/인덱스 필터
    if name in OVERSEAS_EXCLUDE:
        return False
    
    return True

def get_stock_code(name):
    """
    네이버 증권 통합 검색 API를 통해 종목명의 6자리 주식 종목코드를 조회합니다.
    """
    if name in CODE_CACHE:
        return CODE_CACHE[name]
    
    encoded = urllib.parse.quote(name)
    url = f"https://ac.stock.naver.com/ac?q={encoded}&target=index,stock,etf"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            items = data.get("items", [])
            code = ""
            for item in items:
                if item.get("name", "").strip() == name:
                    code = item.get("code", "").strip()
                    break
            if not code and items:
                code = items[0].get("code", "").strip()
            
            CODE_CACHE[name] = code
            return code
    except Exception:
        CODE_CACHE[name] = ""
        return ""

import os

def main():
    default_input = "data/etf_dtl_list.csv" if os.path.exists("data/etf_dtl_list.csv") else "etf_dtl_list.csv"
    parser = argparse.ArgumentParser(description="주도주 분석용 종목코드/종목명 순위 추출 스크립트")
    parser.add_argument("--input-csv", type=str, default=default_input, help=f"입력 CSV 파일 경로 (기본값: {default_input})")
    parser.add_argument("--save-csv", type=str, default="data/etf_top_stocks.csv", help="저장할 CSV 파일 경로 (기본값: data/etf_top_stocks.csv)")
    parser.add_argument("--include-rank", action="store_true", help="순위 컬럼 포함 여부")
    args = parser.parse_args()

    try:
        with open(args.input_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        print(f"[오류] '{args.input_csv}' 파일을 읽는 도중 에러가 발생했습니다: {e}")
        sys.exit(1)

    stock_counter = Counter()

    for r in rows:
        stk_name = r.get("구성종목명", "").strip()
        if is_valid_stock(stk_name):
            stock_counter[stk_name] += 1

    sorted_stocks = stock_counter.most_common()
    total_valid = len(sorted_stocks)

    print(f"총 {total_valid}개 순수 주식 종목의 6자리 종목코드 조회를 시작합니다...")
    
    result_rows = []
    for rank, (stk_name, count) in enumerate(sorted_stocks, 1):
        code = get_stock_code(stk_name)
        detail_url = f"https://stock.naver.com/domestic/stock/{code}/price" if code else ""
        
        row_dict = {
            "종목코드": code,
            "종목명": stk_name,
            "상세페이지": detail_url
        }
        if args.include_rank:
            row_dict = {"순위": rank, **row_dict}
            
        result_rows.append(row_dict)

        if rank % 50 == 0 or rank == total_valid:
            print(f"[{rank}/{total_valid}] 종목코드 조회 진행 중... ({stk_name} -> {code})")
        time.sleep(0.02)

    print("\n" + "=" * 80)
    print(f"{'순위':<4} | {'종목코드':<8} | {'종목명':<16} | {'상세페이지'}")
    print("-" * 80)
    for idx, r in enumerate(result_rows[:25], 1):
        print(f"{idx:<4} | {r['종목코드']:<8} | {r['종목명']:<16} | {r['상세페이지']}")
    print("=" * 80)

    # CSV 저장 (종목코드, 종목명, 상세페이지)
    if args.save_csv:
        fieldnames = list(result_rows[0].keys()) if result_rows else ["종목코드", "종목명", "상세페이지"]
        with open(args.save_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(result_rows)
        print(f"\n[성공] '종목코드', '종목명', '상세페이지' 정제 결과가 저장되었습니다: {args.save_csv} (총 {len(result_rows)}개 종목)")

if __name__ == "__main__":
    main()
