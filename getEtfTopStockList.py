#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 [3단계] 순수 국내 주식 종목 정제 및 6자리 종목코드 매핑 프로그램 (getEtfTopStockList.py)
================================================================================
1. 프로그램 역할:
   2단계에서 수집한 ETF 주요 구성종목(`data/etf_dtl_list.csv`)에서 
   현금, 채권, 해외주식, 선물/파생상품 등을 깨끗하게 제외하고,
   순수 '국내 주식 종목'만 필터링하여 네이버 증권 6자리 종목코드(예: 005930)와
   상세페이지 URL을 매핑합니다.

2. 입력 데이터:
   - CSV 파일: `data/etf_dtl_list.csv` (2단계 실행 결과)

3. 출력 결과:
   - CSV 파일: `data/etf_top_stocks.csv` (정제된 순수 주식 종목코드, 종목명, 네이버상세페이지 URL 등 약 320여 개)

4. 주요 작동 흐름 (누구나 이해할 수 있는 단계별 설명):
   - 1단계 [필터링]: 종목명 중 '원화현금', '국고채', '선물', '해외주식' 등을 자동 정제합니다.
   - 2단계 [집계]: 각 개별 종목이 수많은 ETF에서 상위 비중으로 등장하는 횟수(인기도)를 계산합니다.
   - 3단계 [조회]: 네이버 통합검색 API를 통해 각 주식 종목의 6자리 종목코드를 찾아냅니다.
   - 4단계 [저장]: 최종 정제된 주도주 320여 개 목록을 `data/etf_top_stocks.csv` 파일로 저장합니다.
================================================================================
"""

import csv                  # CSV 파일 처리 라이브러리
import argparse             # 터미널 실행 옵션 파서
import sys                  # 시스템 처리 라이브러리
import re                   # 글자 패턴 검사를 위한 정규표현식
import urllib.request       # 네이버 웹 서버 접속 라이브러리
import json                 # JSON 데이터 파싱 라이브러리
import urllib.parse         # 한글 종목명을 인터넷 웹주소용(URL인코딩)으로 바꿔주는 라이브러리
import time                 # 대기 시간(sleep) 제공 도구
import os                   # 파일 및 디렉토리 확인 라이브러리
from collections import Counter # 종목 등장 횟수를 편리하게 카운팅해주는 파이썬 기본 도구

# ==============================================================================
# 💡 해외 주식 / 인덱스 예외 필터링 목록
# (국내 ETF에 편입된 해외 기업 주식명들을 미리 정의하여 제거합니다)
# ==============================================================================
OVERSEAS_EXCLUDE = {
    'VANGUARD FTSE EMERGING MARKE', 'CHINA CONSTRUCTION BANK-H', 'IND & COMM BK OF CHINA-H',
    'VANGUARD TOT WORLD STK ETF', 'BANK OF CHINA LTD-H', 'STRIVE 1000 DIVIDEND GROWTH',
    'DIREX DAI AV BULL 2X ETF-USD', 'AMPHENOL CORP-CL A', 'JPMORGAN CHASE & CO',
    'NEXTERA ENERGY INC', 'Yes Bank Ltd', 'SUZLON ENERGY LTD', 'IDFC Bank Ltd',
    'NHPC Ltd', 'GMR Airports Limited'
}

# ==============================================================================
# 💡 ETF 브랜드 접두사 목록
# (ETF 펀드가 또 다른 ETF를 보유한 재간접 ETF의 경우, 대상 ETF명을 제거하기 위함)
# ==============================================================================
ETF_PREFIXES = (
    'KODEX ', 'TIGER ', 'RISE ', 'ACE ', 'SOL ', 'PLUS ', 'HANARO ', 'TIME ',
    'KoAct ', 'WON ', '1Q ', 'IBK ', 'KIWOOM ', 'BNK ', 'DAISHIN ', '아이엠에셋 ', '마이티 '
)

# 💡 종목코드 검색 속도를 극대화하기 위한 임시 저장소 (캐시 딕셔너리)
CODE_CACHE = {}

def is_valid_stock(name):
    """
    구성종목 이름이 순수한 '국내 일반 주식'인지 검증하는 스마트 필터 함수입니다.
    현금, 채권, 파생상품, 타 ETF, 해외 종목 등을 무도 걸러냅니다.
    
    :param name: 종목명 (예: '삼성전자', '원화현금', '국고채3년')
    :return: True(매수/분석 대상 국내주식), False(제외 대상)
    """
    name = name.strip()
    if not name:
        return False
    
    # 1. 현금 / 예수금 관련 항목 제외
    if name in ('원화현금', '설정현금액', '현금', 'KRW', '예치금', '원화예금', '원화현금액'):
        return False
    
    # 2. 선물 / 옵션 / 파생상품 제외 (예: 'F 202412', 'KOSPI200 선물')
    if '선물' in name or 'F 20' in name or 'F20' in name or re.search(r'202\d-', name):
        return False
    
    # 3. 타 ETF / ETN 종목 보유분 제외 (예: 'KODEX 200', 'TIGER 2차전지')
    if name.startswith(ETF_PREFIXES):
        return False
    
    # 4. 채권 / 통안채 / 국고채 / 회사채 관련 필터
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
    네이버 증권 자동완성/검색 API를 통해 종목명의 '6자리 주식 종목코드'를 조회합니다.
    (예: '삼성전자' -> '005930', 'SK하이닉스' -> '000660')
    """
    # 💡 이미 검색했던 종목이면 인터넷 접속 없이 캐시에서 즉시 반환하여 속도를 높입니다.
    if name in CODE_CACHE:
        return CODE_CACHE[name]
    
    # 한글 종목명을 웹 서버가 이해할 수 있는 주소 형태(URL 인코딩)로 변환
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
            
            # 정확히 종목명이 일치하는 항목의 6자리 코드 추출
            for item in items:
                if item.get("name", "").strip() == name:
                    code = item.get("code", "").strip()
                    break
            # 정확히 일치하는 명칭이 없는 경우 첫 번째 검색 결과 사용
            if not code and items:
                code = items[0].get("code", "").strip()
            
            # 캐시에 결과 저장 후 반환
            CODE_CACHE[name] = code
            return code
    except Exception:
        CODE_CACHE[name] = ""
        return ""

def main():
    """
    [3단계] 국내 주도주 종목 정제 및 코드 매핑 메인 실행 함수입니다.
    """
    default_input = "data/etf_dtl_list.csv" if os.path.exists("data/etf_dtl_list.csv") else "etf_dtl_list.csv"
    
    parser = argparse.ArgumentParser(description="[3단계] 주도주 종목 정제 및 6자리 종목코드 매핑 스크립트")
    parser.add_argument("--input-csv", type=str, default=default_input, help=f"2단계에서 생성한 CSV 경로 (기본값: {default_input})")
    parser.add_argument("--save-csv", type=str, default="data/etf_top_stocks.csv", help="저장할 CSV 파일 경로 (기본값: data/etf_top_stocks.csv)")
    parser.add_argument("--include-rank", action="store_true", help="결과에 인기 순위 번호 포함 여부")
    args = parser.parse_args()

    # 1. 2단계 `data/etf_dtl_list.csv` 파일 불러오기
    try:
        with open(args.input_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        print(f"[❌ 오류] '{args.input_csv}' 파일을 읽는 도중 에러가 발생했습니다: {e}")
        print("💡 팁: 2단계 스크립트(getEtfDtlList.py)를 먼저 실행했는지 확인하세요.")
        sys.exit(1)

    print(f"\n🚀 [3단계] '{args.input_csv}' 파일에서 총 {len(rows)}개 구성종목 항목을 읽었습니다.")

    # 2. 순수 주식 종목만 카운팅 (중복 제거 및 등장 횟수 집계)
    stock_counter = Counter()
    for r in rows:
        stk_name = r.get("구성종목명", "").strip()
        if is_valid_stock(stk_name):
            stock_counter[stk_name] += 1

    # 가장 많이 ETF에 포함된 순서대로 정렬
    sorted_stocks = stock_counter.most_common()
    total_valid = len(sorted_stocks)

    print(f"✅ 필터링 완료: 현금/채권/해외주식 등을 제거하고 총 {total_valid}개 순수 주식 종목을 선별했습니다.")
    print("🔍 각 종목의 네이버 증권 6자리 종목코드 조회를 시작합니다...\n")
    
    result_rows = []
    # 3. 선별된 종목마다 네이버 API를 통해 6자리 종목코드 및 상세페이지 주소 매핑
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

        # 진행 상황 안내 출력 (50개 단위)
        if rank % 50 == 0 or rank == total_valid:
            print(f"⏳ [{rank}/{total_valid}] 종목코드 매핑 진행 중... ({stk_name} -> {code})")
        time.sleep(0.02)

    # 4. 콘솔 상위 25개 미리보기 출력
    print("\n" + "=" * 80)
    print(f"{'순위':<4} | {'종목코드':<8} | {'종목명':<20} | {'네이버 상세페이지 주소'}")
    print("-" * 80)
    for idx, r in enumerate(result_rows[:25], 1):
        print(f"{idx:<4} | {r['종목코드']:<8} | {r['종목명']:<20} | {r['상세페이지']}")
    print("=" * 80)

    # 5. 매핑 결과를 `data/etf_top_stocks.csv` 파일로 저장
    if args.save_csv:
        save_dir = os.path.dirname(args.save_csv)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

        fieldnames = list(result_rows[0].keys()) if result_rows else ["종목코드", "종목명", "상세페이지"]
        with open(args.save_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(result_rows)
        print(f"\n💾 [저장 완료] 주도주 종목코드 정제 결과가 저장되었습니다: {args.save_csv} (총 {len(result_rows)}개 종목)")

if __name__ == "__main__":
    main()
