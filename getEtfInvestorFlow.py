import urllib.request
import json
import csv
import argparse
import sys
import time

def parse_quant(quant_str):
    """
    '+1,234,567' 또는 '-350,942' 수량 문자열을 정수(int)로 변환합니다.
    """
    if not quant_str:
        return 0
    clean = str(quant_str).replace(',', '').replace('+', '').strip()
    try:
        return int(clean)
    except ValueError:
        return 0

def fetch_investor_trend(code, page_size=5):
    """
    네이버 증권 API를 통해 특정 종목의 최근 N일간 투자자별 매매동향(외인/기관/개인)을 수집합니다.
    """
    url = f"https://m.stock.naver.com/api/stock/{code}/trend?page=1&pageSize={page_size}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"[경고] 종목코드 {code} 수급 데이터 조회 실패: {e}")
        return []

def analyze_investor_flow(rows):
    """
    최근 일별 수급 데이터를 바탕으로 연속 매수 일수 및 쌍끌이 여부를 분석합니다.
    """
    if not rows:
        return {
            "현재가": "0",
            "외국인보유율": "0.00%",
            "외국인연속매수": 0,
            "기관연속매수": 0,
            "쌍끌이여부": "X",
            "최근3일외인순매수": 0,
            "최근3일기관순매수": 0
        }

    latest = rows[0]
    close_price = latest.get("closePrice", "0")
    hold_ratio = latest.get("foreignerHoldRatio", "0.00%")

    # 연속 매수 일수 계산
    f_streak = 0
    for r in rows:
        val = parse_quant(r.get("foreignerPureBuyQuant"))
        if val > 0:
            f_streak += 1
        else:
            break

    o_streak = 0
    for r in rows:
        val = parse_quant(r.get("organPureBuyQuant"))
        if val > 0:
            o_streak += 1
        else:
            break

    # 최근 3일 누적 순매수 수량
    recent_3 = rows[:3]
    f_sum_3 = sum(parse_quant(r.get("foreignerPureBuyQuant")) for r in recent_3)
    o_sum_3 = sum(parse_quant(r.get("organPureBuyQuant")) for r in recent_3)

    # 최근일 기준 외인/기관 동시 순매수 여부 (쌍끌이)
    latest_f = parse_quant(latest.get("foreignerPureBuyQuant"))
    latest_o = parse_quant(latest.get("organPureBuyQuant"))
    dual_buying = "O" if (latest_f > 0 and latest_o > 0) else "X"

    return {
        "현재가": close_price,
        "외국인보유율": hold_ratio,
        "외국인연속매수": f_streak,
        "기관연속매수": o_streak,
        "쌍끌이여부": dual_buying,
        "최근3일외인순매수": f_sum_3,
        "최근3일기관순매수": o_sum_3
    }

def fetch_moving_averages(code):
    """
    네이버 증권 일별 가격 API를 통해 최근 120일 종가를 수집하여
    5일, 20일, 60일, 120일 이동평균선과 20일선 위 여부, 정배열 여부를 계산합니다.
    """
    close_prices = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for page in (1, 2):
        url = f"https://m.stock.naver.com/api/stock/{code}/price?page={page}&pageSize=60"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as res:
                data = json.loads(res.read().decode("utf-8"))
                if isinstance(data, list):
                    for item in data:
                        cp_str = item.get("closePrice", "0")
                        cp = parse_quant(cp_str)
                        if cp > 0:
                            close_prices.append(cp)
        except Exception:
            break

    if not close_prices:
        return {
            "20일선위": "X",
            "정배열여부": "X",
            "MA5": 0,
            "MA20": 0,
            "MA60": 0,
            "MA120": 0
        }

    curr_price = close_prices[0]
    
    ma5 = round(sum(close_prices[:5]) / len(close_prices[:5])) if len(close_prices) >= 5 else 0
    ma20 = round(sum(close_prices[:20]) / len(close_prices[:20])) if len(close_prices) >= 20 else 0
    ma60 = round(sum(close_prices[:60]) / len(close_prices[:60])) if len(close_prices) >= 60 else 0
    ma120 = round(sum(close_prices[:120]) / len(close_prices[:120])) if len(close_prices) >= 120 else 0

    above_ma20 = "O" if (ma20 > 0 and curr_price >= ma20) else "X"
    is_aligned = "O" if (ma5 > 0 and ma20 > 0 and ma60 > 0 and ma120 > 0 and ma5 >= ma20 >= ma60 >= ma120) else "X"

    return {
        "20일선위": above_ma20,
        "정배열여부": is_aligned,
        "MA5": ma5,
        "MA20": ma20,
        "MA60": ma60,
        "MA120": ma120
    }

def determine_investment_grade(dual_buying, above_ma20, is_aligned):
    """
    수급(쌍끌이)과 기술적 지표(20일선위, 정배열)를 종합하여 투자등급(A+, A, B, C)을 정합니다.
    - A+: 쌍끌이(O) + 20일선위(O) + 정배열(O) (최상위 대세상승주)
    - A : 쌍끌이(O) + 20일선위(O) (우량 수급주)
    - B : 쌍끌이(O) 또는 20일선위(O) (관심주)
    - C : 조건 미충족 (관망 대상)
    """
    if dual_buying == "O" and above_ma20 == "O" and is_aligned == "O":
        return "A+"
    elif dual_buying == "O" and above_ma20 == "O":
        return "A"
    elif dual_buying == "O" or above_ma20 == "O":
        return "B"
    else:
        return "C"

import glob

def find_latest_previous_file(today_str):
    """
    현재 실행 날짜(today_str e.g. 20261003)보다 이전인 가장 최근의 분석 CSV 파일을 찾습니다.
    """
    analysis_folders = sorted(glob.glob("분석_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]"))
    prev_files = []
    for folder in analysis_folders:
        folder_name = os.path.basename(folder)
        date_part = folder_name.replace("분석_", "")
        if date_part < today_str:
            csv_path = os.path.join(folder, f"분석_{date_part}.csv")
            if os.path.exists(csv_path):
                prev_files.append((date_part, csv_path))
    
    if prev_files:
        prev_files.sort(key=lambda x: x[0], reverse=True)
        return prev_files[0][1]
    
    # 예전 통합 CSV 파일이 존재할 경우 fallback
    if os.path.exists("data/etf_investor_flow.csv"):
        return "data/etf_investor_flow.csv"
    elif os.path.exists("etf_investor_flow.csv"):
        return "etf_investor_flow.csv"
        
    return None

def load_previous_analysis(prev_filepath):
    """
    이전 분석 CSV 파일에서 종목코드별 투자등급 및 수급/이평선 지표를 읽어와 딕셔너리로 반환합니다.
    """
    if not prev_filepath or not os.path.exists(prev_filepath):
        return {}
    
    prev_map = {}
    try:
        with open(prev_filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get("종목코드", "").strip()
                if code:
                    prev_map[code] = {
                        "투자등급": row.get("투자등급", "").strip(),
                        "쌍끌이여부": row.get("쌍끌이여부", "").strip(),
                        "20일선위": row.get("20일선위", "").strip(),
                        "정배열여부": row.get("정배열여부", "").strip()
                    }
    except Exception as e:
        print(f"[경고] 이전 분석 파일('{prev_filepath}') 로딩 실패: {e}")
    return prev_map

def compare_grade_change(prev_info, curr_grade, dual_buying, above_ma20, is_aligned):
    """
    이전 등급과 현재 등급을 비교하여 등급변동(예: A -> A+) 및 변동이유를 반환합니다.
    """
    if not prev_info:
        return f"NEW ({curr_grade})", f"{curr_grade}등급 신규 포착"
    
    prev_grade = prev_info.get("투자등급", "")
    if not prev_grade:
        return f"NEW ({curr_grade})", f"{curr_grade}등급 신규 포착"
    
    if prev_grade == curr_grade:
        return "-", "등급 유지"
    
    change_str = f"{prev_grade} -> {curr_grade}"
    reasons = []
    
    prev_dual = prev_info.get("쌍끌이여부", "")
    prev_ma20 = prev_info.get("20일선위", "")
    prev_align = prev_info.get("정배열여부", "")

    # 상향 원인
    if is_aligned == "O" and prev_align != "O":
        reasons.append("정배열 달성(5>=20>=60>=120일)")
    if dual_buying == "O" and prev_dual != "O":
        reasons.append("외인/기관 쌍끌이 순매수 유입")
    if above_ma20 == "O" and prev_ma20 != "O":
        reasons.append("20일선 위 가격 회복")
    
    # 하향 원인
    if is_aligned != "O" and prev_align == "O":
        reasons.append("이평선 정배열 이탈")
    if dual_buying != "O" and prev_dual == "O":
        reasons.append("쌍끌이 수급 이탈")
    if above_ma20 != "O" and prev_ma20 == "O":
        reasons.append("20일선 아래 가격 이탈")
    
    reason_str = ", ".join(reasons) if reasons else "수급 및 차트 조건 변경"
    
    grade_order = {"A+": 4, "A": 3, "B": 2, "C": 1}
    prev_rank = grade_order.get(prev_grade, 0)
    curr_rank = grade_order.get(curr_grade, 0)
    
    if curr_rank > prev_rank:
        return f"{change_str} (상향)", reason_str
    else:
        return f"{change_str} (하향)", reason_str

import os
from datetime import datetime

def main():
    today_str = datetime.now().strftime("%Y%m%d")
    default_input = "data/etf_top_stocks.csv" if os.path.exists("data/etf_top_stocks.csv") else "etf_top_stocks.csv"
    default_save_dir = f"분석_{today_str}"
    default_save_csv = f"{default_save_dir}/분석_{today_str}.csv"
    
    auto_prev_csv = find_latest_previous_file(today_str)

    parser = argparse.ArgumentParser(description="ETF 주도주 외국인/기관 수급 및 이동평균선 분석 스크립트")
    parser.add_argument("--input-csv", type=str, default=default_input, help=f"입력 CSV 파일 경로 (기본값: {default_input})")
    parser.add_argument("--save-csv", type=str, default=default_save_csv, help=f"저장할 CSV 파일 경로 (기본값: {default_save_csv})")
    parser.add_argument("--prev-csv", type=str, default=auto_prev_csv, help="이전 등급 비교용 CSV 파일 경로")
    parser.add_argument("--limit", type=int, default=0, help="분석할 주도주 수 제한 (0일 경우 전체)")
    parser.add_argument("--delay", type=float, default=0.01, help="요청 간 대기 시간(초) (기본값: 0.01초)")
    args = parser.parse_args()

    try:
        with open(args.input_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            stock_list = list(reader)
    except Exception as e:
        print(f"[오류] '{args.input_csv}' 파일을 읽는 도중 에러가 발생했습니다: {e}")
        sys.exit(1)

    print(f"'{args.input_csv}' 파일에서 총 {len(stock_list)}개의 주도주 목록을 읽었습니다.")

    if args.prev_csv:
        print(f"이전 분석 데이터 비교 파일: '{args.prev_csv}'")
        prev_map = load_previous_analysis(args.prev_csv)
    else:
        print("이전 분석 비교 파일이 존재하지 않아 신규 비교 모드로 진행합니다.")
        prev_map = {}

    if args.limit > 0:
        stock_list = stock_list[:args.limit]
        print(f"주도주 분석 제한 적용: {len(stock_list)}개 종목만 처리합니다.")

    analyzed_rows = []
    total_stocks = len(stock_list)
    start_time = time.time()

    print("\n외국인/기관 수급 및 5/20/60/120일 이동평균선 분석을 시작합니다...")

    for idx, item in enumerate(stock_list, 1):
        code = item.get("종목코드", "").strip()
        name = item.get("종목명", "").strip()
        detail_url = item.get("상세페이지", "").strip()

        if not code:
            continue

        trend_data = fetch_investor_trend(code, page_size=5)
        flow = analyze_investor_flow(trend_data)
        ma_info = fetch_moving_averages(code)

        grade = determine_investment_grade(
            flow["쌍끌이여부"],
            ma_info["20일선위"],
            ma_info["정배열여부"]
        )

        prev_info = prev_map.get(code)
        grade_change, change_reason = compare_grade_change(
            prev_info,
            grade,
            flow["쌍끌이여부"],
            ma_info["20일선위"],
            ma_info["정배열여부"]
        )

        analyzed_rows.append({
            "종목코드": code,
            "종목명": name,
            "투자등급": grade,
            "등급변동": grade_change,
            "변동이유": change_reason,
            "현재가": flow["현재가"],
            "외국인보유율": flow["외국인보유율"],
            "쌍끌이여부": flow["쌍끌이여부"],
            "외국인연속매수(일)": flow["외국인연속매수"],
            "기관연속매수(일)": flow["기관연속매수"],
            "최근3일외인순매수": f"{flow['최근3일외인순매수']:,}",
            "최근3일기관순매수": f"{flow['최근3일기관순매수']:,}",
            "20일선위": ma_info["20일선위"],
            "정배열여부": ma_info["정배열여부"],
            "MA5": f"{ma_info['MA5']:,}" if ma_info['MA5'] else "0",
            "MA20": f"{ma_info['MA20']:,}" if ma_info['MA20'] else "0",
            "MA60": f"{ma_info['MA60']:,}" if ma_info['MA60'] else "0",
            "MA120": f"{ma_info['MA120']:,}" if ma_info['MA120'] else "0",
            "상세페이지": detail_url
        })

        if idx % 50 == 0 or idx == total_stocks:
            elapsed = time.time() - start_time
            print(f"[{idx}/{total_stocks}] 데이터 수집 진행 중... ({name} -> 등급: {grade}, 변동: {grade_change})")

        time.sleep(args.delay)

    # 우선순위 정렬: 등급(A+ -> A -> B -> C) -> 연속 매수합
    grade_order = {"A+": 4, "A": 3, "B": 2, "C": 1}
    analyzed_rows.sort(
        key=lambda x: (
            grade_order.get(x["투자등급"], 0),
            x["외국인연속매수(일)"] + x["기관연속매수(일)"]
        ),
        reverse=True
    )

    print("\n" + "=" * 135)
    print(f"{'종목코드':<8} | {'종목명':<16} | {'등급':<4} | {'등급변동':<16} | {'변동이유':<30} | {'현재가':<10} | {'쌍끌이':<4} | {'20일선위':<6}")
    print("-" * 135)
    
    for r in analyzed_rows[:30]:
        print(f"{r['종목코드']:<8} | {r['종목명']:<16} | {r['투자등급']:<4} | {r['등급변동']:<16} | {r['변동이유']:<30} | {r['현재가']:<10} | {r['쌍끌이여부']:<4} | {r['20일선위']:<6}")
    print("=" * 115)

    a_plus_count = sum(1 for r in analyzed_rows if r['투자등급'] == 'A+')
    a_count = sum(1 for r in analyzed_rows if r['투자등급'] == 'A')
    upgraded_count = sum(1 for r in analyzed_rows if "(상향)" in r['등급변동'])
    downgraded_count = sum(1 for r in analyzed_rows if "(하향)" in r['등급변동'])
    
    print(f"\n[분석 완료] 총 {total_stocks}개 종목 중 A+등급: {a_plus_count}개 / A등급: {a_count}개 (상향 종목: {upgraded_count}개 / 하향 종목: {downgraded_count}개)")

    # CSV 저장 (날짜별 폴더 및 동시 저장 처리)
    fieldnames = [
        "종목코드", "종목명", "투자등급", "등급변동", "변동이유", "현재가", "외국인보유율", "쌍끌이여부",
        "외국인연속매수(일)", "기관연속매수(일)", "최근3일외인순매수", "최근3일기관순매수",
        "20일선위", "정배열여부", "MA5", "MA20", "MA60", "MA120", "상세페이지"
    ]

    target_files = [args.save_csv, "etf_investor_flow.csv", "data/etf_investor_flow.csv"]
    for target in target_files:
        if not target:
            continue
        save_dir = os.path.dirname(target)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        with open(target, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(analyzed_rows)
        print(f"[성공] 수급 분석 결과 저장이 완료되었습니다: {target}")

if __name__ == "__main__":
    main()
