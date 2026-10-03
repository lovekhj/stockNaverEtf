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

SECTOR_RULES = [
    ('반도체/소부장', [r'반도체', r'소부장', r'메모리', r'팹리스', r'파운드리']),
    ('2차전지/배터리', [r'2차전지', r'배터리', r'양극재', r'음극재', r'리튬']),
    ('바이오/헬스케어', [r'바이오', r'헬스케어', r'제약', r'신약', r'의료']),
    ('조선/방산/중공업', [r'조선', r'방산', r'우주', r'항공', r'해운', r'중공업']),
    ('금융/지주', [r'금융', r'은행', r'증권', r'보험', r'지주']),
    ('자동차/모빌리티', [r'자동차', r'모빌리티', r'전장', r'부품', r'현대차그룹']),
    ('IT/소프트웨어/AI', [r'소프트웨어', r'AI', r'인공지능', r'클라우드', r'플랫폼', r'게임', r'메타버스', r'IT']),
    ('전력/에너지/원자력', [r'전력', r'원자력', r'신재생', r'태양광', r'수소', r'에너지', r'전선']),
    ('철강/소재/화학', [r'철강', r'소재', r'화학', r'정유', r'석유']),
    ('건설/인프라', [r'건설', r'인프라', r'토목']),
    ('엔터/미디어/소비재', [r'엔터', r'미디어', r'K-POP', r'화장품', r'음식료', r'유통', r'패션', r'면세'])
]

STOCK_NAME_KEYWORDS = [
    ('반도체/소부장', [r'반도체', r'칩', r'하이닉스', r'네오셈', r'가온칩스', r'자람테크', r'테크윙', r'와이씨', r'오픈엣지', r'디아이', r'제주반도체', r'에이직랜드', r'솔브레인', r'동진쎄미', r'하나마이크론', r'한미반도체', r'이오테크닉스', r'ISC', r'HPSP']),
    ('2차전지/배터리', [r'에코프로', r'엘앤에프', r'엔켐', r'대주전자', r'나노신소재', r'윤성에프앤씨', r'피엔티', r'신흥에스이씨']),
    ('바이오/헬스케어', [r'바이오', r'제약', r'셀트리온', r'유한양행', r'한미약품', r'알테오젠', r'오스코텍', r'펩트론', r'파마리서치', r'리가켐', r'휴젤', r'에스티팜', r'삼천당제약', r'케어젠', r'보로노이', r'클래시스', r'비올', r'원텍']),
    ('조선/방산/중공업', [r'한화에어로', r'현대로템', r'LIG넥스원', r'풍산', r'한국항공우주', r'HD현대', r'삼성중공업', r'한화오션', r'현대미포', r'STX엔진']),
    ('금융/지주', [r'금융', r'지주', r'은행', r'증권', r'보험', r'메리츠', r'삼성화재', r'DB손해보험', r'현대해상', r'키움증권']),
    ('자동차/모빌리티', [r'현대차', r'기아', r'모비스', r'HL만도', r'에스엘', r'서연이화', r'화신', r'성우하이텍']),
    ('IT/소프트웨어/AI', [r'NAVER', r'카카오', r'안랩', r'이스트소프트', r'폴라리스오피스', r'솔트룩스', r'마음AI', r'크래프톤', r'펄어비스', r'엔씨소프트', r'넷마블']),
    ('전력/에너지/원자력', [r'한국전력', r'두산에너빌리티', r'HD현대일렉트릭', r'효성중공업', r'LS ELECTRIC', r'LS일렉트릭', r'대한전선', r'일진전기', r'제룡전기']),
    ('철강/소재/화학', [r'POSCO', r'포스코', r'LG화학', r'롯데케미칼', r'금호석유', r'SK케미칼', r'SKC']),
    ('건설/인프라', [r'대우건설', r'GS건설', r'DL이앤씨', r'HDC현대산업', r'계룡건설']),
    ('엔터/미디어/소비재', [r'하이브', r'JYP', r'SM', r'YG', r'CJ ENM', r'스튜디오드래곤', r'아모레', r'코스맥스', r'한국콜마', r'APR', r'에이피알', r'삼양식품', r'농심', r'빙그레'])
]

def determine_sector(stk_name, stock_etfs):
    """
    ETF 편입 현황 및 종목명 키워드를 종합 분석하여 종목의 대표 섹터/테마를 판별합니다.
    """
    etfs = stock_etfs.get(stk_name, [])
    counts = Counter()
    for etf in etfs:
        for sector_label, patterns in SECTOR_RULES:
            if any(re.search(p, etf, re.IGNORECASE) for p in patterns):
                counts[sector_label] += 1
    if counts:
        return counts.most_common(1)[0][0]
    
    for sector_label, patterns in STOCK_NAME_KEYWORDS:
        if any(re.search(p, stk_name, re.IGNORECASE) for p in patterns):
            return sector_label
    return '일반 주도주'

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

    # 각 종목별 편입된 업종/테마 ETF 목록 딕셔너리 구축
    stock_etfs = {}
    stock_counter = Counter()
    for r in rows:
        stk_name = r.get("구성종목명", "").strip()
        etf_name = r.get("종목명", "").strip()
        cat_code = r.get("카테고리코드", "").strip()
        if is_valid_stock(stk_name):
            stock_counter[stk_name] += 1
            if cat_code == "2": # 업종/테마 카테고리
                stock_etfs.setdefault(stk_name, []).append(etf_name)

    # 가장 많이 ETF에 포함된 순서대로 정렬
    sorted_stocks = stock_counter.most_common()
    total_valid = len(sorted_stocks)

    print(f"✅ 필터링 완료: 현금/채권/해외주식 등을 제거하고 총 {total_valid}개 순수 주식 종목을 선별했습니다.")
    print("🔍 각 종목의 네이버 증권 6자리 종목코드 조회를 시작합니다...\n")
    
    result_rows = []
    start_time = time.time()
    # 3. 선별된 종목마다 네이버 API를 통해 6자리 종목코드 및 상세페이지 주소 매핑
    for rank, (stk_name, count) in enumerate(sorted_stocks, 1):
        code = get_stock_code(stk_name)
        sector = determine_sector(stk_name, stock_etfs)
        detail_url = f"https://stock.naver.com/domestic/stock/{code}/price" if code else ""
        
        row_dict = {
            "종목코드": code,
            "종목명": stk_name,
            "섹터": sector,
            "상세페이지": detail_url
        }
        if args.include_rank:
            row_dict = {"순위": rank, **row_dict}
            
        result_rows.append(row_dict)

        # 진행 상황 안내 출력 (20개 단위 및 1번째/마지막)
        if rank % 20 == 0 or rank == total_valid or rank == 1:
            elapsed = time.time() - start_time
            pct = (rank / total_valid) * 100
            avg_per_item = elapsed / rank
            remaining = (total_valid - rank) * avg_per_item
            code_display = code if code else "미발견"
            print(f"⏳ [{rank:3d}/{total_valid:3d}] ({pct:5.1f}%) | 코드매핑: {stk_name[:14]:<14} ({sector:<12}) -> {code_display:<6} | 경과: {elapsed:5.1f}초 (남은시간: 약 {remaining:4.1f}초)")

        time.sleep(0.02)

    # 4. 콘솔 상위 25개 미리보기 출력
    print("\n" + "=" * 90)
    print(f"{'순위':<4} | {'종목코드':<8} | {'종목명':<16} | {'섹터':<16} | {'네이버 상세페이지 주소'}")
    print("-" * 90)
    for idx, r in enumerate(result_rows[:25], 1):
        print(f"{idx:<4} | {r['종목코드']:<8} | {r['종목명']:<16} | {r['섹터']:<16} | {r['상세페이지']}")
    print("=" * 90)

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
