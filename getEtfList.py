import urllib.request
import json
import csv
import argparse
import sys

# 네이버 ETF 탭 카테고리 매핑
TAB_CATEGORY_MAP = {
    1: "국내 시장지수",
    2: "국내 업종/테마",
    3: "국내 파생",
    4: "해외 주식",
    5: "원자재",
    6: "채권",
    7: "기타"
}

def fetch_etf_list():
    """
    네이버 금융 ETF API를 통해 전체 ETF 목록 데이터를 수집합니다.
    """
    url = "https://finance.naver.com/api/sise/etfItemList.nhn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://finance.naver.com/sise/etf.naver"
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            content = response.read().decode("euc-kr", errors="ignore")
            data = json.loads(content)
            
            result_code = data.get("resultCode")
            if result_code != "success":
                print(f"[경고] API 응답 결과 코드: {result_code}")

            raw_items = data.get("result", {}).get("etfItemList", [])
            parsed_items = []

            for item in raw_items:
                code = item.get("itemcode", "")
                name = item.get("itemname", "")
                tab_code = item.get("etfTabCode", 0)
                
                # 카테고리 1(국내 시장지수), 2(국내 업종/테마) 만 수집
                if tab_code not in (1, 2):
                    continue

                category = TAB_CATEGORY_MAP.get(tab_code, "기타")
                
                # 상세 페이지 URL
                detail_url = f"https://stock.naver.com/domestic/stock/{code}/price"

                parsed_items.append({
                    "종목코드": code,
                    "종목명": name,
                    "카테고리코드": tab_code,
                    "카테고리명": category,
                    "상세페이지": detail_url
                })

            return parsed_items
    except Exception as e:
        print(f"[오류] ETF 데이터를 수집하는 중 에러가 발생했습니다: {e}")
        sys.exit(1)

import os

def main():
    parser = argparse.ArgumentParser(description="네이버 주식 ETF 목록 수집 스크립트")
    parser.add_argument("--save-csv", type=str, default="data/etf_list.csv", help="저장할 CSV 파일 경로 (기본값: data/etf_list.csv)")
    parser.add_argument("--save-json", type=str, default=None, help="저장할 JSON 파일 경로")
    parser.add_argument("--category", type=int, choices=[1, 2, 3, 4, 5, 6, 7], help="카테고리 코드 필터 (1: 국내지수, 2: 업종/테마, 3: 파생, 4: 해외주식, 5: 원자재, 6: 채권, 7: 기타)")
    parser.add_argument("--limit", type=int, default=0, help="출력할 종목 수 제한 (0일 경우 전체)")
    args = parser.parse_args()

    print("네이버 금융 ETF 전체 목록 수집을 시작합니다...")
    items = fetch_etf_list()
    print(f"총 {len(items)}개의 ETF 종목을 수집했습니다.")

    # 카테고리 필터링
    if args.category:
        items = [item for item in items if item["카테고리코드"] == args.category]
        category_name = TAB_CATEGORY_MAP.get(args.category, "")
        print(f"카테고리 필터링 적용: '{category_name}' (남은 종목 수: {len(items)}개)")

    display_items = items[:args.limit] if args.limit > 0 else items

    # 콘솔 상위 목록 출력
    print("\n" + "=" * 100)
    print(f"{'순번':<4} | {'종목코드':<8} | {'종목명':<25} | {'카테고리코드':<6} | {'카테고리명':<10} | {'상세페이지'}")
    print("-" * 100)
    
    preview_count = min(15, len(display_items))
    for idx, item in enumerate(display_items[:preview_count], 1):
        print(f"{idx:<4} | {item['종목코드']:<8} | {item['종목명']:<25} | {item['카테고리코드']:<6} | {item['카테고리명']:<10} | {item['상세페이지']}")
    
    if len(display_items) > preview_count:
        print(f"... 외 {len(display_items) - preview_count}개 종목 생략")
    print("=" * 100)

    # CSV 저장
    if args.save_csv:
        save_dir = os.path.dirname(args.save_csv)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            
        fieldnames = list(items[0].keys()) if items else []
        with open(args.save_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(items)
        print(f"\n[성공] CSV 파일이 저장되었습니다: {args.save_csv}")

    # JSON 저장
    if args.save_json:
        save_json_dir = os.path.dirname(args.save_json)
        if save_json_dir:
            os.makedirs(save_json_dir, exist_ok=True)
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"[성공] JSON 파일이 저장되었습니다: {args.save_json}")

if __name__ == "__main__":
    main()
