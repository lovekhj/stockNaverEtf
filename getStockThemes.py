#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 종목-테마 연결 수집 프로그램 (getStockThemes.py)
================================================================================
1. 프로그램 역할:
   네이버 증권의 테마 목록과 테마별 종목을 받아, 우리 대상 종목이 어느 테마에
   들어 있는지를 "연결 하나 = 한 줄"로 적습니다. 대시보드의 "종목-테마" 화면이
   이 파일을 읽습니다. 매일 도는 1~5단계와는 별개이며 `main.py`에 연결되어
   있지 않습니다. 테마 구성은 자주 바뀌지 않으므로 가끔(주 1회 정도) 돌립니다.

2. 입력 데이터:
   - `data/etf_top_stocks.csv` (대상 종목)

3. 출력 결과:
   - `data/stock_theme_matrix.csv`
     열: 종목코드, 종목명, 테마번호, 테마명, 테마종목수, 대상종목수, 종목테마수, 물려받음
       · 테마종목수 = 네이버가 그 테마에 넣은 전체 종목 수
       · 대상종목수 = 그중 우리 대상 종목 수
       · 종목테마수 = 그 종목이 들어 있는 테마 수
       · 물려받음   = 우선주가 보통주의 테마를 물려받았으면 보통주 종목코드
   - `stockdata/theme_descriptions.csv` (테마 설명), `stockdata/theme_stock_reasons.csv`
     (종목별 편입 사유). 네이버가 쓴 글이라 공개 저장소에 올리지 않습니다.
     `stockdata/` 는 `.gitignore` 대상입니다.

4. 데이터 주의:
   - 출처는 네이버 증권 테마(m.stock.naver.com)이며 비공식 API라 구조가 바뀌면 멈출 수 있습니다.
   - 시세가 아니라 종목-테마 연결이므로 지연 여부와 관계없습니다.
   - 네이버 테마는 조금이라도 관련이 있으면 넣는 식이라 주력 사업과 곁가지를 구분하지
     않습니다. 테마종목수와 종목테마수가 클수록 연결이 약하다고 보면 됩니다.
   - 테마에 없는 종목은 이 파일에 나오지 않습니다.
================================================================================
"""

import urllib.request  # 웹 API 접속 라이브러리
import json            # JSON 데이터 해석 라이브러리
import csv             # CSV 파일 읽기/쓰기 도구
import sys             # 프로그램 시스템 제어 라이브러리
import time            # 연속 접속 시 대기시간(sleep) 도구
import os              # 디렉토리 생성 라이브러리

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
THEME_API = "https://m.stock.naver.com/api/stocks/theme"
PAGE_SIZE = 100
STOCK_FILE = "data/etf_top_stocks.csv"
MATRIX_FILE = "data/stock_theme_matrix.csv"
DESCRIPTION_FILE = "stockdata/theme_descriptions.csv"
REASON_FILE = "stockdata/theme_stock_reasons.csv"
MATRIX_HEADER = ["종목코드", "종목명", "테마번호", "테마명", "테마종목수", "대상종목수", "종목테마수", "물려받음"]


def fetch_json(url, retries=3):
    """
    URL을 호출해 JSON을 돌려줍니다. 실패하면 잠시 쉬고 다시 시도하며,
    끝까지 실패하면 None을 돌려줍니다.
    """
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as res:
                return json.loads(res.read().decode("utf-8"))
        except Exception:
            time.sleep(1 + attempt)
    return None


def fetch_theme_list():
    """네이버 테마 전체 목록 [{no, name, totalCount}, ...] 을 돌려줍니다."""
    themes = []
    page = 1
    while True:
        data = fetch_json(f"{THEME_API}?page={page}&pageSize={PAGE_SIZE}")
        if data is None:
            return None
        themes += data.get("groups", [])
        if not data.get("groups") or len(themes) >= data.get("totalCount", 0):
            return themes
        page += 1


def fetch_theme_detail(theme_no):
    """테마 하나의 (종목 목록, 테마 설명, 종목별 편입 사유) 를 돌려줍니다."""
    stocks, description, reasons = [], "", {}
    page = 1
    while True:
        data = fetch_json(f"{THEME_API}/{theme_no}?page={page}&pageSize={PAGE_SIZE}")
        if data is None:
            return None
        stocks += data.get("stocks", [])
        description = data.get("themeDescription") or description
        reasons.update(data.get("themeItemInfoMap") or {})
        if not data.get("stocks") or len(stocks) >= data.get("totalCount", 0):
            return stocks, description, reasons
        page += 1


def read_target_stocks():
    with open(STOCK_FILE, encoding="utf-8-sig", newline="") as f:
        return {row["종목코드"]: row["종목명"] for row in csv.DictReader(f)}


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    targets = read_target_stocks()
    print(f"📋 대상 종목 {len(targets)}개")

    themes = fetch_theme_list()
    if not themes:
        print("❌ 테마 목록을 받지 못했습니다. 기존 파일은 그대로 둡니다.")
        sys.exit(1)
    print(f"🏷️  네이버 테마 {len(themes)}개 수집 시작")

    theme_info = {}      # 테마번호 -> (테마명, 테마종목수)
    stock_themes = {}    # 종목코드 -> [테마번호, ...]
    descriptions, reasons = [], []
    for idx, theme in enumerate(themes, 1):
        detail = fetch_theme_detail(theme["no"])
        if detail is None:
            # 일부만 받은 채로 쓰면 연결이 빠진 파일이 되므로 멈춘다
            print(f"❌ 테마 {theme['no']}({theme['name']})를 받지 못했습니다. 기존 파일은 그대로 둡니다.")
            sys.exit(1)
        stocks, description, reason_map = detail
        theme_info[theme["no"]] = (theme["name"], len(stocks))
        descriptions.append([theme["no"], theme["name"], description])
        for stock in stocks:
            stock_themes.setdefault(stock["itemCode"], []).append(theme["no"])
        for code, reason in reason_map.items():
            reasons.append([theme["no"], theme["name"], code, reason])
        if idx % 50 == 0:
            print(f"   ... {idx}/{len(themes)}")
        time.sleep(0.05)

    # 우선주는 네이버 테마에 거의 없으므로 보통주(끝자리 0)의 테마를 물려받는다
    inherited = {}
    for code in targets:
        common = code[:5] + "0"
        if code not in stock_themes and common != code and common in stock_themes:
            inherited[code] = common

    target_count = {}    # 테마번호 -> 우리 대상 종목 수
    for code in targets:
        for theme_no in stock_themes.get(inherited.get(code, code), []):
            target_count[theme_no] = target_count.get(theme_no, 0) + 1

    rows, missing = [], []
    for code, name in targets.items():
        theme_nos = stock_themes.get(inherited.get(code, code), [])
        if not theme_nos:
            missing.append(name)
        # 종목 수가 적은 테마(더 좁은 테마)부터 적는다
        for theme_no in sorted(theme_nos, key=lambda no: (theme_info[no][1], no)):
            theme_name, theme_size = theme_info[theme_no]
            rows.append([code, name, theme_no, theme_name, theme_size,
                         target_count[theme_no], len(theme_nos), inherited.get(code, "")])

    write_csv(MATRIX_FILE, MATRIX_HEADER, rows)
    write_csv(DESCRIPTION_FILE, ["테마번호", "테마명", "설명"], descriptions)
    write_csv(REASON_FILE, ["테마번호", "테마명", "종목코드", "편입사유"], reasons)

    print(f"✅ {MATRIX_FILE}: 연결 {len(rows)}줄, 종목 {len(targets) - len(missing)}개, 테마 {len(target_count)}개")
    print(f"   우선주가 보통주 테마를 물려받음: {len(inherited)}개")
    print(f"   테마 없는 종목 {len(missing)}개: {', '.join(missing) if missing else '-'}")
    print(f"✅ {DESCRIPTION_FILE}, {REASON_FILE} (공개하지 않음)")


if __name__ == "__main__":
    main()
