#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 [4단계] 일봉 분석 프로그램: 이동평균선, 매수신호, 추세 통과 (getEtfInvestorFlow.py)
================================================================================
1. 프로그램 역할:
   3단계에서 정제한 종목(`data/etf_top_stocks.csv`)의 수정주가 일봉을 네이버 증권에서 받아
   이동평균선(5·20·60·120일), 등락률, 20일 이격도, 차트 꼬리, 매수신호(A/B/C),
   추세 통과 여부와 3개월 상승률을 계산해 CSV로 저장합니다.

   (2026-10-10: 외국인·기관 수급 수집과 투자등급(A+/A/B/C) 산출을 없앴습니다.
    과거 검증에서 등급 순서가 이후 수익률과 맞지 않았고, 화면·리포트에서 쓰지 않게 됐기 때문입니다.
    파일 이름은 이 스크립트를 부르는 곳이 많아 그대로 둡니다.)

2. 입력 데이터:
   - CSV 파일: `data/etf_top_stocks.csv` (3단계 실행 결과)
   - CSV 파일: `data/stock_sectors.csv` (종목별 시장·섹터. 없으면 3단계의 섹터를 그대로 씁니다)

3. 출력 결과:
   - CSV 파일: `reports/report_YYYYMMDD.csv`
   - 5단계 리포트(`reports/report_YYYYMMDD.md`, PDF) 자동 생성 연동

4. 판정 규칙:
   - 매수신호와 추세 통과의 정의는 `buySignal.py`에 있습니다.
   - 검증 중인 기준이며 매수·매도 추천이 아닙니다. 데이터: 네이버 증권 일봉(수정주가), 장 마감 후 확정치.
================================================================================
"""

import urllib.request  # 웹 API 접속 라이브러리
import json            # JSON 데이터 해석 라이브러리
import csv             # CSV 파일 읽기/쓰기 도구
import argparse        # CLI 실행 옵션 파서
import sys             # 프로그램 시스템 제어 라이브러리
import time            # 연속 접속 시 대기시간(sleep) 도구
import os              # 디렉토리 생성 및 파일 검색 라이브러리
from datetime import datetime, timedelta # 오늘 날짜(YYYYMMDD) 계산 라이브러리

from getStockHistory import fetch_daily_prices  # 수정주가 일봉 수집 (백테스트와 같은 출처)
from buySignal import judge_bars, judge_trend, measure_last_bar, is_strong_close, SIGNAL_NONE, SIGNAL_BUY, SIGNAL_REVIEW

CHART_LOOKBACK_DAYS = 400   # 일봉을 받는 기간 (달력 일수). 1년 최고 종가에 250거래일이 필요하다
SECTOR_CSV = "data/stock_sectors.csv"   # 종목별 시장·섹터 (네이버 업종을 묶은 분류)
CANDLE_LONG_TAIL = 0.5      # 긴 꼬리: 꼬리가 당일 범위에서 차지하는 비율 하한
CANDLE_DOJI_BODY = 0.1      # 십자형: 몸통 비율 상한
CANDLE_LONG_BODY = 0.7      # 장대봉: 몸통 비율 하한

FIELDNAMES = [
    "종목코드", "종목명", "시장", "섹터", "매수신호", "매수신호사유", "등락률", "현재가",
    "20일이격도", "차트꼬리", "추세통과", "3개월수익률", "고점대비", "강한마감",
    "MA5", "MA20", "MA60", "MA120", "상세페이지"
]

def get_latest_market_bizdate(sample_code="005930"):
    """
    네이버 증권 API를 호출하여 가장 최근 주식 시장 마감/거래일자(YYYYMMDD)를 자동 감지합니다.
    주말/공휴일/장 시작 전 실행 시 가장 최근에 장이 열렸던 거래일(예: 금요일)이 자동 설정됩니다.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    # 1) price API (일별 시세 거래일) 우선 감지
    url_price = f"https://m.stock.naver.com/api/stock/{sample_code}/price?page=1&pageSize=1"
    try:
        req = urllib.request.Request(url_price, headers=headers)
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            prices = data if isinstance(data, list) else data.get("result", [])
            if prices and isinstance(prices, list) and len(prices) > 0:
                traded_at = prices[0].get("localTradedAt", "").replace("-", "").strip()
                if traded_at and len(traded_at) == 8 and traded_at.isdigit():
                    return traded_at
    except Exception:
        pass

    # 2) trend API (수급 거래일) 차선 감지
    url_trend = f"https://m.stock.naver.com/api/stock/{sample_code}/trend?page=1&pageSize=1"
    try:
        req = urllib.request.Request(url_trend, headers=headers)
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            trends = data if isinstance(data, list) else data.get("result", [])
            if trends and isinstance(trends, list) and len(trends) > 0:
                bizdate = trends[0].get("bizdate", "").strip()
                if bizdate and len(bizdate) == 8 and bizdate.isdigit():
                    return bizdate
    except Exception:
        pass

    return datetime.now().strftime("%Y%m%d")

def fetch_chart_bars(code, target_date):
    """
    기준일자까지의 수정주가 일봉을 받습니다. 이평선, 등락률, 차트 꼬리, 매수신호를 모두 이 일봉으로 계산합니다.
    (시세 API는 수정주가가 아니고, 최근 하루의 시가·거래량·전일 대비가 한국거래소 종가 기준과 달라서 쓰지 않습니다)

    :param code: 6자리 주식 종목코드
    :param target_date: 기준 거래일자 (YYYYMMDD)
    :return: [(YYYYMMDD, 시가, 고가, 저가, 종가, 거래량), ...] 날짜 오름차순. 실패 시 None
    """
    start_date = (datetime.strptime(target_date, "%Y%m%d") - timedelta(days=CHART_LOOKBACK_DAYS)).strftime("%Y%m%d")
    return fetch_daily_prices(code, start_date, target_date)

def analyze_moving_averages(bars):
    """
    수정주가 일봉으로 5일, 20일, 60일, 120일 이동평균선(MA)과 등락률을 계산합니다.
    """
    prices = [b[4] for b in bars if b[4] > 0]
    if len(prices) < 20:
        return None  # 데이터 부족 시 계산 불가능

    current_price = prices[-1] # 기준일자 종가 (현재가)

    return {
        "current_price": current_price,
        "chg_rate": f"{(current_price / prices[-2] - 1) * 100:+.2f}%",  # 전일 종가 대비 (한국거래소 종가 기준)
        "ma5": sum(prices[-5:]) / 5.0,
        "ma20": sum(prices[-20:]) / 20.0,
        "ma60": sum(prices[-60:]) / 60.0 if len(prices) >= 60 else 0,
        "ma120": sum(prices[-120:]) / 120.0 if len(prices) >= 120 else 0
    }

def classify_candle(open_p, high_p, low_p, close_p):
    """
    하루 일봉의 시가·고가·저가·종가로 캔들 모양을 분류합니다.
    꼬리와 몸통이 당일 범위(고가 - 저가)에서 차지하는 비율로 나눕니다.

    :return: 캔들 모양 문자열. 거래가 없어 판정할 수 없으면 빈 문자열
    """
    spread = high_p - low_p
    if open_p <= 0 or spread <= 0:
        return ""  # 거래정지이거나 하루 종일 한 가격
    body = abs(close_p - open_p) / spread
    upper_tail = (high_p - max(open_p, close_p)) / spread
    lower_tail = (min(open_p, close_p) - low_p) / spread
    is_up = close_p >= open_p

    if upper_tail >= CANDLE_LONG_TAIL:
        return "긴 윗꼬리"
    if lower_tail >= CANDLE_LONG_TAIL:
        return "긴 아래꼬리"
    if body <= CANDLE_DOJI_BODY:
        return "십자형"
    if body >= CANDLE_LONG_BODY:
        return "장대양봉" if is_up else "장대음봉"
    return "보통 양봉" if is_up else "보통 음봉"

def judge_buy_signal(bars, target_date):
    """
    기준일자 종가 기준의 매수신호(A/B/C)와 사유를 돌려줍니다.

    :return: (매수신호, 사유)
    """
    if bars[-1][0] != target_date:
        return SIGNAL_NONE, f"기준일자 일봉 없음 (최근 {bars[-1][0]})"
    return judge_bars([b[4] for b in bars], [b[5] for b in bars])

def load_stock_sectors(path=SECTOR_CSV):
    """
    종목별 시장·섹터 파일을 읽습니다. 파일이 없으면 빈 딕셔너리를 돌려주고 3단계의 섹터를 그대로 씁니다.

    :return: {종목코드: (시장, 섹터)}
    """
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8-sig") as f:
        return {r["종목코드"].strip(): (r["시장"].strip(), r["섹터"].strip()) for r in csv.DictReader(f)}

def judge_sector_columns(bars, target_date):
    """
    섹터별 종목조회 화면에 쓰는 열(추세통과, 3개월수익률, 고점대비, 강한마감)을 돌려줍니다.
    기준일자 일봉이 없거나 일봉이 모자라면 모두 "-" 입니다.
    """
    empty = {"추세통과": "-", "3개월수익률": "-", "고점대비": "-", "강한마감": "-"}
    closes = [b[4] for b in bars]
    volumes = [b[5] for b in bars]
    trend = judge_trend(closes) if bars[-1][0] == target_date else None
    if trend is None or volumes[-1] == 0:
        return empty
    passed, ret_3m, from_high = trend
    return {
        "추세통과": "O" if passed else "X",
        "3개월수익률": f"{ret_3m * 100:+.1f}%",
        "고점대비": f"{from_high * 100:+.1f}%",
        "강한마감": "O" if is_strong_close(*measure_last_bar(closes, volumes)) else "X",
    }

def main():
    """
    [4단계] 일봉 분석 메인 실행 함수입니다.
    """
    default_input = "data/etf_top_stocks.csv"

    parser = argparse.ArgumentParser(description="[4단계] 일봉 분석 스크립트 (이동평균선, 매수신호, 추세 통과)")
    parser.add_argument("--input-csv", type=str, default=default_input, help=f"3단계 종목 파일 경로 (기본값: {default_input})")
    parser.add_argument("--save-csv", type=str, default=None, help="저장할 분석 CSV 경로 (미지정 시 최근 마감 거래일 기준 자동 생성)")
    parser.add_argument("--date", type=str, default=None, help="분석 대상 거래일자 (YYYYMMDD 형식, 미지정 시 API 최신 마감 거래일 자동 감지)")
    parser.add_argument("--limit", type=int, default=0, help="분석할 종목 수 제한 (테스트용, 0이면 전체)")
    parser.add_argument("--delay", type=float, default=0.03, help="요청 간 대기시간(초) (기본값: 0.03초)")
    args = parser.parse_args()

    # 분석 기준 거래일자 결정 (지정 날짜 > 네이버 API 최신 장마감 거래일)
    target_date = args.date.strip() if args.date else get_latest_market_bizdate()
    save_csv_path = args.save_csv if args.save_csv else f"reports/report_{target_date}.csv"

    today_cal = datetime.now().strftime("%Y-%m-%d")
    fmt_target = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}"
    print(f"\n📅 [거래일 기준 감지] 실행 시각: {today_cal} | 네이버 API 최근 마감 거래일(기준일자): {fmt_target}")
    print(f"📁 [결과 파일 경로] {save_csv_path}")

    # 1. 3단계 종목 데이터 불러오기
    try:
        with open(args.input_csv, "r", encoding="utf-8-sig") as f:
            stock_list = list(csv.DictReader(f))
    except Exception as e:
        print(f"[❌ 오류] '{args.input_csv}' 파일을 읽는 도중 에러가 발생했습니다: {e}")
        print("💡 팁: 3단계 스크립트(getEtfTopStockList.py)를 먼저 실행했는지 확인하세요.")
        sys.exit(1)

    print(f"\n🚀 [4단계] '{args.input_csv}' 파일에서 총 {len(stock_list)}개의 종목을 읽었습니다.")
    if args.limit > 0:
        stock_list = stock_list[:args.limit]
        print(f"🔍 종목 수 제한 적용: {len(stock_list)}개 종목만 분석합니다.")

    stock_sectors = load_stock_sectors()
    if not stock_sectors:
        print(f"ℹ️ '{SECTOR_CSV}' 파일이 없어 3단계의 섹터를 그대로 씁니다. (시장 칸은 '-')")

    print("📊 수정주가 일봉 수집과 이동평균선·매수신호·추세 통과 분석을 시작합니다...\n")

    analyzed_rows = []
    price_failed = []  # 일봉을 받지 못해 결과에서 빠진 종목
    start_time = time.time()

    # 2. 종목별 일봉 수집과 분석
    for idx, s in enumerate(stock_list, 1):
        code = s.get("종목코드", "").strip()
        name = s.get("종목명", "").strip()
        if not code:
            continue
        market, sector = stock_sectors.get(code, ("-", s.get("섹터", "-").strip()))

        # 실패하면 한 번 더 시도한다
        bars = fetch_chart_bars(code, target_date) or fetch_chart_bars(code, target_date)
        ma_info = analyze_moving_averages(bars) if bars else None
        if not ma_info:
            price_failed.append(f"[{code}] {name}")
            time.sleep(args.delay)
            continue

        disparity = round(ma_info['current_price'] / ma_info['ma20'] * 100, 1)

        # 매수신호 (강한 마감 + 추세 통과 후보 규칙, 기준일자 종가 매수 기준)
        buy_signal, buy_reason = judge_buy_signal(bars, target_date)

        # 차트 꼬리
        last_bar = bars[-1]
        candle_str = classify_candle(last_bar[1], last_bar[2], last_bar[3], last_bar[4]) if last_bar[5] > 0 else ""

        analyzed_rows.append({
            "종목코드": code,
            "종목명": name,
            "시장": market,
            "섹터": sector,
            "매수신호": buy_signal,
            "매수신호사유": buy_reason,
            "등락률": ma_info["chg_rate"],
            "현재가": f"{round(ma_info['current_price']):,}",
            "20일이격도": f"{disparity}%",
            "차트꼬리": candle_str,
            **judge_sector_columns(bars, target_date),
            "MA5": f"{round(ma_info['ma5']):,}",
            "MA20": f"{round(ma_info['ma20']):,}",
            "MA60": f"{round(ma_info['ma60']):,}",
            "MA120": f"{round(ma_info['ma120']):,}",
            "상세페이지": s.get("상세페이지", "").strip()
        })

        # 20개 단위 및 1번째/마지막 진행 상황 출력
        if idx % 20 == 0 or idx == len(stock_list) or idx == 1:
            elapsed = time.time() - start_time
            remaining = (len(stock_list) - idx) * (elapsed / idx)
            print(f"⏳ [{idx:3d}/{len(stock_list):3d}] ({idx / len(stock_list) * 100:5.1f}%) | [{code}] {name[:12]:<12} ({sector:<12}) | 매수신호: {buy_signal} | 경과: {elapsed:5.1f}초 (남은시간: 약 {remaining:4.1f}초)")

        time.sleep(args.delay)

    # 3. 정렬: 매수신호 A -> B -> C -> 신호 없음, 같은 신호 안에서는 종목코드 순
    signal_order = {SIGNAL_BUY: 1, SIGNAL_REVIEW: 2}
    analyzed_rows.sort(key=lambda r: (signal_order.get(r["매수신호"], 4 if r["매수신호"] == SIGNAL_NONE else 3), r["종목코드"]))

    buy_rows = [r for r in analyzed_rows if r["매수신호"] == SIGNAL_BUY]
    review_count = sum(1 for r in analyzed_rows if r["매수신호"] == SIGNAL_REVIEW)
    pass_count = sum(1 for r in analyzed_rows if r["추세통과"] == "O")
    print(f"\n✅ [분석 완료] 총 {len(analyzed_rows)}개 종목 | 추세 통과: {pass_count}개")
    print(f"🎯 [매수신호] {SIGNAL_BUY}: {len(buy_rows)}개 / {SIGNAL_REVIEW}: {review_count}개 (기준일자 종가 매수 기준, 검증 중인 후보 규칙)")
    for r in buy_rows:
        print(f"   - [{r['종목코드']}] {r['종목명']} {r['현재가']}원 | {r['매수신호사유']}")
    if price_failed:
        print(f"⚠️ [일봉 수집 실패] {len(price_failed)}개 (결과에서 제외): {', '.join(price_failed)}")

    # 4. `reports/report_YYYYMMDD.csv` 저장
    if save_csv_path:
        save_dir = os.path.dirname(save_csv_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        with open(save_csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(analyzed_rows)
        print(f"💾 [저장 완료] 일봉 분석 결과가 저장되었습니다: {save_csv_path}")

        # 5단계 마크다운·PDF 리포트 자동 생성 연동
        try:
            from getEtfAiReport import generate_ai_report
            print("\n🤖 [자동 연동] 5단계 추세추종 분석 리포트를 자동 생성합니다...")
            generate_ai_report(save_csv_path)
        except Exception as e:
            print(f"⚠️ 마크다운 리포트 생성 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
