#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 [검증용] 추세추종 매도 규칙 백테스트 프로그램 (backtestTrendRules.py)
================================================================================
1. 프로그램 역할:
   `stockdata/` 의 과거 일봉·수급으로 "매수 조건을 채운 날 종가에 사서 매도 규칙대로
   팔았다면" 매매 하나하나가 어땠는지 셉니다. 같은 매수 조건에 매도 규칙만 바꿔 비교합니다.
   매일 도는 1~5단계와는 별개이며 `main.py`에 연결되어 있지 않습니다.

2. 입력 데이터:
   - `stockdata/{종목코드}.csv` (getStockHistory.py 실행 결과)

3. 출력 결과:
   - 화면에 매수 조건 x 매도 규칙 표를 출력합니다. 파일은 만들지 않습니다.

4. 매매 방법:
   - 매수: 보유 중이 아닌 종목이 조건을 채운 날 종가에 삽니다. 수급은 전일까지 확정치만 씁니다.
   - 매도: 모두 종가로 판단하고 그날 종가에 전량 팝니다.
       · 10일 보유       : 10거래일 뒤 종가에 판다 (비교 기준)
       · 트레일링 -5%    : 종가 <= 보유 중 최고 종가 x 0.95
       · 확정 규칙 전체  : 트레일링 -5% / 종가 < 20일선 / 10거래일째 종가 <= 매수가, 먼저 오는 것
   - 판 다음 날부터 같은 종목을 다시 살 수 있습니다.
   - 종목별로 따로 셉니다. 계좌 하나로 몇 종목을 동시에 들 수 있는지는 따지지 않습니다.

5. 대상에서 빼는 것:
   - 상장 후 250거래일이 안 된 날의 매수 (`--min-value` 를 주면 거래대금 미달인 날도 뺀다)
   - 거래정지일(거래량 0)의 매수·매도. 매도 조건이 되어도 거래가 되는 날까지 미룹니다.
   - 보유 중에 하루 ±30% 초과 등락이 있는 매매, 데이터 끝까지 팔지 못한 매매

6. 읽을 때 주의:
   - 현재 유니버스만 쓰므로 생존 편향이 있습니다. 조건 간, 규칙 간 차이만 봅니다.
   - 종가에 정확히 체결된다고 가정합니다. 갭하락이면 손실이 -5%를 넘습니다.
   - 과거 데이터 분석이며 매수·매도 추천이 아닙니다.
================================================================================
"""

import argparse        # CLI 실행 옵션 파서
import glob            # 폴더 내 종목 파일 검색 라이브러리
import os              # 파일 경로 처리 라이브러리
import sys             # 프로그램 시스템 제어 라이브러리
from statistics import median  # 중앙값 계산 도구

from checkSignalReturns import load_rows, rolling_mean, MIN_HISTORY, PRICE_LIMIT
from buySignal import is_strong_close, is_aligned

TRAIL_STOP = 0.05      # 트레일링 스톱: 보유 중 최고 종가 대비 하락폭
HOLD_DAYS = 10         # 10일 보유, 기간 청산에 쓰는 거래일 수
EXIT_RULES = ("10일 보유", "트레일링 -5%", "확정 규칙 전체")
# 표에 출력하는 매수 조건 순서 (entry_signals 의 이름과 같아야 한다)
ENTRY_NAMES = (
    "조건 없음",
    "종가 > 5 > 20 > 60, 20일선 상승",
    "강한 마감",
    "강한 마감 + 정배열 (후보 규칙)",
    "A안 + ③ 52주 고점 -15% 이내",
    "확정 매수 조건 (수급 3일 연속)",
)

def load_stock(path):
    """
    종목 CSV를 읽어 매매 판단에 쓰는 값들을 묶어 돌려줍니다.
    """
    dates, c, vol, fo, og = load_rows(path)
    n = len(c)
    stock = {
        "dates": dates, "c": c, "vol": vol, "vol20": rolling_mean(vol, 20),
        "ma5": rolling_mean(c, 5), "ma20": rolling_mean(c, 20), "ma60": rolling_mean(c, 60),
        "value20": rolling_mean([c[i] * vol[i] / 1e8 for i in range(n)], 20),
        "broken": [i > 0 and abs(c[i] / c[i - 1] - 1) > PRICE_LIMIT for i in range(n)],
    }
    # 쌍끌이 연속 일수 (수급이 빈 날은 None)
    streak = [None] * n
    run = 0
    for i in range(n):
        if fo[i] is None or og[i] is None:
            run = 0
            continue
        run = run + 1 if (fo[i] > 0 and og[i] > 0) else 0
        streak[i] = run
    stock["streak"] = streak
    return stock

def entry_signals(s, t):
    """
    T일에 각 매수 조건을 채웠는지 돌려줍니다.
    """
    c, ma5, ma20, ma60 = s["c"][t], s["ma5"][t], s["ma20"][t], s["ma60"][t]
    ma20_up = ma20 > s["ma20"][t - 5]
    prev_streak = s["streak"][t - 1]
    aligned = is_aligned(c, ma5, ma20, ma60, s["ma20"][t - 5])
    prev_volume = s["vol20"][t - 1]
    strong = is_strong_close(c / s["c"][t - 1] - 1, s["vol"][t] / prev_volume if prev_volume > 0 else 0.0)
    return {
        "조건 없음": True,
        "종가 > 5 > 20 > 60, 20일선 상승": aligned,
        "강한 마감": strong,
        "강한 마감 + 정배열 (후보 규칙)": strong and aligned,
        "A안 + ③ 52주 고점 -15% 이내": (c > ma20 > ma60 and ma60 > s["ma60"][t - 20]
                                    and c >= 0.85 * max(s["c"][t - MIN_HISTORY + 1:t + 1])),
        "확정 매수 조건 (수급 3일 연속)": c > ma20 and ma20_up and prev_streak is not None and prev_streak >= 3,
    }

def find_exit(s, t, rule):
    """
    T일 종가에 산 매매를 규칙대로 팔 날을 찾습니다.

    :return: 매도일 인덱스. 데이터 끝까지 못 팔았거나 보유 중 이상 등락이 있으면 None
    """
    c, vol = s["c"], s["vol"]
    entry, peak = c[t], c[t]
    pending = False  # 매도 조건이 됐지만 거래정지라 못 판 상태
    for u in range(t + 1, len(c)):
        if s["broken"][u]:
            return None
        peak = max(peak, c[u])
        held = u - t
        if rule == "10일 보유":
            hit = held >= HOLD_DAYS
        elif rule == "트레일링 -5%":
            hit = c[u] <= peak * (1 - TRAIL_STOP)
        else:
            hit = (c[u] <= peak * (1 - TRAIL_STOP) or c[u] < s["ma20"][u]
                   or (held == HOLD_DAYS and c[u] <= entry))
        pending = pending or hit
        if pending and vol[u] > 0:
            return u
    return None

def run_backtest(data_dir, min_value):
    """
    전 종목에 매수 조건 x 매도 규칙을 돌려 매매 목록을 만듭니다.

    :return: {(매수 조건, 매도 규칙): [(매수일, 수익률, 보유 거래일), ...]}
    """
    trades = {}
    for path in sorted(glob.glob(os.path.join(data_dir, "*.csv"))):
        if os.path.basename(path)[:-4] in ("KOSPI", "KOSDAQ"):
            continue
        s = load_stock(path)
        n = len(s["c"])
        if n < MIN_HISTORY + 2:
            continue
        free_from = {}  # (매수 조건, 매도 규칙)별로 다시 살 수 있는 첫 날
        for t in range(MIN_HISTORY - 1, n - 1):
            if s["value20"][t] < min_value or s["vol"][t] == 0 or s["broken"][t]:
                continue
            for name, ok in entry_signals(s, t).items():
                if not ok:
                    continue
                for rule in EXIT_RULES:
                    key = (name, rule)
                    if t < free_from.get(key, 0):
                        continue  # 아직 보유 중
                    u = find_exit(s, t, rule)
                    if u is None:
                        free_from[key] = n  # 못 판 매매 이후로는 더 세지 않는다
                        continue
                    free_from[key] = u + 1
                    trades.setdefault(key, []).append((s["dates"][t], s["c"][u] / s["c"][t] - 1, u - t))
    return trades

def summarize(recs, cost):
    """
    매매 목록의 건수, 승률, 평균, 손익비 등을 계산합니다. 수익률은 비용을 뺀 값입니다.
    """
    rets = [r - cost for _, r, _ in recs]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    days = sum(d for _, _, d in recs) / len(recs)
    mean = sum(rets) / len(rets)
    return {
        "n": len(rets), "win": len(wins) / len(rets), "mean": mean, "median": median(rets),
        "avg_win": avg_win, "avg_loss": avg_loss,
        "ratio": avg_win / abs(avg_loss) if avg_loss else 0.0,
        "days": days, "per_day": mean / days, "worst": min(rets),
    }

def main():
    """
    [검증용] 추세추종 매도 규칙 백테스트 메인 실행 함수입니다.
    """
    parser = argparse.ArgumentParser(description="[검증용] 추세추종 매도 규칙 백테스트 스크립트")
    parser.add_argument("--data-dir", type=str, default="stockdata", help="과거 데이터 폴더 (기본값: stockdata)")
    parser.add_argument("--min-value", type=float, default=0, help="20일 평균 거래대금 최소값(억 원) (기본값: 0, 조건 없음)")
    parser.add_argument("--cost", type=float, default=0.25, help="왕복 비용(%%) (기본값: 0.25)")
    args = parser.parse_args()

    if not glob.glob(os.path.join(args.data_dir, "*.csv")):
        print(f"❌ {args.data_dir}/ 에 데이터가 없습니다. 먼저 getStockHistory.py --all --index 를 실행하세요.")
        sys.exit(1)

    trades = run_backtest(args.data_dir, args.min_value)
    cost = args.cost / 100
    all_dates = [d for recs in trades.values() for d, _, _ in recs]
    print(f"📅 매수일 범위: {min(all_dates)} ~ {max(all_dates)}, 거래대금 하한 {args.min_value:g}억 원, 왕복 비용 {args.cost:g}% 차감")

    entry_names = [name for name in ENTRY_NAMES if (name, EXIT_RULES[0]) in trades]

    for name in entry_names:
        print(f"\n■ 매수: {name}")
        print(f"{'매도 규칙':<16}{'건수':>8}{'승률':>8}{'평균':>9}{'중앙값':>9}{'평균이익':>9}{'평균손실':>9}{'손익비':>7}{'보유일':>7}{'하루당':>9}{'최악':>9}")
        for rule in EXIT_RULES:
            m = summarize(trades[(name, rule)], cost)
            print(f"{rule:<16}{m['n']:>10,}{m['win'] * 100:>9.1f}%{m['mean'] * 100:>+10.2f}%{m['median'] * 100:>+10.2f}%"
                  f"{m['avg_win'] * 100:>+11.2f}%{m['avg_loss'] * 100:>+11.2f}%{m['ratio']:>9.2f}{m['days']:>9.1f}"
                  f"{m['per_day'] * 100:>+10.3f}%{m['worst'] * 100:>+10.1f}%")

    # 연도별로 같은 방향인지 (매수 연도 기준 평균 수익률)
    years = sorted({d[:4] for d in all_dates})
    print("\n■ 연도별 평균 수익률, 비용 후 (건수)")
    print(f"{'매수 / 매도':<44}" + "".join(f"{y:>17}" for y in years))
    for name in entry_names[1:]:
        for rule in EXIT_RULES[1:]:
            line = f"{name[:24] + ' / ' + rule:<44}"
            for y in years:
                sub = [r - cost for d, r, _ in trades[(name, rule)] if d[:4] == y]
                line += f"{sum(sub) / len(sub) * 100:>+8.2f}% ({len(sub):>5,})" if sub else f"{'-':>17}"
            print(line)

if __name__ == "__main__":
    main()
