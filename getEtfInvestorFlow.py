#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 [4단계] 외국인/기관 수급 & 이동평균선(추세추종) 통합 분석 및 투자등급 산출 프로그램
================================================================================
1. 프로그램 역할:
   3단계에서 정제한 320여 개 주도주 종목(`data/etf_top_stocks.csv`)을 받아와서
   네이버 증권 API를 통해 실시간 외국인/기관 수급 데이터(쌍끌이 연속 매수일) 및 
   최근 120일간의 이동평균선(5일, 20일, 60일, 120일 MA)을 계산합니다.
   
   이후 추세추종 원칙에 따라 종목마다 **투자등급(A+, A, B, C)**을 부여하고, 
   이전 거래일 결과 파일(`reports/report_YYYYMMDD.csv`)과 자동 비교하여 
   **등급 상향/하향 변동(예: A -> A+) 및 변동 이유**를 기록합니다.

2. 입력 데이터:
   - CSV 파일: `data/etf_top_stocks.csv` (3단계 실행 결과)
   - 이전 분석 CSV 파일: `reports/report_이전날짜.csv` (등급 변동 비교용, 자동 검색)

3. 출력 결과:
   - CSV 파일: `reports/report_YYYYMMDD.csv` (예: `reports/report_20261002.csv`)
   - 💡 5단계 AI 분석 마크다운 리포트(`reports/report_YYYYMMDD.md`) 자동 호출 연동

4. 주요 작동 흐름 (누구나 이해할 수 있는 단계별 설명):
   - 1단계 [읽기]: 320개 주도주 목록을 불러옵니다.
   - 2단계 [비교분석 검색]: `reports/` 폴더에서 가장 최근에 저장된 이전 분석 CSV 파일을 찾습니다.
   - 3단계 [수급/차트 조회]: 네이버 API를 호출해 외국인/기관 동시 연속 매수 일수와 5/20/60/120일 이동평균선을 계산합니다.
   - 4단계 [등급 및 변동 부여]:
     - **A+ 등급**: 쌍끌이 매수(O) + 20일선 위(O) + 정배열(O) (5 >= 20 >= 60 >= 120일선)
     - **A 등급**: 쌍끌이 매수(O) + 20일선 위(O)
     - **B 등급**: 수급 또는 차트 1가지 만족
     - **C 등급**: 20일선 이탈 등 관망 대상
     - 이전 대비 **상향(A->A+)** 또는 **하향(A+->B)** 변동 이유를 자동 기록합니다.
   - 5단계 [저장 & 5단계 연동]: 결과를 `reports/report_YYYYMMDD.csv`로 저장하고 바로 5단계 AI 리포트 생성기를 자동 호출합니다.
================================================================================
"""

import urllib.request  # 웹 API 접속 라이브러리
import json            # JSON 데이터 해석 라이브러리
import csv             # CSV 파일 읽기/쓰기 도구
import argparse        # CLI 실행 옵션 파서
import sys             # 프로그램 시스템 제어 라이브러리
import time            # 연속 접속 시 대기시간(sleep) 도구
import os              # 디렉토리 생성 및 파일 검색 라이브러리
import glob            # 폴더 내 패턴(분석_*.csv)에 맞는 파일들을 찾아주는 라이브러리
from datetime import datetime # 오늘 날짜(YYYYMMDD) 계산 라이브러리

def parse_quant(quant_str):
    """
    네이버 수량 텍스트 (예: '+1,234,567' 또는 '-350,942')를 파이썬 정수(int) 숫자로 변환합니다.
    """
    if not quant_str:
        return 0
    clean = str(quant_str).replace(',', '').replace('+', '').strip()
    try:
        return int(clean)
    except ValueError:
        return 0

def get_latest_market_bizdate(sample_code="005930"):
    """
    네이버 증권 API를 호출하여 가장 최근 주식 시장 마감 거래일자(YYYYMMDD)를 자동 감지합니다.
    주말/공휴일/장 시작 전 실행 시 가장 최근에 장이 열렸던 거래일(예: 금요일)이 자동 설정됩니다.
    """
    url = f"https://m.stock.naver.com/api/stock/{sample_code}/trend?page=1&pageSize=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
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

def fetch_investor_trend(code, page_size=5):
    """
    네이버 증권 API를 통해 특정 종목의 최근 N일간 외국인/기관 매매동향 데이터를 수집합니다.
    
    :param code: 6자리 주식 종목코드 (예: '011200')
    :param page_size: 수집할 일수 (기본값: 최근 5일)
    :return: (외국인 연속매수일수, 기관 연속매수일수, 최근 3일 외인순매수 합, 최근 3일 기관순매수 합, 외국인보유율, 현재가)
    """
    url = f"https://m.stock.naver.com/api/stock/{code}/trend?page=1&pageSize={page_size}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            
            # API 응답 구조 검증
            if isinstance(data, list):
                trends = data
            elif isinstance(data, dict):
                trends = data.get("result", []) or data.get("message", {}).get("result", [])
            else:
                trends = []

            if not trends:
                return 0, 0, 0, 0, "0.0%", "0"

            # 가장 최근일의 현재가 및 외국인 소진율(보유율)
            latest = trends[0]
            close_price = latest.get("closePrice", "0")
            foreign_ratio = latest.get("foreignerHoldRatio") or latest.get("foreignHoldRate") or "0.0%"

            # 💡 외국인 연속 매수 일수 계산
            foreign_seq = 0
            for item in trends:
                f_quant_str = item.get("foreignerPureBuyQuant") or item.get("foreignPureBuyQuant") or "0"
                f_quant = parse_quant(f_quant_str)
                if f_quant > 0:
                    foreign_seq += 1
                else:
                    break  # 순매수가 끊기면 계산 중단

            # 💡 기관 연속 매수 일수 계산
            organ_seq = 0
            for item in trends:
                o_quant_str = item.get("organPureBuyQuant") or item.get("organPureBuy") or "0"
                o_quant = parse_quant(o_quant_str)
                if o_quant > 0:
                    organ_seq += 1
                else:
                    break  # 순매수가 끊기면 계산 중단

            # 최근 3일간 누적 순매수 수량 합산
            recent_3 = trends[:3]
            f_sum_3 = sum(parse_quant(i.get("foreignerPureBuyQuant") or i.get("foreignPureBuyQuant") or "0") for i in recent_3)
            o_sum_3 = sum(parse_quant(i.get("organPureBuyQuant") or i.get("organPureBuy") or "0") for i in recent_3)

            return foreign_seq, organ_seq, f_sum_3, o_sum_3, foreign_ratio, close_price

    except Exception:
        return 0, 0, 0, 0, "0.0%", "0"

def fetch_moving_averages(code):
    """
    네이버 증권 시세 API를 호출하여 최근 120일간의 일별 종가를 수집하고, 
    추세추종 핵심 차트지표인 5일, 20일, 60일, 120일 이동평균선(MA)을 계산합니다.
    """
    # 120일 이상의 이동평균선을 계산하기 위해 최근 120개 일별 가격 데이터를 수집
    prices = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 1페이지당 60개씩 총 2페이지(120일분) 수집
    for page in (1, 2):
        url = f"https://m.stock.naver.com/api/stock/{code}/price?page={page}&pageSize=60"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as res:
                data = json.loads(res.read().decode("utf-8"))
                p_list = data if isinstance(data, list) else data.get("result", [])
                for item in p_list:
                    cp_str = item.get("closePrice", "0").replace(',', '').strip()
                    if cp_str.isdigit() and int(cp_str) > 0:
                        prices.append(int(cp_str))
        except Exception:
            pass

    if len(prices) < 20:
        return None  # 데이터 부족 시 계산 불가능

    current_price = prices[0] # 오늘 종가 (현재가)
    
    # 각 이동평균선(MA) 계산 (최근 N일간의 종가 평균)
    ma5 = sum(prices[:5]) / 5.0 if len(prices) >= 5 else 0
    ma20 = sum(prices[:20]) / 20.0 if len(prices) >= 20 else 0
    ma60 = sum(prices[:60]) / 60.0 if len(prices) >= 60 else 0
    ma120 = sum(prices[:120]) / 120.0 if len(prices) >= 120 else 0

    # 20일 이동평균선 상회 여부 (20일선 위 = 상승 추세 기본 조건)
    above_ma20 = (current_price >= ma20) if ma20 > 0 else False

    # 이동평균선 완전 정배열 여부 (5일선 >= 20일선 >= 60일선 >= 120일선)
    is_aligned = False
    if ma5 > 0 and ma20 > 0 and ma60 > 0 and ma120 > 0:
        is_aligned = (ma5 >= ma20 >= ma60 >= ma120)

    return {
        "current_price": current_price,
        "above_ma20": above_ma20,
        "is_aligned": is_aligned,
        "ma5": ma5,
        "ma20": ma20,
        "ma60": ma60,
        "ma120": ma120
    }

def find_latest_previous_file(today_str):
    """
    `reports/` 폴더 내에서 오늘 날짜(YYYYMMDD) 이전의 가장 최근 분석 CSV 파일을 찾아냅니다.
    (이전 등급과 비교하여 등급 상향/하향 및 변동이유를 구하기 위함)
    """
    anal_dir = "reports"
    if not os.path.exists(anal_dir):
        return None, {}

    files = glob.glob(os.path.join(anal_dir, "report_*.csv"))
    prev_files = []
    
    for f in files:
        base_name = os.path.basename(f)
        date_part = base_name.replace("report_", "").replace(".csv", "")
        # 오늘 날짜 이전의 파일들만 수집
        if date_part.isdigit() and date_part < today_str:
            prev_files.append((date_part, f))

    if not prev_files:
        return None, {}

    # 가장 최근 날짜 순으로 정렬하여 이전 파일 선정
    prev_files.sort(key=lambda x: x[0], reverse=True)
    latest_prev_path = prev_files[0][1]

    # 이전 파일 데이터 읽어서 {종목코드: 투자등급} 딕셔너리로 저장
    prev_grades = {}
    try:
        with open(latest_prev_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('종목코드', '').strip()
                grade = row.get('투자등급', '').strip()
                if code and grade:
                    prev_grades[code] = grade
    except Exception as e:
        print(f"[⚠️ 경고] 이전 분석 파일({latest_prev_path}) 읽기 실패: {e}")

    return latest_prev_path, prev_grades

def calculate_grade(bi_buying, above_ma20, is_aligned):
    """
    추세추종 원칙에 의거하여 종목의 투자등급(A+, A, B, C)을 산출합니다.
    """
    if bi_buying and above_ma20 and is_aligned:
        return "A+"  # 최상위 대세상승주 (쌍끌이 + 20일선위 + 정배열)
    elif bi_buying and above_ma20:
        return "A"   # 우량 수급 상승주 (쌍끌이 + 20일선위)
    elif bi_buying or above_ma20:
        return "B"   # 관찰 대상 종목 (수급 또는 차트 중 1가지 만족)
    else:
        return "C"   # 매수 관망 대상 (20일선 아래 하락 추세 등)

def evaluate_grade_change(prev_grade, current_grade, is_aligned, above_ma20, bi_buying):
    """
    이전 등급과 현재 등급을 비교하여 '등급변동' 명칭 및 상세한 '변동이유' 텍스트를 만들어냅니다.
    """
    grade_order = {"A+": 4, "A": 3, "B": 2, "C": 1}

    if not prev_grade:
        return f"NEW ({current_grade})", f"{current_grade}등급 신규 포착"

    prev_val = grade_order.get(prev_grade, 0)
    curr_val = grade_order.get(current_grade, 0)

    if curr_val > prev_val: # 등급 상향
        change_text = f"{prev_grade} -> {current_grade} (상향)"
        reasons = []
        if current_grade == "A+" and is_aligned:
            reasons.append("정배열 달성(5>=20>=60>=120일)")
        if above_ma20 and not is_aligned:
            reasons.append("20일선 돌파")
        if bi_buying:
            reasons.append("외인/기관 쌍끌이 유입")
        reason_text = ", ".join(reasons) if reasons else "수급 및 차트 조건 개선"
        return change_text, reason_text

    elif curr_val < prev_val: # 등급 하향
        change_text = f"{prev_grade} -> {current_grade} (하향)"
        reasons = []
        if not above_ma20:
            reasons.append("20일선 이탈")
        if not bi_buying:
            reasons.append("쌍끌이 매수 중단")
        if prev_grade == "A+" and not is_aligned:
            reasons.append("정배열 이탈")
        reason_text = ", ".join(reasons) if reasons else "수급 및 차트 약화"
        return change_text, reason_text

    else: # 등급 유지
        return f"{current_grade} (유지)", "기존 등급 유지"

def main():
    """
    [4단계] 외국인/기관 수급 & 이동평균선 통합 분석 메인 실행 함수입니다.
    """
    default_input = "data/etf_top_stocks.csv"

    parser = argparse.ArgumentParser(description="[4단계] 외국인/기관 수급 & 이동평균선 통합 분석 스크립트")
    parser.add_argument("--input-csv", type=str, default=default_input, help=f"3단계 종목 파일 경로 (기본값: {default_input})")
    parser.add_argument("--save-csv", type=str, default=None, help="저장할 분석 CSV 경로 (미지정 시 최근 마감 거래일 기준 자동 생성)")
    parser.add_argument("--date", type=str, default=None, help="분석 대상 거래일자 (YYYYMMDD 형식, 미지정 시 API 최신 마감 거래일 자동 감지)")
    parser.add_argument("--limit", type=int, default=0, help="분석할 종목 수 제한 (테스트용, 0이면 전체)")
    parser.add_argument("--delay", type=float, default=0.03, help="요청 간 대기시간(초) (기본값: 0.03초)")
    args = parser.parse_args()

    # 분석 기준 거래일자 결정 (지정 날짜 > 네이버 API 최신 장마감 거래일)
    if args.date:
        target_date = args.date.strip()
    else:
        target_date = get_latest_market_bizdate()

    save_csv_path = args.save_csv if args.save_csv else f"reports/report_{target_date}.csv"

    today_cal = datetime.now().strftime("%Y-%m-%d")
    fmt_target = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}"
    print(f"\n📅 [거래일 기준 감지] 실행 시각: {today_cal} | 네이버 API 최근 마감 거래일(기준일자): {fmt_target}")
    print(f"📁 [결과 파일 경로] {save_csv_path}")

    # 1. 3단계 주도주 종목 데이터 불러오기
    try:
        with open(args.input_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            stock_list = list(reader)
    except Exception as e:
        print(f"[❌ 오류] '{args.input_csv}' 파일을 읽는 도중 에러가 발생했습니다: {e}")
        print("💡 팁: 3단계 스크립트(getEtfTopStockList.py)를 먼저 실행했는지 확인하세요.")
        sys.exit(1)

    total_stocks = len(stock_list)
    print(f"\n🚀 [4단계] '{args.input_csv}' 파일에서 총 {total_stocks}개의 주도주 목록을 읽었습니다.")

    # 2. 이전 거래일 분석 CSV 파일 검색 (기준일자 이전 파일 비교)
    prev_file_path, prev_grades = find_latest_previous_file(target_date)
    if prev_file_path:
        print(f"🔍 이전 분석 파일 발견: '{prev_file_path}' (이전 {len(prev_grades)}개 종목 등급과 비교합니다)")
    else:
        print("ℹ️ 이전 분석 파일이 없습니다. (오늘 최초 신규 비교 모드로 진행합니다)")

    if args.limit > 0:
        stock_list = stock_list[:args.limit]
        print(f"🔍 종목 수 제한 적용: {len(stock_list)}개 종목만 분석합니다.")

    print("📊 실시간 외국인/기관 수급 및 5/20/60/120일 이동평균선 수집/분석을 시작합니다...\n")

    analyzed_rows = []
    start_time = time.time()

    # 3. 320개 주도주 종목별 실시간 수급 및 차트 이동평균선 분석
    for idx, s in enumerate(stock_list, 1):
        code = s.get("종목코드", "").strip()
        name = s.get("종목명", "").strip()
        sector = s.get("섹터", "일반 주도주").strip()
        detail_url = s.get("상세페이지", "").strip()

        if not code:
            continue

        # 수급 데이터 (외인/기관 연속 매수일) 수집
        f_seq, o_seq, f_sum3, o_sum3, f_ratio, trend_price = fetch_investor_trend(code, page_size=5)

        # 이동평균선 (MA5, MA20, MA60, MA120) 계산
        ma_info = fetch_moving_averages(code)
        if not ma_info:
            time.sleep(args.delay)
            continue

        curr_price_str = f"{ma_info['current_price']:,}"
        bi_buying = (f_seq >= 1 and o_seq >= 1)  # 외인 & 기관 동시 연속 매수 (쌍끌이) 여부
        bi_str = "O" if bi_buying else "X"
        above_ma20_str = "O" if ma_info['above_ma20'] else "X"
        aligned_str = "O" if ma_info['is_aligned'] else "X"

        # 추세추종 투자등급(A+, A, B, C) 계산
        current_grade = calculate_grade(bi_buying, ma_info['above_ma20'], ma_info['is_aligned'])

        # 이전 날짜와 비교하여 등급 변동 및 이유 산출
        prev_grade = prev_grades.get(code, None)
        grade_change, change_reason = evaluate_grade_change(
            prev_grade, current_grade, ma_info['is_aligned'], ma_info['above_ma20'], bi_buying
        )

        analyzed_rows.append({
            "종목코드": code,
            "종목명": name,
            "섹터": sector,
            "투자등급": current_grade,
            "등급변동": grade_change,
            "변동이유": change_reason,
            "현재가": curr_price_str,
            "외국인보유율": f_ratio,
            "쌍끌이여부": bi_str,
            "외국인연속매수(일)": f_seq,
            "기관연속매수(일)": o_seq,
            "최근3일외인순매수": f"{f_sum3:,}",
            "최근3일기관순매수": f"{o_sum3:,}",
            "20일선위": above_ma20_str,
            "정배열여부": aligned_str,
            "MA5": f"{round(ma_info['ma5']):,}",
            "MA20": f"{round(ma_info['ma20']):,}",
            "MA60": f"{round(ma_info['ma60']):,}",
            "MA120": f"{round(ma_info['ma120']):,}",
            "상세페이지": detail_url
        })

        # 20개 단위 및 1번째/마지막 진행 상황 상세 출력
        if idx % 20 == 0 or idx == len(stock_list) or idx == 1:
            elapsed = time.time() - start_time
            pct = (idx / len(stock_list)) * 100
            avg_per_item = elapsed / idx
            remaining = (len(stock_list) - idx) * avg_per_item
            print(f"⏳ [{idx:3d}/{len(stock_list):3d}] ({pct:5.1f}%) | 수급분석: [{code}] {name[:12]:<12} ({sector:<12}) | 등급: {current_grade:<2} | 경과: {elapsed:5.1f}초 (남은시간: 약 {remaining:4.1f}초)")

        time.sleep(args.delay)

    # 4. 등급 정렬 (A+ -> A -> B -> C 순)
    grade_order = {"A+": 1, "A": 2, "B": 3, "C": 4}
    analyzed_rows.sort(key=lambda x: (grade_order.get(x["투자등급"], 99), x["종목코드"]))

    # 콘솔 상위 30개 결과 미리보기
    print("\n" + "=" * 145)
    print(f"{'종목코드':<8} | {'종목명':<16} | {'섹터':<14} | {'등급':<4} | {'등급변동':<16} | {'현재가':<10} | {'쌍끌이':<4} | {'20일선위':<6}")
    print("-" * 145)
    
    for r in analyzed_rows[:30]:
        print(f"{r['종목코드']:<8} | {r['종목명']:<16} | {r['섹터']:<14} | {r['투자등급']:<4} | {r['등급변동']:<16} | {r['현재가']:<10} | {r['쌍끌이여부']:<4} | {r['20일선위']:<6}")
    print("=" * 145)

    a_plus_count = sum(1 for r in analyzed_rows if r['투자등급'] == 'A+')
    a_count = sum(1 for r in analyzed_rows if r['투자등급'] == 'A')
    upgraded_count = sum(1 for r in analyzed_rows if "(상향)" in r['등급변동'])
    downgraded_count = sum(1 for r in analyzed_rows if "(하향)" in r['등급변동'])
    
    print(f"\n✅ [분석 완료] 총 {len(analyzed_rows)}개 종목 중 A+등급: {a_plus_count}개 / A등급: {a_count}개 (상향: {upgraded_count}개 / 하향: {downgraded_count}개)")

    # 5. `분석/분석_YYYYMMDD.csv` 파일 저장
    if save_csv_path:
        fieldnames = [
            "종목코드", "종목명", "섹터", "투자등급", "등급변동", "변동이유", "현재가", "외국인보유율", "쌍끌이여부",
            "외국인연속매수(일)", "기관연속매수(일)", "최근3일외인순매수", "최근3일기관순매수",
            "20일선위", "정배열여부", "MA5", "MA20", "MA60", "MA120", "상세페이지"
        ]
        save_dir = os.path.dirname(save_csv_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        with open(save_csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(analyzed_rows)
        print(f"💾 [저장 완료] 일별 수급 및 이평선 분석 결과가 저장되었습니다: {save_csv_path}")

        # 💡 5단계 AI 분석 마크다운 리포트(분석_YYYYMMDD.md) 100% 자동 생성 연동
        try:
            from getEtfAiReport import generate_ai_report
            print("\n🤖 [자동 연동] 5단계 AI 추세추종 분석 마크다운 리포트를 자동 생성합니다...")
            generate_ai_report(save_csv_path)
        except Exception as e:
            print(f"⚠️ AI 마크다운 리포트 생성 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
