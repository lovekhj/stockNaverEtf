#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 가상 주식거래 리포트 (virtualTrade.py)
================================================================================
1. 프로그램 역할:
   실제 돈을 쓰지 않고, 정해 둔 규칙대로 샀다고 치고 매일 결과를 적어 두는 모의 거래 장부입니다.

2. 규칙 (2026-10-10 사용자 결정. 근거는 `docs/종목선정_검증.md` 14번):
   - 매수: 매수신호 A(추세 통과 + 강한 마감)인 날, 그날 종가에 100만 원어치 매수
           (1주 단위로 100만 원에 가장 가까운 수량. 이미 들고 있는 종목은 다시 사지 않는다)
   - 보유: 오르면 팔지 않는다. 종가가 오르면 손절가도 따라 올라간다
   - 매도: 종가가 손절가(보유 중 최고 종가의 -5%) 이하인 날, 그날 종가에 전량 매도
   - 다시 사기: 판 다음 날부터, 다시 추세 통과 + 강한 마감이 나오면 산다

3. 입력 데이터:
   - `reports/report_YYYYMMDD.csv` (4단계 결과: 그날의 추세 통과·강한 마감과 종가)
   - 보유 종목의 그날 일봉 (네이버 증권 수정주가, 장 마감 후 확정치)

4. 출력 결과:
   - `reports/virtual_trades.csv` : 날짜별·종목별 한 줄씩 쌓이는 장부 (상태: 매수 / 보유 / 매도)

5. 주의:
   - 가상 거래입니다. 실제 보유 종목이나 계좌가 아니며 매수·매도 추천이 아닙니다.
   - 수수료·세금·슬리피지를 넣지 않았습니다. 종가에 정확히 사고 판다고 가정합니다.
   - 종가로 팔기 때문에 갭 하락한 날은 -5%보다 크게 잃습니다. 그대로 적습니다.
   - 날짜 순서대로 실행해야 합니다. 같은 날짜를 다시 실행하면 그날 기록만 새로 씁니다.
================================================================================
"""

import argparse
import csv
import glob
import os
import sys

from getEtfAiReport import read_report_rows
from getStockHistory import fetch_daily_prices

LEDGER_CSV = "reports/virtual_trades.csv"
BUY_AMOUNT = 1_000_000   # 한 종목을 사는 금액 (원). 1주 단위로 가장 가까운 수량을 산다
STOP_DROP = 0.05         # 손절 폭: 보유 중 최고 종가 대비

STATUS_BUY, STATUS_HOLD, STATUS_SELL = "매수", "보유", "매도"

FIELDNAMES = [
    "날짜", "종목코드", "종목명", "시장", "섹터", "상태", "수량", "매수일", "매수가",
    "최고종가", "손절가", "종가", "매도가", "평가금액", "손익", "수익률", "비고"
]

def to_int(text):
    """
    "52,900" 같은 가격 글자를 정수로 바꿉니다.
    """
    return int(round(float(str(text).replace(",", ""))))

def buy_quantity(price):
    """
    BUY_AMOUNT 에 가장 가까운 매수 수량을 돌려줍니다. (최소 1주)
    """
    return max(1, round(BUY_AMOUNT / price))

def is_buy_signal(report_row):
    """
    그날 살 종목인지 돌려줍니다. (매수신호 A = 추세 통과 + 강한 마감. 정의는 buySignal.py)
    """
    return report_row.get("매수신호", "").startswith("A")

def read_ledger():
    if not os.path.exists(LEDGER_CSV):
        return []
    with open(LEDGER_CSV, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def make_row(date, base, status, close, peak_close, note=""):
    """
    장부 한 줄을 만듭니다. base 에는 종목코드, 종목명, 시장, 섹터, 수량, 매수일, 매수가가 들어 있습니다.
    """
    quantity, buy_price = int(base["수량"]), int(base["매수가"])
    return {
        "날짜": date, "종목코드": base["종목코드"], "종목명": base["종목명"], "시장": base["시장"], "섹터": base["섹터"],
        "상태": status, "수량": quantity, "매수일": base["매수일"], "매수가": buy_price,
        "최고종가": peak_close, "손절가": round(peak_close * (1 - STOP_DROP)), "종가": close,
        "매도가": close if status == STATUS_SELL else "",
        "평가금액": 0 if status == STATUS_SELL else close * quantity,
        "손익": (close - buy_price) * quantity, "수익률": f"{(close / buy_price - 1) * 100:+.2f}%", "비고": note
    }

def run(date):
    """
    기준일 하루의 가상 거래를 장부에 적습니다.

    :return: 그날 적은 줄 리스트. 실행할 수 없으면 None
    """
    report_path = f"reports/report_{date}.csv"
    report_rows = read_report_rows(report_path) if os.path.exists(report_path) else []
    if not report_rows:
        print(f"⚠️ [가상 거래] '{report_path}' 가 없어 건너뜁니다.")
        return None
    if not any(r.get("매수신호", "")[:1] in ("A", "B", "C") for r in report_rows):
        print(f"⚠️ [가상 거래] {date} 리포트에 매수신호 열이 없어 건너뜁니다.")
        return None

    ledger = read_ledger()
    if any(r["날짜"] > date for r in ledger):
        print(f"⚠️ [가상 거래] 장부에 {date} 보다 뒤의 날짜가 있어 건너뜁니다. 날짜 순서대로 실행해야 합니다.")
        return None
    past = [r for r in ledger if r["날짜"] < date]
    prev_date = max((r["날짜"] for r in past), default=None)
    holdings = [r for r in past if r["날짜"] == prev_date and r["상태"] in (STATUS_BUY, STATUS_HOLD)]

    # 1. 보유 종목: 그날 종가가 손절가 이하면 종가에 판다
    today_rows = []
    for held in holdings:
        bars = fetch_daily_prices(held["종목코드"], date, date) or fetch_daily_prices(held["종목코드"], date, date)
        bar = bars[-1] if bars and bars[-1][0] == date and bars[-1][5] > 0 else None
        peak, stop = int(held["최고종가"]), int(held["손절가"])
        if bar is None:
            today_rows.append(make_row(date, held, STATUS_HOLD, int(held["종가"]), peak, note="거래 없음 (종가는 직전 값)"))
            continue
        close_p = round(bar[4])
        if close_p <= stop:
            today_rows.append(make_row(date, held, STATUS_SELL, close_p, peak, note=f"종가가 손절가 {stop:,}원 이하"))
        else:
            today_rows.append(make_row(date, held, STATUS_HOLD, close_p, max(peak, close_p)))

    # 2. 추세 통과 + 강한 마감인 종목을 종가에 산다 (들고 있거나 오늘 판 종목은 사지 않는다)
    held_codes = {r["종목코드"] for r in today_rows}
    for row in report_rows:
        if not is_buy_signal(row) or row["종목코드"] in held_codes:
            continue
        close_p = to_int(row["현재가"])
        base = {"종목코드": row["종목코드"], "종목명": row["종목명"], "시장": row.get("시장", "-"), "섹터": row.get("섹터", "-"),
                "수량": buy_quantity(close_p), "매수일": date, "매수가": close_p}
        note = f"매수신호 A (등락률 {row.get('등락률', '-')}, 3개월 {row.get('3개월수익률', '-')})"
        today_rows.append(make_row(date, base, STATUS_BUY, close_p, close_p, note=note))

    with open(LEDGER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(past + today_rows)

    count = lambda status: sum(1 for r in today_rows if r["상태"] == status)
    holding_rows = [r for r in today_rows if r["상태"] != STATUS_SELL]
    cost = sum(r["매수가"] * r["수량"] for r in holding_rows)
    value = sum(r["평가금액"] for r in holding_rows)
    realized = sum(int(r["손익"]) for r in past + today_rows if r["상태"] == STATUS_SELL)
    print(f"🧾 [가상 거래 {date}] 매수 {count(STATUS_BUY)}건 / 보유 {count(STATUS_HOLD)}건 / 매도 {count(STATUS_SELL)}건")
    print(f"   보유 원금 {cost:,}원 | 평가금액 {value:,}원 | 평가손익 {value - cost:+,}원 | 누적 실현손익 {realized:+,}원")
    print(f"💾 [저장 완료] {LEDGER_CSV} (가상 거래이며 매수·매도 추천이 아닙니다)")
    return today_rows

def main():
    parser = argparse.ArgumentParser(description="가상 주식거래 리포트: 추세 통과 + 강한 마감 종목을 종가에 샀다고 치고 매일 장부에 적습니다")
    parser.add_argument("--date", type=str, default=None, help="기준 거래일 (YYYYMMDD). 미지정 시 가장 최근 분석 CSV의 날짜")
    args = parser.parse_args()

    date = args.date
    if not date:
        files = sorted(glob.glob("reports/report_*.csv"))
        if not files:
            print("⚠️ [가상 거래] reports/ 폴더에 분석 CSV가 없습니다.")
            sys.exit(0)
        date = os.path.basename(files[-1]).replace("report_", "").replace(".csv", "")
    run(date.strip())

if __name__ == "__main__":
    main()
