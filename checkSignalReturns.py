#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 [검증용] 신호 뒤 수익률 세기 프로그램 (checkSignalReturns.py)
================================================================================
1. 프로그램 역할:
   `stockdata/` 의 과거 일봉·수급으로 "조건을 채운 날 종가에 샀다면 N거래일 뒤
   종가는 어땠나"를 조건별로 셉니다. 매도 규칙은 넣지 않고 매수 조건만 봅니다.
   매일 도는 1~5단계와는 별개이며 `main.py`에 연결되어 있지 않습니다.

2. 입력 데이터:
   - `stockdata/{종목코드}.csv`, `stockdata/KOSPI.csv` (getStockHistory.py 실행 결과)

3. 출력 결과:
   - 화면에 조건별 표를 출력합니다. 파일은 만들지 않습니다.

4. 재는 방법:
   - 매수: 조건을 채운 날(T)의 종가. 수급은 전일(T-1)까지 확정치만 씁니다.
   - 수익률: T+N 종가 / T 종가 - 1 (N = 5, 10). 비용은 넣지 않습니다.
   - 초과수익률: 같은 날 "대상 종목 전체"의 평균 수익률을 뺀 값입니다.
     시장이 오른 덕인지 조건 덕인지 가르기 위한 값이며, 조건 비교는 이 값으로 합니다.
   - 현재 등급(A+/A/B/C)은 장 마감 후에 나오므로 다음 날(T+1) 종가 매수로 잽니다.

5. 대상에서 빼는 날:
   - 상장 후 250거래일이 안 된 날 (52주 최고가를 계산할 수 없음)
   - 20일 평균 거래대금이 기준 미만인 날, 거래량이 0인 날(거래정지)
   - 수급이 빈 날, 재는 구간 안에 하루 ±30% 초과 등락이나 거래정지가 있는 날

6. 읽을 때 주의:
   - 현재 유니버스만 쓰므로 생존 편향이 있습니다. 절대 수익률이 아니라 조건 간 차이만 봅니다.
   - 하루씩 겹치는 구간을 세므로 건수만큼 독립된 매매가 아닙니다.
   - 과거 데이터 분석이며 매수·매도 추천이 아닙니다.
================================================================================
"""

import csv             # CSV 파일 읽기 도구
import argparse        # CLI 실행 옵션 파서
import glob            # 폴더 내 종목 파일 검색 라이브러리
import os              # 파일 경로 처리 라이브러리
import sys             # 프로그램 시스템 제어 라이브러리
from statistics import median  # 중앙값 계산 도구

HORIZONS = (5, 10)      # 수익률을 재는 기간 (거래일)
MIN_HISTORY = 250       # 조건 계산에 필요한 최소 거래일 수 (52주 최고가)
PRICE_LIMIT = 0.305     # 하루 등락이 이보다 크면 수정주가 오류·거래재개로 보고 뺀다

def load_rows(path):
    """
    종목(또는 지수) CSV를 읽어 열별 리스트로 돌려줍니다. 수급이 빈 칸이면 None 입니다.
    """
    dates, closes, volumes, foreigns, organs = [], [], [], [], []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dates.append(row["날짜"])
            closes.append(float(row["종가"]))
            volumes.append(float(row["거래량"]))
            foreigns.append(int(row["외국인순매수"]) if row["외국인순매수"] != "" else None)
            organs.append(int(row["기관순매수"]) if row["기관순매수"] != "" else None)
    return dates, closes, volumes, foreigns, organs

def rolling_mean(values, window):
    """
    이동평균을 계산합니다. 앞쪽에 값이 모자란 구간은 None 입니다.
    """
    out = [None] * len(values)
    total = 0.0
    for i, v in enumerate(values):
        total += v
        if i >= window:
            total -= values[i - window]
        if i >= window - 1:
            out[i] = total / window
    return out

def load_market_filter(save_dir):
    """
    날짜별로 "코스피 종가 > 60일선" 여부를 돌려줍니다.
    """
    dates, closes, _, _, _ = load_rows(os.path.join(save_dir, "KOSPI.csv"))
    ma60 = rolling_mean(closes, 60)
    return {d: (ma60[i] is not None and closes[i] > ma60[i]) for i, d in enumerate(dates)}

def build_records(save_dir, min_value):
    """
    전 종목을 훑어 대상이 되는 (종목, 날짜)마다 조건 값과 N일 뒤 수익률을 만듭니다.

    :return: 레코드(dict) 리스트
    """
    market_up = load_market_filter(save_dir)
    max_h = max(HORIZONS)
    records = []

    for path in sorted(glob.glob(os.path.join(save_dir, "*.csv"))):
        code = os.path.basename(path)[:-4]
        if code in ("KOSPI", "KOSDAQ"):
            continue
        dates, c, vol, fo, og = load_rows(path)
        n = len(c)
        if n < MIN_HISTORY + max_h + 2:
            continue

        ma5, ma20, ma60, ma120 = (rolling_mean(c, w) for w in (5, 20, 60, 120))
        # 거래대금(억 원) = 수정주가 종가 x 수정 전 거래량 (분할 이전 구간은 실제보다 작게 나온다)
        value20 = rolling_mean([c[i] * vol[i] / 1e8 for i in range(n)], 20)
        # 하루 등락이 가격제한폭을 넘거나 거래가 없던 날
        broken = [vol[i] == 0 or (i > 0 and abs(c[i] / c[i - 1] - 1) > PRICE_LIMIT) for i in range(n)]

        # 쌍끌이 연속 일수: 그날까지 외국인·기관이 모두 순매수한 날이 며칠 이어졌나 (빈 칸은 None)
        streak = [None] * n
        run = 0
        for i in range(n):
            if fo[i] is None or og[i] is None:
                run = 0
                continue
            run = run + 1 if (fo[i] > 0 and og[i] > 0) else 0
            streak[i] = run

        for t in range(MIN_HISTORY - 1, n - max_h - 1):
            if value20[t] < min_value or vol[t] == 0 or streak[t] is None or streak[t - 1] is None:
                continue
            # T+1 매수(등급용)까지 재므로 T+1 ~ T+max_h+1 구간이 깨끗해야 한다
            if any(broken[t + 1:t + max_h + 2]):
                continue
            rec = {
                "date": dates[t],
                "year": dates[t][:4],
                "market_up": market_up.get(dates[t], False),
                "above_ma20": c[t] > ma20[t],
                "ma20_up": ma20[t] > ma20[t - 5],
                "above_ma5": c[t] > ma5[t],
                "ma5_over_ma20": ma5[t] > ma20[t],
                "ma20_over_ma60": ma20[t] > ma60[t],
                "ret60": c[t] / c[t - 60] - 1,
                "trend_a": c[t] > ma20[t] > ma60[t] and ma60[t] > ma60[t - 20],
                "ma60_slope": ma60[t] / ma60[t - 20] - 1,
                "ma_gap": ma20[t] / ma60[t] - 1,
                "from_high": c[t] / max(c[t - MIN_HISTORY + 1:t + 1]) - 1,
                "disparity": c[t] / ma20[t],
                "streak_prev": streak[t - 1],   # 전일까지 (확정 규칙: 종가 매수 시점에 아는 수급)
                # 현재 등급 기준 (getEtfInvestorFlow.py 와 같은 식, 당일 수급 포함)
                "grade_bi": fo[t] > 0 and og[t] > 0,
                "grade_above": c[t] >= ma20[t],
                "grade_aligned": ma5[t] >= ma20[t] >= ma60[t] >= ma120[t],
            }
            for h in HORIZONS:
                rec[f"r{h}"] = c[t + h] / c[t] - 1
                rec[f"g{h}"] = c[t + 1 + h] / c[t + 1] - 1   # 등급용: 다음 날 종가 매수
            records.append(rec)
    return records

def add_excess_returns(records):
    """
    레코드마다 같은 날 대상 종목 전체의 평균 수익률을 뺀 초과수익률을 붙입니다.
    """
    keys = [f"{p}{h}" for p in ("r", "g") for h in HORIZONS]
    sums = {}
    for rec in records:
        day = sums.setdefault(rec["date"], [0] + [0.0] * len(keys))
        day[0] += 1
        for j, k in enumerate(keys):
            day[j + 1] += rec[k]
    for rec in records:
        day = sums[rec["date"]]
        for j, k in enumerate(keys):
            rec["x" + k] = rec[k] - day[j + 1] / day[0]

def grade_of(rec):
    """
    현재 운영 중인 등급 기준으로 A+/A/B/C 를 매깁니다.
    """
    if rec["grade_bi"] and rec["grade_above"] and rec["grade_aligned"]:
        return "A+"
    if rec["grade_bi"] and rec["grade_above"]:
        return "A"
    if rec["grade_bi"] or rec["grade_above"]:
        return "B"
    return "C"

def print_table(title, rows, prefix="r"):
    """
    조건별 건수와 수익률 표를 출력합니다. rows = [(조건 이름, 레코드 리스트), ...]
    """
    print(f"\n■ {title}")
    head = f"{'조건':<34}{'건수':>9}{'날수':>6}"
    for h in HORIZONS:
        head += f"{f'{h}일평균':>9}{f'{h}일초과':>9}{f'{h}일중앙':>9}{f'{h}일승률':>8}"
    print(head)
    for name, recs in rows:
        line = f"{name:<34}{len(recs):>10,}{len({r['date'] for r in recs}):>7,}"
        if not recs:
            print(line)
            continue
        for h in HORIZONS:
            vals = [r[f"{prefix}{h}"] for r in recs]
            excess = sum(r[f"x{prefix}{h}"] for r in recs) / len(recs)
            win = sum(1 for v in vals if v > 0) / len(vals)
            line += f"{sum(vals) / len(vals) * 100:>+11.2f}%{excess * 100:>+11.2f}%{median(vals) * 100:>+11.2f}%{win * 100:>9.1f}%"
        print(line)

def main():
    """
    [검증용] 신호 뒤 수익률 세기 메인 실행 함수입니다.
    """
    parser = argparse.ArgumentParser(description="[검증용] 신호 뒤 수익률 세기 스크립트")
    parser.add_argument("--data-dir", type=str, default="stockdata", help="과거 데이터 폴더 (기본값: stockdata)")
    parser.add_argument("--min-value", type=float, default=50, help="20일 평균 거래대금 최소값(억 원) (기본값: 50)")
    args = parser.parse_args()

    if not os.path.exists(os.path.join(args.data_dir, "KOSPI.csv")):
        print(f"❌ {args.data_dir}/KOSPI.csv 가 없습니다. 먼저 getStockHistory.py --all --index 를 실행하세요.")
        sys.exit(1)

    records = build_records(args.data_dir, args.min_value)
    add_excess_returns(records)
    days = sorted({r["date"] for r in records})
    print(f"📅 대상: {days[0]} ~ {days[-1]} ({len(days):,}거래일), 종목·날짜 {len(records):,}건, 거래대금 {args.min_value:g}억 원 이상")
    print("   평균·중앙·승률은 N거래일 뒤 종가 기준, 초과는 같은 날 대상 전체 평균을 뺀 값, 비용 제외")

    def pick(cond):
        return [r for r in records if cond(r)]

    # 추세 필터 (수급 조건 없이 추세만)
    trend = pick(lambda r: r["trend_a"])
    print_table("추세 필터 (수급 조건 없음)", [
        ("대상 전체", records),
        ("종가 > 20일선", pick(lambda r: r["above_ma20"])),
        ("A안", trend),
        ("A안 + ① 60일선 기울기 2%", [r for r in trend if r["ma60_slope"] >= 0.02]),
        ("A안 + ② 20-60일선 간격 2%", [r for r in trend if r["ma_gap"] >= 0.02]),
        ("A안 + ③ 52주 고점 -15% 이내", [r for r in trend if r["from_high"] >= -0.15]),
        ("A안 + ①②③", [r for r in trend if r["ma60_slope"] >= 0.02 and r["ma_gap"] >= 0.02 and r["from_high"] >= -0.15]),
    ])

    # 이평선 조합: 60일선을 조건에 넣을 때와 뺄 때
    short = pick(lambda r: r["above_ma5"] and r["ma5_over_ma20"] and r["ma20_up"])
    print_table("이평선 조합 (수급 조건 없음)", [
        ("종가 > 5 > 20, 20일선 상승", short),
        ("  그중 20일선 > 60일선", [r for r in short if r["ma20_over_ma60"]]),
        ("  그중 20일선 <= 60일선", [r for r in short if not r["ma20_over_ma60"]]),
        ("A안 (종가 > 20 > 60, 60 상승)", trend),
    ])
    print_table("이미 오른 정도: 최근 60거래일 수익률 (종가 > 5 > 20, 20일선 상승 안에서)", [
        ("0% 미만", [r for r in short if r["ret60"] < 0]),
        ("0~20%", [r for r in short if 0 <= r["ret60"] < 0.2]),
        ("20~50%", [r for r in short if 0.2 <= r["ret60"] < 0.5]),
        ("50% 이상", [r for r in short if r["ret60"] >= 0.5]),
    ])

    # 수급 연속 일수 (확정 매수 조건 1·2번 위에서 비교)
    base = pick(lambda r: r["above_ma20"] and r["ma20_up"])
    print_table("수급: 전일까지 외국인 AND 기관 연속 순매수 (종가 > 20일선, 20일선 상승)", [
        ("수급 조건 없음", base),
        ("1일 이상", [r for r in base if r["streak_prev"] >= 1]),
        ("2일 이상", [r for r in base if r["streak_prev"] >= 2]),
        ("3일 이상 (확정 매수 조건)", [r for r in base if r["streak_prev"] >= 3]),
    ])

    # 20일선 이격 (확정 매수 조건 안에서 자리에 따라)
    rule = [r for r in base if r["streak_prev"] >= 3]
    print_table("20일선 이격 (확정 매수 조건 안에서)", [
        ("100~105%", [r for r in rule if r["disparity"] <= 1.05]),
        ("105~108%", [r for r in rule if 1.05 < r["disparity"] <= 1.08]),
        ("108~115%", [r for r in rule if 1.08 < r["disparity"] <= 1.15]),
        ("115% 초과", [r for r in rule if r["disparity"] > 1.15]),
    ])

    # 시장 필터
    rows = []
    for name, recs in (("대상 전체", records), ("A안", trend), ("확정 매수 조건", rule)):
        rows.append((f"{name} / 코스피 60일선 위", [r for r in recs if r["market_up"]]))
        rows.append((f"{name} / 코스피 60일선 아래", [r for r in recs if not r["market_up"]]))
    print_table("시장 필터: 코스피 종가 > 60일선", rows)

    # 현재 등급 (다음 날 종가 매수 기준)
    by_grade = {}
    for r in records:
        by_grade.setdefault(grade_of(r), []).append(r)
    print_table("현재 등급 (등급이 나온 다음 날 종가 매수)", [(g, by_grade.get(g, [])) for g in ("A+", "A", "B", "C")], prefix="g")

    # 연도별로 같은 방향인지 (10일 초과수익률)
    print(f"\n■ 연도별 {HORIZONS[-1]}일 초과수익률 (건수)")
    groups = [("A안", trend), ("A안+①②③", [r for r in trend if r["ma60_slope"] >= 0.02 and r["ma_gap"] >= 0.02 and r["from_high"] >= -0.15]),
              ("확정 매수 조건", rule), ("등급 A+", by_grade.get("A+", []))]
    years = sorted({r["year"] for r in records})
    print(f"{'조건':<18}" + "".join(f"{y:>18}" for y in years))
    for name, recs in groups:
        key = f"xg{HORIZONS[-1]}" if name.startswith("등급") else f"xr{HORIZONS[-1]}"
        line = f"{name:<18}"
        for y in years:
            sub = [r[key] for r in recs if r["year"] == y]
            line += f"{(sum(sub) / len(sub) * 100 if sub else 0):>+9.2f}% ({len(sub):>6,})" if sub else f"{'-':>18}"
        print(line)

if __name__ == "__main__":
    main()
