import urllib.request
import json
import csv
import re
import argparse
import sys
import time

def fetch_etf_portfolio(etf_code):
    """
    WiseReport Naver Company Info 페이지에서 특정 ETF의 포트폴리오(CU당 구성종목 및 비중)를 수집합니다.
    """
    url = f"https://navercomp.wisereport.co.kr/v2/company/c1080001.aspx?cmp_cd={etf_code}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://finance.naver.com/item/main.naver?code={etf_code}"
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode("utf-8", errors="ignore")
            
            # var CU_data = {...}; 추출
            m = re.search(r'var\s+CU_data\s*=\s*(\{.*?\});', html, re.DOTALL)
            if not m:
                return []

            data = json.loads(m.group(1))
            grid_data = data.get("grid_data", [])

            constituents = []
            for item in grid_data:
                stk_name = item.get("STK_NM_KOR", "").strip()
                if not stk_name:
                    continue
                
                weight = item.get("ETF_WEIGHT")
                cnt = item.get("AGMT_STK_CNT")

                # 비율 포맷팅
                if weight is not None:
                    ratio_str = f"{weight:.2f}%"
                elif cnt is not None:
                    ratio_str = f"{cnt:,.2f} (주)"
                else:
                    ratio_str = "-"

                constituents.append({
                    "구성종목명": stk_name,
                    "비율": ratio_str,
                    "raw_weight": weight if weight is not None else 0
                })

            return constituents
    except Exception as e:
        print(f"[경고] 종목코드 {etf_code} 포트폴리오 수집 실패: {e}")
        return []

import os

def main():
    default_input = "data/etf_list.csv" if os.path.exists("data/etf_list.csv") else "etf_list.csv"
    parser = argparse.ArgumentParser(description="주도주 분석을 위한 ETF 상위 구성종목 수집 스크립트")
    parser.add_argument("--input-csv", type=str, default=default_input, help=f"입력 CSV 파일 경로 (기본값: {default_input})")
    parser.add_argument("--save-csv", type=str, default="data/etf_dtl_list.csv", help="저장할 CSV 파일 경로 (기본값: data/etf_dtl_list.csv)")
    parser.add_argument("--save-json", type=str, default=None, help="저장할 JSON 파일 경로")
    parser.add_argument("--limit-etf", type=int, default=0, help="수집할 ETF 종목 수 제한 (0일 경우 전체)")
    parser.add_argument("--top-n", type=int, default=5, help="ETF당 상위 N개 구성종목만 수집 (기본값: 5위까지)")
    parser.add_argument("--delay", type=float, default=0.03, help="요청 간 대기 시간(초) (기본값: 0.03초)")
    args = parser.parse_args()

    # 입력 CSV 파일 읽기
    try:
        with open(args.input_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            etf_list = list(reader)
    except Exception as e:
        print(f"[오류] '{args.input_csv}' 파일을 읽는 도중 에러가 발생했습니다: {e}")
        sys.exit(1)

    print(f"'{args.input_csv}' 파일에서 총 {len(etf_list)}개의 ETF 목록을 읽었습니다.")

    if args.limit_etf > 0:
        etf_list = etf_list[:args.limit_etf]
        print(f"ETF 처리 제한 적용: {len(etf_list)}개 ETF만 처리합니다.")

    top_n_label = f"상위 1~{args.top_n}위" if args.top_n > 0 else "전체"
    print(f"ETF당 {top_n_label} 주요 구성종목(주도주 분석용) 수집을 시작합니다...")

    detailed_rows = []
    total_etfs = len(etf_list)
    start_time = time.time()

    for idx, etf in enumerate(etf_list, 1):
        code = etf.get("종목코드", "").strip()
        name = etf.get("종목명", "").strip()
        cat_code = etf.get("카테고리코드", "").strip()
        cat_name = etf.get("카테고리명", "").strip()
        detail_url = etf.get("상세페이지", "").strip()

        if not code:
            continue

        constituents = fetch_etf_portfolio(code)

        # 상위 N개(기본 1~5위) 필터링
        if args.top_n > 0:
            constituents = constituents[:args.top_n]

        # 비율순 순번 부여 (1~5위)
        for seq, item in enumerate(constituents, 1):
            detailed_rows.append({
                "종목코드": code,
                "종목명": name,
                "카테고리코드": cat_code,
                "카테고리명": cat_name,
                "상세페이지": detail_url,
                "순번": seq,
                "구성종목명": item["구성종목명"],
                "비율": item["비율"]
            })

        if idx % 100 == 0 or idx == total_etfs:
            elapsed = time.time() - start_time
            print(f"[{idx}/{total_etfs}] ETF 처리 중... (누적 상위 구성종목 행: {len(detailed_rows)}개, 소요시간: {elapsed:.1f}초)")

        time.sleep(args.delay)

    print(f"\n[수집 완료] 총 {total_etfs}개 ETF에서 {len(detailed_rows)}개의 주도주(상위 {top_n_label}) 데이터를 추출했습니다.")

    # CSV 저장
    if args.save_csv:
        fieldnames = ["종목코드", "종목명", "카테고리코드", "카테고리명", "상세페이지", "순번", "구성종목명", "비율"]
        with open(args.save_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(detailed_rows)
        print(f"[성공] CSV 파일이 저장되었습니다: {args.save_csv}")

    # JSON 저장
    if args.save_json:
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(detailed_rows, f, ensure_ascii=False, indent=2)
        print(f"[성공] JSON 파일이 저장되었습니다: {args.save_json}")

if __name__ == "__main__":
    main()
