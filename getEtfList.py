#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 [1단계] 네이버 주식 ETF 전체 목록 수집 프로그램 (getEtfList.py)
================================================================================
1. 프로그램 역할:
   네이버 증권 API를 호출하여 한국 주식 시장에 상장된 전체 ETF(상장지수펀드) 목록을
   자동으로 수집합니다. 주도주 분석에 필요한 '국내 시장지수' 및 '국내 업종/테마' ETF를
   추려내는 첫 번째 시작 스크립트입니다.

2. 입력 데이터:
   - 없음 (인터넷을 통해 네이버 증권 서버 API에서 실시간 수집)

3. 출력 결과:
   - CSV 파일: `data/etf_list.csv` (ETF 종목코드, 종목명, 카테고리코드, 카테고리명, 상세페이지 URL)

4. 주요 작동 흐름 (누구나 이해할 수 있는 단계별 설명):
   - 1단계 [접속]: 네이버 증권 ETF 목록 제공 서버(API)에 요청을 보냅니다.
   - 2단계 [수집]: 전체 ETF 데이터 중 '국내 지수' 및 '국내 업종/테마' 카테고리만 골라냅니다.
   - 3단계 [정리]: 각 ETF의 6자리 종목코드와 네이버 증권 상세페이지 웹주소를 만듭니다.
   - 4단계 [저장]: 수집한 결과를 `data/etf_list.csv` 파일로 저장합니다.
================================================================================
"""

import urllib.request  # 웹사이트 주소(URL)에 접속하여 데이터를 받아오는 표준 라이브러리
import json            # 서버에서 전달받은 JSON 데이터(키-값 형태)를 파이썬에서 읽을 수 있게 변환해주는 도구
import csv             # 엑셀과 호환되는 CSV 파일로 읽고 쓰기 위한 라이브러리
import argparse        # 터미널 명령어 창에서 --save-csv 같은 실행 옵션을 처리해주는 도구
import sys             # 프로그램 종료(sys.exit) 등 시스템 명령 처리를 위한 도구
import os              # 폴더(디렉토리) 생성 및 파일 경로 확인을 위한 라이브러리

# ==============================================================================
# 💡 네이버 증권 ETF 탭(카테고리) 번호 매핑표
# 1번과 2번(국내 시장지수, 국내 업종/테마)이 주도주 분석 대상입니다.
# ==============================================================================
TAB_CATEGORY_MAP = {
    1: "국내 시장지수",   # 예: KODEX 200, TIGER 코스닥150 등
    2: "국내 업종/테마",   # 예: KODEX 반도체, TIGER 2차전지테마 등
    3: "국내 파생",       # 예: 레버리지, 인버스 (주도주 분석 제외)
    4: "해외 주식",       # 예: TIGER 미국나스닥100 (국내 주도주 분석 제외)
    5: "원자재",         # 예: KODEX 골드선물 (주도주 분석 제외)
    6: "채권",           # 예: KODEX 국고채3년 (주도주 분석 제외)
    7: "기타"            # 기타 파생 및 액티브 펀드
}

def fetch_etf_list():
    """
    네이버 금융 서버 API에 직접 접속하여 상장된 ETF 데이터를 끌어오는 핵심 함수입니다.
    """
    # 네이버 금융 ETF 목록 데이터를 제공하는 실시간 API 주소
    url = "https://finance.naver.com/api/sise/etfItemList.nhn"
    
    # 웹 브라우저(크롬 등)에서 접속하는 것처럼 속이기 위한 헤더 설정 (차단 방지)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://finance.naver.com/sise/etf.naver"
    }

    # 인터넷 접속 요청 생성
    req = urllib.request.Request(url, headers=headers)
    try:
        # 네이버 서버에 접속하여 응답 데이터를 받습니다.
        with urllib.request.urlopen(req) as response:
            # EUC-KR(한글 인코딩) 데이터를 글자 깨짐 없이 읽어옵니다.
            content = response.read().decode("euc-kr", errors="ignore")
            # 텍스트 형태의 응답을 파이썬 딕셔너리 구조로 변환
            data = json.loads(content)
            
            # API 응답 성공 여부 확인
            result_code = data.get("resultCode")
            if result_code != "success":
                print(f"[⚠️ 경고] 네이버 API 응답 상태가 정상이 아닙니다: {result_code}")

            # 전체 ETF 종목 리스트 추출
            raw_items = data.get("result", {}).get("etfItemList", [])
            parsed_items = []

            # 수집된 각 ETF 종목을 하나씩 검사하고 필요한 정보만 뽑아냅니다.
            for item in raw_items:
                code = item.get("itemcode", "")      # 6자리 종목코드 (예: '069500')
                name = item.get("itemname", "")      # ETF 종목명 (예: 'KODEX 200')
                tab_code = item.get("etfTabCode", 0) # 카테고리 번호 (1: 지수, 2: 업종/테마 등)
                
                # 💡 핵심 필터: 카테고리 1(국내 시장지수)과 2(국내 업종/테마)만 골라냅니다.
                # (채권, 해외주식, 레버리지/인버스 파생상품 등은 제외)
                if tab_code not in (1, 2):
                    continue

                # 숫자 카테고리를 알아보기 쉬운 한글 명칭으로 변환
                category = TAB_CATEGORY_MAP.get(tab_code, "기타")
                
                # 네이버 증권 시세/수급 페이지 웹주소 자동 생성
                detail_url = f"https://stock.naver.com/domestic/stock/{code}/price"

                # 예쁘게 정리된 종목 정보를 리스트에 추가
                parsed_items.append({
                    "종목코드": code,
                    "종목명": name,
                    "카테고리코드": tab_code,
                    "카테고리명": category,
                    "상세페이지": detail_url
                })

            return parsed_items

    except Exception as e:
        print(f"[❌ 오류] 인터넷 접속 또는 데이터 읽기 중 오류가 발생했습니다: {e}")
        sys.exit(1)

def main():
    """
    프로그램이 실행되면 가장 먼저 동작하는 메인 실행 함수입니다.
    """
    # 터미널 입력 옵션 설정 (예: python3 getEtfList.py --save-csv my_etf.csv)
    parser = argparse.ArgumentParser(description="[1단계] 네이버 주식 ETF 목록 수집 스크립트")
    parser.add_argument("--save-csv", type=str, default="data/etf_list.csv", help="저장할 CSV 파일 경로 (기본값: data/etf_list.csv)")
    parser.add_argument("--save-json", type=str, default=None, help="저장할 JSON 파일 경로 (필요 시 지정)")
    parser.add_argument("--category", type=int, choices=[1, 2, 3, 4, 5, 6, 7], help="특정 카테고리만 필터링 (1: 지수, 2: 업종/테마)")
    parser.add_argument("--limit", type=int, default=0, help="수집할 종목 수 제한 (테스트용, 0이면 전체)")
    args = parser.parse_args()

    print("\n🚀 [1단계] 네이버 금융 ETF 전체 목록 수집을 시작합니다...")
    
    # 1. 네이버 서버에서 ETF 목록 수집 실행
    items = fetch_etf_list()
    print(f"✅ 총 {len(items)}개의 국내 주식형 ETF 종목 수집을 완료했습니다.")

    # 2. 특정 카테고리 필터 옵션이 있는 경우 적용
    if args.category:
        items = [item for item in items if item["카테고리코드"] == args.category]
        category_name = TAB_CATEGORY_MAP.get(args.category, "")
        print(f"🔍 카테고리 필터링 적용: '{category_name}' (남은 종목 수: {len(items)}개)")

    # 3. 수집 개수 제한 옵션이 있는 경우 적용
    display_items = items[:args.limit] if args.limit > 0 else items

    # 4. 화면(콘솔)에 상위 15개 미리보기 출력
    print("\n" + "=" * 100)
    print(f"{'순번':<4} | {'종목코드':<8} | {'종목명':<30} | {'카테고리명':<10} | {'상세페이지 주소'}")
    print("-" * 100)
    
    preview_count = min(15, len(display_items))
    for idx, item in enumerate(display_items[:preview_count], 1):
        print(f"{idx:<4} | {item['종목코드']:<8} | {item['종목명']:<30} | {item['카테고리명']:<10} | {item['상세페이지']}")
    
    if len(display_items) > preview_count:
        print(f"... 외 {len(display_items) - preview_count}개 종목 생략")
    print("=" * 100)

    # 5. 수집 결과를 CSV 파일로 저장 (엑셀에서 열 수 있는 utf-8-sig 인코딩)
    if args.save_csv:
        save_dir = os.path.dirname(args.save_csv)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True) # 폴더가 없으면 자동 생성
            
        fieldnames = list(items[0].keys()) if items else []
        with open(args.save_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader() # 맨 위 헤더 컬럼 작성
            writer.writerows(items) # 수집 데이터 대입
        print(f"💾 [저장 완료] CSV 파일이 저장되었습니다: {args.save_csv}")

    # 6. JSON 저장 옵션이 설정된 경우 JSON 파일로도 저장
    if args.save_json:
        save_json_dir = os.path.dirname(args.save_json)
        if save_json_dir:
            os.makedirs(save_json_dir, exist_ok=True)
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        print(f"💾 [저장 완료] JSON 파일이 저장되었습니다: {args.save_json}")

if __name__ == "__main__":
    main()
