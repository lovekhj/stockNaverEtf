#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 [검증용] 과거 일봉 + 외국인/기관 수급 수집 프로그램 (getStockHistory.py)
================================================================================
1. 프로그램 역할:
   종목선정 기준을 과거 데이터로 검증(백테스트)하기 위해, 종목별 과거 일봉과
   외국인/기관 순매수를 네이버 증권에서 받아 날짜 기준으로 한 파일에 합칩니다.
   매일 도는 1~5단계와는 별개이며 `main.py`에 연결되어 있지 않습니다.

2. 입력 데이터:
   - `--codes` 로 지정한 종목코드, 또는 `--all` 일 때 `data/etf_top_stocks.csv`

3. 출력 결과:
   - CSV 파일: `stockdata/{종목코드}.csv` (예: `stockdata/011200.csv`)
   - 지수: `stockdata/KOSPI.csv`, `stockdata/KOSDAQ.csv` (`--index` 지정 시)
   - 열: 날짜, 시가, 고가, 저가, 종가, 거래량, 외국인순매수, 기관순매수
   - 💡 `stockdata/` 는 `.gitignore` 대상입니다. 공개 저장소에 올리지 않습니다.

4. 주요 작동 흐름:
   - 1단계 [일봉]: 차트 API에서 수정주가 일봉을 기간 전체 한 번에 받습니다.
   - 2단계 [수급]: 수급 API는 한 번에 60거래일만 주므로 날짜를 넘겨 가며 이어 받습니다.
   - 3단계 [합치기]: 일봉 날짜를 기준으로 수급을 붙입니다.
   - 4단계 [저장]: 매번 기간 전체를 새로 받아 파일을 덮어씁니다.

5. 데이터 주의:
   - 종가는 수정주가(액면분할·증자 반영)이고, 거래량과 순매수 수량은 수정 전 값입니다.
   - 수급이 없는 날은 0이 아니라 빈 칸으로 둡니다. (0 = 순매수 없음, 빈 칸 = 모름)
   - 장 마감 후 확정치이며, 네이버 증권 비공식 API라 구조가 바뀌면 멈출 수 있습니다.
================================================================================
"""

import urllib.request  # 웹 API 접속 라이브러리
import json            # JSON 데이터 해석 라이브러리
import csv             # CSV 파일 읽기/쓰기 도구
import argparse        # CLI 실행 옵션 파서
import sys             # 프로그램 시스템 제어 라이브러리
import time            # 연속 접속 시 대기시간(sleep) 도구
import os              # 디렉토리 생성 라이브러리
from datetime import datetime, timedelta # 수집 기간 계산 라이브러리

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
CSV_HEADER = ["날짜", "시가", "고가", "저가", "종가", "거래량", "외국인순매수", "기관순매수"]
INDEX_SYMBOLS = ("KOSPI", "KOSDAQ")
TREND_PAGE_SIZE = 60  # 수급 API가 허용하는 최대값 (더 크게 주면 400 오류)

def fetch_text(url, retries=3):
    """
    URL을 호출해 본문 문자열을 돌려줍니다. 실패하면 잠시 쉬고 다시 시도하며,
    끝까지 실패하면 None을 돌려줍니다.
    """
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as res:
                return res.read().decode("utf-8")
        except Exception:
            time.sleep(1 + attempt)
    return None

def parse_quant(quant_str):
    """
    '+309,030', '-456,208' 같은 순매수 문자열을 정수로 바꿉니다.
    """
    return int(str(quant_str).replace(",", "").replace("+", "").strip())

def fetch_daily_prices(symbol, start_date, end_date):
    """
    네이버 차트 API에서 수정주가 일봉을 받습니다. 종목코드와 지수(KOSPI, KOSDAQ) 모두 됩니다.

    :return: [(YYYYMMDD, 시가, 고가, 저가, 종가, 거래량), ...] 날짜 오름차순. 실패 시 None
    """
    url = (f"https://fchart.stock.naver.com/siseJson.naver?symbol={symbol}&requestType=1"
           f"&startTime={start_date}&endTime={end_date}&timeframe=day")
    text = fetch_text(url)
    if text is None:
        return None
    try:
        # 응답이 작은따옴표를 쓰는 배열이라 큰따옴표로 바꿔야 JSON으로 읽힌다
        rows = json.loads(text.replace("'", '"'))
    except ValueError:
        return None
    # 첫 줄은 열 이름(['날짜', '시가', ...])이라 건너뛴다
    return [tuple(r[:6]) for r in rows[1:]]

def fetch_investor_flows(code, start_date, end_date):
    """
    외국인/기관 순매수(수량)를 start_date까지 거슬러 올라가며 받습니다.
    수급 API는 `page`를 무시하고 `bizdate` 이전 60거래일만 주므로,
    받은 구간의 가장 오래된 날짜를 다음 `bizdate`로 넣어 이어 받습니다.

    :return: ({YYYYMMDD: (외국인순매수, 기관순매수)}, 정상완료 여부)
    """
    flows = {}
    # bizdate 당일은 포함되지 않으므로 종료일 다음 날부터 시작한다
    cursor = (datetime.strptime(end_date, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
    while cursor > start_date:
        url = f"https://m.stock.naver.com/api/stock/{code}/trend?pageSize={TREND_PAGE_SIZE}&bizdate={cursor}"
        text = fetch_text(url)
        if text is None:
            return flows, False
        try:
            trends = json.loads(text)
        except ValueError:
            return flows, False
        if not isinstance(trends, list) or not trends:
            break  # 상장 이전이라 더 받을 데이터가 없음
        for item in trends:
            try:
                flows[item["bizdate"]] = (parse_quant(item["foreignerPureBuyQuant"]),
                                          parse_quant(item["organPureBuyQuant"]))
            except (KeyError, ValueError):
                pass  # 값이 없는 날은 빈 칸으로 남긴다
        oldest = trends[-1]["bizdate"]
        if oldest >= cursor:
            break  # 날짜가 더 내려가지 않으면 무한 반복을 막기 위해 중단
        cursor = oldest
    return flows, True

def save_history(symbol, prices, flows, save_dir):
    """
    일봉에 수급을 붙여 `stockdata/{symbol}.csv` 로 저장하고, 수급이 빈 날짜 목록을 돌려줍니다.
    """
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, f"{symbol}.csv")
    missing = []
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for ymd, open_p, high_p, low_p, close_p, volume in prices:
            flow = flows.get(ymd) if flows is not None else None
            if flows is not None and flow is None:
                missing.append(ymd)
            foreign, organ = flow if flow else ("", "")
            writer.writerow([f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}", open_p, high_p, low_p, close_p, volume, foreign, organ])
    return missing

def load_universe_codes(input_csv):
    """
    3단계 결과 파일에서 종목코드를 중복 없이 읽습니다.
    """
    codes = []
    with open(input_csv, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = row.get("종목코드", "").strip()
            if code and code not in codes:
                codes.append(code)
    return codes

def main():
    """
    [검증용] 과거 일봉 + 수급 수집 메인 실행 함수입니다.
    """
    default_input = "data/etf_top_stocks.csv"

    parser = argparse.ArgumentParser(description="[검증용] 과거 일봉 + 외국인/기관 수급 수집 스크립트")
    parser.add_argument("--codes", type=str, default=None, help="수집할 종목코드 (쉼표로 구분, 예: 011200,086520)")
    parser.add_argument("--all", action="store_true", help=f"{default_input} 의 전 종목 수집")
    parser.add_argument("--index", action="store_true", help="코스피·코스닥 지수 일봉도 수집")
    parser.add_argument("--input-csv", type=str, default=default_input, help=f"--all 일 때 읽을 종목 파일 (기본값: {default_input})")
    parser.add_argument("--years", type=int, default=5, help="수집 기간(년) (기본값: 5)")
    parser.add_argument("--save-dir", type=str, default="stockdata", help="저장 폴더 (기본값: stockdata)")
    parser.add_argument("--limit", type=int, default=0, help="수집할 종목 수 제한 (테스트용, 0이면 전체)")
    parser.add_argument("--delay", type=float, default=0.2, help="종목 간 대기시간(초) (기본값: 0.2초)")
    args = parser.parse_args()

    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    elif args.all:
        codes = load_universe_codes(args.input_csv)
    else:
        codes = []
    if args.limit > 0:
        codes = codes[:args.limit]
    if not codes and not args.index:
        parser.error("--codes, --all, --index 중 하나는 지정해야 합니다.")

    today = datetime.now()
    end_date = today.strftime("%Y%m%d")
    start_date = today.replace(year=today.year - args.years).strftime("%Y%m%d")
    print(f"📅 수집 기간: {start_date} ~ {end_date} / 종목 {len(codes)}개 / 저장 폴더: {args.save_dir}/")

    failed = []

    if args.index:
        for symbol in INDEX_SYMBOLS:
            prices = fetch_daily_prices(symbol, start_date, end_date)
            if not prices:
                failed.append(symbol)
                print(f"❌ {symbol}: 일봉 수집 실패")
                continue
            save_history(symbol, prices, None, args.save_dir)
            print(f"✅ {symbol}: {len(prices)}일 ({prices[0][0]} ~ {prices[-1][0]})")

    for i, code in enumerate(codes, 1):
        prices = fetch_daily_prices(code, start_date, end_date)
        if not prices:
            failed.append(code)
            print(f"❌ [{i}/{len(codes)}] {code}: 일봉 수집 실패")
            continue
        # 상장이 수집 시작일보다 늦은 종목은 상장일까지만 수급을 받는다
        flows, completed = fetch_investor_flows(code, prices[0][0], end_date)
        if not completed:
            # 수급이 중간에 끊긴 파일은 남기지 않는다. 일부만 빈 칸인 파일이 정상 파일로 보이면 안 된다
            failed.append(code)
            print(f"❌ [{i}/{len(codes)}] {code}: 수급 수집 중단 (저장하지 않음)")
            continue
        missing = save_history(code, prices, flows, args.save_dir)
        note = f", 수급 빈 날 {len(missing)}일 (예: {', '.join(missing[:3])})" if missing else ""
        print(f"✅ [{i}/{len(codes)}] {code}: {len(prices)}일 ({prices[0][0]} ~ {prices[-1][0]}){note}")
        time.sleep(args.delay)

    if failed:
        print(f"\n⚠️ 실패 {len(failed)}개: {', '.join(failed)}")
        sys.exit(1)
    print("\n🎉 수집 완료")

if __name__ == "__main__":
    main()
