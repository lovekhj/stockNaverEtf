#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 매수신호 판정 규칙 (buySignal.py)
================================================================================
1. 프로그램 역할:
   "강한 마감 + 정배열인 날 종가에 산다"는 후보 규칙을 한 곳에 정의합니다.
   4단계 등급 산출(getEtfInvestorFlow.py)과 백테스트(backtestTrendRules.py)가
   같은 정의를 쓰도록 이 파일만 고치면 양쪽에 반영됩니다.

2. 매수신호:
   - A(매수)     : 강한 마감 + 정배열
   - B(재검토)   : 강한 마감과 정배열 중 하나만 충족
   - C(매수금지) : 둘 다 아님

3. 조건:
   - 강한 마감: 당일 등락률 +3% 이상, 거래량이 직전 20거래일 평균의 1.5배 이상
   - 정배열   : 종가 > 5일선 > 20일선 > 60일선, 20일선 > 5거래일 전 20일선
   - 종가 위치(고가 근처 마감)와 거래대금 하한은 2026-10-10에 조건에서 뺐습니다.

4. 주의:
   - 검증 중인 후보 규칙입니다 (`docs/종목선정_검증.md` 11, 12번). 확정된 규칙이 아닙니다.
   - 신호는 그날 종가 매수를 뜻합니다. 장 마감 후에 본 신호를 다음 날 사면 다른 매매입니다.
   - 과거 데이터 분석에 따른 분류이며 매수·매도 추천이 아닙니다.
================================================================================
"""

STRONG_CHANGE = 0.03       # 강한 마감: 당일 등락률 하한
STRONG_VOLUME = 1.5        # 강한 마감: 직전 20일 평균 거래량 대비 배수 하한
MIN_BARS = 66              # 판정에 필요한 최소 거래일 수 (60일선 + 5거래일 전 20일선)

SIGNAL_BUY = "A(매수)"
SIGNAL_REVIEW = "B(재검토)"
SIGNAL_AVOID = "C(매수금지)"
SIGNAL_NONE = "-"

def is_strong_close(change, volume_ratio):
    """
    강한 마감 여부를 돌려줍니다.

    :param change: 당일 등락률 (0.03 = +3%)
    :param volume_ratio: 당일 거래량 / 직전 20거래일 평균 거래량
    """
    return change >= STRONG_CHANGE and volume_ratio >= STRONG_VOLUME

def is_aligned(close, ma5, ma20, ma60, ma20_prev5):
    """
    정배열(종가 > 5일선 > 20일선 > 60일선, 20일선 상승) 여부를 돌려줍니다.
    """
    return close > ma5 > ma20 > ma60 and ma20 > ma20_prev5

def grade_signal(strong, aligned):
    """
    조건 충족 여부로 매수신호 A/B/C를 매깁니다.
    """
    if strong and aligned:
        return SIGNAL_BUY
    if strong or aligned:
        return SIGNAL_REVIEW
    return SIGNAL_AVOID

def judge_bars(closes, volumes):
    """
    일봉 리스트(오래된 날 → 최근 날)의 마지막 날에 대한 매수신호와 사유를 돌려줍니다.

    :return: (매수신호, 사유). 데이터가 모자라면 ("-", 이유)
    """
    n = len(closes)
    if n < MIN_BARS:
        return SIGNAL_NONE, f"일봉 {n}일 (최소 {MIN_BARS}일 필요)"
    if volumes[-1] == 0:
        return SIGNAL_NONE, "거래 없음"

    def mean(values):
        return sum(values) / len(values)

    close = closes[-1]
    change = close / closes[-2] - 1
    prev_volume = mean(volumes[-21:-1])
    volume_ratio = volumes[-1] / prev_volume if prev_volume > 0 else 0.0

    strong = is_strong_close(change, volume_ratio)
    aligned = is_aligned(close, mean(closes[-5:]), mean(closes[-20:]), mean(closes[-60:]), mean(closes[-25:-5]))

    reason = (f"강한마감 {'O' if strong else 'X'} ({change * 100:+.1f}%, 거래량 {volume_ratio:.1f}배), "
              f"정배열 {'O' if aligned else 'X'}")
    return grade_signal(strong, aligned), reason
