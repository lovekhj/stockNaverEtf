#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 검증: 가상 거래의 매수 대상 기준 비교 (backtestEntryRules.py)
================================================================================
1. 프로그램 역할:
   "무엇을 살 것인가"의 후보 기준을 같은 매도 규칙으로 과거 일봉에 돌려 비교합니다.
   가상 주식거래 리포트(virtualTrade.py)가 따라갈 기준을 고르기 위한 검증입니다.

2. 비교하는 매수 기준 (그날 종가에 매수, 한 종목은 한 번에 한 건만 보유):
   - 조건 없음        : 비교 기준. 살 수 있는 날이면 언제나 산다
   - A 통과+강한마감   : 추세 통과 + 강한 마감
   - B 매수신호 A      : 강한 마감 + 정배열 (지금의 매수신호 A)
   - A∩B              : 추세 통과 + 강한 마감 + 정배열
   - C 주도주 신규편입 : 섹터 상위 4개 x 통과 종목 5개 목록에 새로 들어온 날 (지금의 가상 거래)

3. 매도 규칙 (가상 거래와 같다):
   - 장중 저가가 손절가(보유 중 최고 종가의 -5%) 이하로 내려간 날 판다
   - 체결 가격은 세 가지로 센다: 손절가(가상 거래의 가정), 갭 반영(시가가 손절가보다 낮으면 시가),
     종가(그날 종가가 손절가 이하일 때 종가에 파는 기존 후보 규칙)

4. 한계:
   - 대상 종목과 섹터 분류가 오늘 기준이다. 과거에 없던 정보로 고른 셈이라 실제보다 좋게 나온다.
     섹터를 쓰는 C가 이 영향을 가장 크게 받는다.
   - 코스피가 크게 오른 기간이다. 하락장은 들어 있지 않다.
   - 종가·손절가에 정확히 체결된다고 가정한다. 과거 분석이며 매수·매도 추천이 아니다.

5. 실행: python3 backtestEntryRules.py   (먼저 getStockHistory.py --all 로 stockdata/ 를 받아 둔다)
================================================================================
"""

import csv
import glob
import os
from statistics import median

from buySignal import is_strong_close, is_aligned, HIGH_BARS, HIGH_DROP_MAX, RETURN_BARS
from getEtfAiReport import LEADER_SECTORS, LEADER_STOCKS

DATA_DIR = "stockdata"
SECTOR_CSV = "data/stock_sectors.csv"
MIN_HISTORY = 250       # 상장 후 이만큼 지난 날부터 센다 (1년 최고 종가 계산)
PRICE_LIMIT = 0.31      # 하루 등락이 이보다 크면 수정주가 오류로 보고 그 매매는 버린다
STOP_DROP = 0.05        # 손절 폭: 보유 중 최고 종가 대비
COST = 0.0025           # 왕복 비용 가정

ENTRY_NAMES = ("조건 없음", "A 통과+강한마감", "B 매수신호 A", "A∩B", "C 주도주 신규편입")
FILL_NAMES = ("손절가", "갭 반영", "종가")

def load_stock(path):
    """
    종목 CSV(날짜, 시가, 고가, 저가, 종가, 거래량)를 읽어 날짜별 판정값을 계산합니다.
    """
    with open(path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    dates = [r["날짜"] for r in rows]
    o = [float(r["시가"]) for r in rows]
    low = [float(r["저가"]) for r in rows]
    c = [float(r["종가"]) for r in rows]
    vol = [float(r["거래량"]) for r in rows]
    n = len(c)

    prefix = [0.0]
    for price in c:
        prefix.append(prefix[-1] + price)
    def ma(t, k):
        return (prefix[t + 1] - prefix[t + 1 - k]) / k

    passed, strong, aligned, ret60 = [False] * n, [False] * n, [False] * n, [0.0] * n
    for t in range(MIN_HISTORY - 1, n):
        if vol[t] <= 0 or c[t - 1] <= 0:
            continue
        ma60, ma20 = ma(t, 60), ma(t, 20)
        passed[t] = c[t] > ma60 > ma(t - 5, 60) and c[t] / max(c[t + 1 - HIGH_BARS:t + 1]) - 1 >= -HIGH_DROP_MAX
        prev_volume = sum(vol[t - 20:t]) / 20
        strong[t] = is_strong_close(c[t] / c[t - 1] - 1, vol[t] / prev_volume if prev_volume > 0 else 0.0)
        aligned[t] = is_aligned(c[t], ma(t, 5), ma20, ma60, ma(t - 5, 20))
        ret60[t] = c[t] / c[t - RETURN_BARS] - 1
    broken = [i > 0 and c[i - 1] > 0 and abs(c[i] / c[i - 1] - 1) > PRICE_LIMIT for i in range(n)]
    return {"dates": dates, "o": o, "low": low, "c": c, "vol": vol, "broken": broken,
            "passed": passed, "strong": strong, "aligned": aligned, "ret60": ret60,
            "index": {d: i for i, d in enumerate(dates)}}

def find_exit(s, t):
    """
    T일 종가에 산 매매의 매도일과 체결 가격을 찾습니다.

    :return: {체결 방식: (매도일 인덱스, 매도 가격)}. 데이터 끝까지 못 팔았거나 이상 등락이 있으면 그 방식은 빠진다
    """
    out = {}
    peak = s["c"][t]
    for u in range(t + 1, len(s["c"])):
        if s["broken"][u]:
            break
        if s["vol"][u] <= 0:
            continue  # 거래정지: 팔 수 없다
        stop = peak * (1 - STOP_DROP)
        if "손절가" not in out and s["low"][u] <= stop:
            out["손절가"] = (u, stop)
            out["갭 반영"] = (u, min(stop, s["o"][u]))
        if "종가" not in out and s["c"][u] <= stop:
            out["종가"] = (u, s["c"][u])
        if len(out) == len(FILL_NAMES):
            break
        peak = max(peak, s["c"][u])
    return out

def leader_entries(stocks, sectors):
    """
    날짜마다 주도주 목록(섹터 상위 4개 x 통과 종목 5개)을 만들고, 목록에 새로 들어온 (종목, 날짜)를 돌려줍니다.
    """
    by_date = {}
    for code, s in stocks.items():
        for t in range(MIN_HISTORY - 1, len(s["c"])):
            if s["vol"][t] > 0:
                by_date.setdefault(s["dates"][t], []).append((code, s["passed"][t], s["ret60"][t]))

    entries, prev_list = set(), set()
    for date in sorted(by_date):
        stats = {}
        for code, passed, ret in by_date[date]:
            sec = stats.setdefault(sectors[code], {"total": 0, "passed": []})
            sec["total"] += 1
            if passed:
                sec["passed"].append((ret, code))
        ranking = sorted((name for name, sec in stats.items() if sec["passed"]),
                         key=lambda name: (-len(stats[name]["passed"]), -len(stats[name]["passed"]) / stats[name]["total"], name))
        today = {code for name in ranking[:LEADER_SECTORS] for _, code in sorted(stats[name]["passed"], reverse=True)[:LEADER_STOCKS]}
        entries.update((code, date) for code in today - prev_list)
        prev_list = today
    return entries

def run_backtest():
    """
    :return: {(매수 기준, 체결 방식): [(매수일, 수익률, 보유 거래일), ...]}
    """
    with open(SECTOR_CSV, "r", encoding="utf-8-sig") as f:
        sectors = {r["종목코드"]: r["섹터"] for r in csv.DictReader(f)}
    stocks = {}
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.csv"))):
        code = os.path.basename(path)[:-4]
        if code in sectors:
            stocks[code] = load_stock(path)
    leaders = leader_entries(stocks, sectors)

    trades = {}
    for code, s in stocks.items():
        n = len(s["c"])
        free_from = {}  # (매수 기준, 체결 방식)별로 다시 살 수 있는 첫 날
        for t in range(MIN_HISTORY - 1, n - 1):
            if s["vol"][t] <= 0 or s["broken"][t]:
                continue
            signals = {
                "조건 없음": True,
                "A 통과+강한마감": s["passed"][t] and s["strong"][t],
                "B 매수신호 A": s["strong"][t] and s["aligned"][t],
                "A∩B": s["passed"][t] and s["strong"][t] and s["aligned"][t],
                "C 주도주 신규편입": (code, s["dates"][t]) in leaders,
            }
            exits = None
            for name, ok in signals.items():
                if not ok:
                    continue
                exits = exits if exits is not None else find_exit(s, t)
                for fill in FILL_NAMES:
                    key = (name, fill)
                    if t < free_from.get(key, 0):
                        continue  # 아직 보유 중
                    if fill not in exits:
                        free_from[key] = n  # 못 판 매매 이후로는 더 세지 않는다
                        continue
                    u, price = exits[fill]
                    free_from[key] = u + 1
                    trades.setdefault(key, []).append((s["dates"][t], price / s["c"][t] - 1 - COST, u - t))
    return trades

def summarize(recs):
    returns = [r[1] for r in recs]
    wins = [x for x in returns if x > 0]
    losses = [x for x in returns if x <= 0]
    days = {}
    for date, ret, _ in recs:
        days.setdefault(date, []).append(ret)
    daily_means = [sum(v) / len(v) for v in days.values()]
    return {
        "건수": len(recs), "하루": len(recs) / len(days), "승률": len(wins) / len(recs),
        "평균": sum(returns) / len(returns), "중앙값": median(returns),
        "손익비": (sum(wins) / len(wins)) / (-sum(losses) / len(losses)) if wins and losses else float("nan"),
        "보유일": sum(r[2] for r in recs) / len(recs),
        "날짜평균": sum(daily_means) / len(daily_means), "신호일": len(days),
    }

def main():
    trades = run_backtest()
    all_dates = sorted({r[0] for recs in trades.values() for r in recs})
    print(f"\n매수일 {all_dates[0]} ~ {all_dates[-1]} | 네이버 증권 일봉(수정주가), 장 마감 후 확정치 | 왕복 비용 {COST * 100:.2f}% 차감")
    print("매도: 장중 저가가 손절가(보유 중 최고 종가 -5%) 이하인 날. 아직 팔리지 않은 매매는 세지 않음\n")

    for fill in FILL_NAMES:
        print(f"=== 체결: {fill} ===")
        print(f"{'매수 기준':<16} {'건수':>7} {'신호 있는 날':>8} {'날당':>6} {'승률':>7} {'매매당 평균':>9} {'중앙값':>8} {'손익비':>6} {'보유일':>6} {'날짜 기준 평균':>10}")
        for name in ENTRY_NAMES:
            st = summarize(trades[(name, fill)])
            print(f"{name:<16} {st['건수']:>8,} {st['신호일']:>10,} {st['하루']:>7.1f} {st['승률'] * 100:>7.1f}% {st['평균'] * 100:>+10.2f}% {st['중앙값'] * 100:>+9.2f}% {st['손익비']:>8.2f} {st['보유일']:>7.1f} {st['날짜평균'] * 100:>+12.2f}%")
        print()

    years = sorted({d[:4] for d in all_dates})
    print("=== 연도별 매매당 평균 (체결: 갭 반영) ===")
    print(f"{'매수 기준':<16} " + " ".join(f"{y:>16}" for y in years))
    for name in ENTRY_NAMES:
        cells = []
        for y in years:
            recs = [r for r in trades[(name, "갭 반영")] if r[0].startswith(y)]
            cells.append(f"{sum(r[1] for r in recs) / len(recs) * 100:>+7.2f}% ({len(recs):>5,})" if recs else f"{'-':>16}")
        print(f"{name:<16} " + " ".join(cells))

if __name__ == "__main__":
    main()
