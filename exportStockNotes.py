#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 옵시디언용 종목·테마 노트 만들기 (exportStockNotes.py)
================================================================================
1. 프로그램 역할:
   종목-테마 연결을 옵시디언에서 쓸 수 있는 마크다운 노트로 내보냅니다.
   종목마다 노트 하나, 테마마다 노트 하나를 만들고 서로 `[[링크]]`로 잇습니다.
   `stocks/` 폴더를 옵시디언 볼트로 복사해서 씁니다.
   매일 도는 1~5단계와는 별개이며 `main.py`에 연결되어 있지 않습니다.

2. 입력 데이터:
   - `data/stock_theme_matrix.csv` (종목-테마 연결, `getStockThemes.py` 가 만듦)
   - `data/etf_top_stocks.csv` (대상 종목, 섹터, 네이버 링크)
   - `data/stock_sectors.csv` (시장)
   - `stockdata/theme_descriptions.csv`, `stockdata/theme_stock_reasons.csv`
     (네이버의 테마 설명과 편입 사유. 없으면 빼고 만듭니다)

3. 출력 결과:
   - `stocks/종목/{종목명}.md`, `stocks/테마/{테마명}.md`
   - 💡 `stocks/` 는 `.gitignore` 대상입니다. 네이버가 쓴 글이 들어 있어 공개 저장소에 올리지 않습니다.

4. 주의:
   - 실행할 때마다 `stocks/종목/`, `stocks/테마/` 를 비우고 새로 만듭니다. 이 두 폴더 안에
     직접 적은 내용은 사라집니다. 직접 쓰는 메모는 다른 폴더에 두고 링크만 겁니다.
   - 대상 종목이 WIDE_THEME_STOCKS 개 이상인 넓은 테마(밸류업, 지주사 등)는 노트를 만들지 않고
     종목 노트에 글자로만 적습니다. 링크로 걸면 그래프가 한 덩어리로 뭉칩니다.
   - 테마 이름의 `/` 는 파일 이름에 쓸 수 없어 `·` 로 바꾸고, 원래 이름은 별칭(aliases)으로 넣습니다.
   - 출처는 네이버 증권 테마이며, 구성은 `getStockThemes.py` 를 마지막으로 돌린 때 기준입니다.
================================================================================
"""

import csv             # CSV 파일 읽기 도구
import os              # 폴더 생성/삭제 라이브러리
import shutil          # 폴더 통째로 지우는 도구
import sys             # 프로그램 시스템 제어 라이브러리

MATRIX_FILE = "data/stock_theme_matrix.csv"
STOCK_FILE = "data/etf_top_stocks.csv"
SECTOR_FILE = "data/stock_sectors.csv"
DESCRIPTION_FILE = "stockdata/theme_descriptions.csv"
REASON_FILE = "stockdata/theme_stock_reasons.csv"
OUT_DIR = "stocks"
STOCK_DIR = os.path.join(OUT_DIR, "종목")
THEME_DIR = os.path.join(OUT_DIR, "테마")
WIDE_THEME_STOCKS = 30  # 대상 종목이 이 수 이상인 테마는 링크로 걸지 않는다


def read_csv(path, required=True):
    if not os.path.exists(path):
        if required:
            print(f"❌ {path} 파일이 없습니다.")
            sys.exit(1)
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def note_name(name):
    """옵시디언 파일 이름과 링크에 쓸 수 없는 `/` 를 `·` 로 바꿉니다."""
    return name.replace("/", "·")


def link(name):
    """노트 링크. 파일 이름이 원래 이름과 다르면 원래 이름으로 보이게 합니다."""
    file_name = note_name(name)
    return f"[[{file_name}]]" if file_name == name else f"[[{file_name}|{name}]]"


def yaml_text(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_note(folder, name, properties, body_lines):
    lines = ["---"]
    for key, value in properties:
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines += [f"  - {yaml_text(item)}" for item in value]
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {yaml_text(value)}")
    lines.append("---")
    with open(os.path.join(folder, note_name(name) + ".md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines + body_lines) + "\n")


def main():
    links = read_csv(MATRIX_FILE)
    stocks = read_csv(STOCK_FILE)
    markets = {row["종목코드"]: row.get("시장", "") for row in read_csv(SECTOR_FILE, required=False)}
    descriptions = {row["테마번호"]: row["설명"] for row in read_csv(DESCRIPTION_FILE, required=False)}
    reasons = {(row["테마번호"], row["종목코드"]): row["편입사유"] for row in read_csv(REASON_FILE, required=False)}
    if not descriptions:
        print(f"ℹ️  {DESCRIPTION_FILE} 이 없어 테마 설명과 편입 사유 없이 만듭니다. (`python3 getStockThemes.py` 로 받습니다)")

    by_stock, by_theme = {}, {}
    for row in links:
        by_stock.setdefault(row["종목코드"], []).append(row)
        by_theme.setdefault(row["테마번호"], []).append(row)

    def reason_text(row):
        # 우선주는 보통주의 편입 사유를 쓴다
        reason = reasons.get((row["테마번호"], row["물려받음"] or row["종목코드"]), "")
        return f" — {reason}" if reason else ""

    # 다시 만들 때 없어진 종목·테마의 노트가 남지 않도록 두 폴더를 비운다
    for folder in (STOCK_DIR, THEME_DIR):
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)

    for stock in stocks:
        code, name = stock["종목코드"], stock["종목명"]
        rows = by_stock.get(code, [])
        narrow = [row for row in rows if int(row["대상종목수"]) < WIDE_THEME_STOCKS]
        wide = [row for row in rows if int(row["대상종목수"]) >= WIDE_THEME_STOCKS]
        properties = [
            ("tags", ["종목"]),
            ("종목코드", code),
            ("시장", markets.get(code, "")),
            ("섹터", stock.get("섹터", "")),
            ("테마수", len(rows)),
        ]
        body = ["", f"[네이버 증권]({stock.get('상세페이지') or f'https://stock.naver.com/domestic/stock/{code}/price'})", ""]
        if rows and rows[0]["물려받음"]:
            body += [f"우선주라서 보통주({rows[0]['물려받음']})의 테마를 물려받았습니다.", ""]
        body.append("## 테마")
        if narrow:
            body += [f"- {link(row['테마명'])} ({row['대상종목수']}){reason_text(row)}" for row in narrow]
        else:
            body.append("- 없음")
        if wide:
            body += ["", "## 넓은 테마 (링크 없음)"]
            body += [f"- {row['테마명']} ({row['대상종목수']})" for row in wide]
        write_note(STOCK_DIR, name, properties, body)

    theme_count = 0
    for theme_no, rows in by_theme.items():
        if len(rows) >= WIDE_THEME_STOCKS:
            continue
        name = rows[0]["테마명"]
        properties = [("tags", ["테마"])]
        if note_name(name) != name:
            properties.append(("aliases", [name]))
        properties += [
            ("테마번호", int(theme_no)),
            ("대상종목수", len(rows)),
            ("네이버전체종목수", int(rows[0]["테마종목수"])),
        ]
        body = [""]
        if descriptions.get(theme_no):
            body += [descriptions[theme_no], ""]
        body.append("## 종목")
        body += [f"- {link(row['종목명'])}{reason_text(row)}" for row in rows]
        write_note(THEME_DIR, name, properties, body)
        theme_count += 1

    print(f"✅ {STOCK_DIR}/ 종목 노트 {len(stocks)}개")
    print(f"✅ {THEME_DIR}/ 테마 노트 {theme_count}개 (넓은 테마 {len(by_theme) - theme_count}개는 만들지 않음)")
    print("   이 두 폴더는 실행할 때마다 새로 만듭니다. 직접 쓰는 메모는 다른 폴더에 두세요.")


if __name__ == "__main__":
    main()
