#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 [2단계] ETF 상위 구성종목(포트폴리오 Top 1~10위) 수집 프로그램 (getEtfDtlList.py)
================================================================================
1. 프로그램 역할:
   1단계에서 수집한 ETF 목록(`data/etf_list.csv`)을 읽어와서 각 ETF 펀드가
   어떤 주식 종목들을 가장 많이 담고 있는지(상위 1~10위 주요 구성종목 및 편입비율)
   WiseReport 기업분석 서버에서 정밀 수집합니다.

2. 입력 데이터:
   - CSV 파일: `data/etf_list.csv` (1단계 실행 결과)

3. 출력 결과:
   - CSV 파일: `data/etf_dtl_list.csv` (ETF명, 구성종목명, 편입비율 등 약 4,000여 개 구성 행)

4. 주요 작동 흐름 (누구나 이해할 수 있는 단계별 설명):
   - 1단계 [읽기]: 1단계에서 만든 `data/etf_list.csv` 목록을 불러옵니다.
   - 2단계 [조회]: 각 ETF마다 와이즈리포트(WiseReport) 기업정보 페이지에 접속합니다.
   - 3단계 [추출]: 해당 ETF의 자산 중 상위 1~10위에 해당하는 구성 주식 종목명과 비중(%)을 뽑아냅니다.
   - 4단계 [저장]: 전체 ETF의 상위 구성종목들을 모아서 `data/etf_dtl_list.csv` 파일로 저장합니다.
================================================================================
"""

import urllib.request  # 웹 페이지 접속을 위한 파이썬 표준 라이브러리
import json            # JSON 데이터 해석 도구
import csv             # CSV 파일 읽기/쓰기 도구
import re              # 웹 페이지 텍스트에서 특수한 패턴(JSON 데이터 등)을 찾는 정규표현식 라이브러리
import argparse        # 명령행 실행 옵션 처리 라이브러리
import sys             # 프로그램 종료 처리 라이브러리
import time            # 연속 접속 시 서버 부하를 줄이기 위한 대기시간(sleep) 제공 도구
import os              # 디렉토리 생성 및 파일 존재 여부 확인 도구

def fetch_etf_portfolio(etf_code):
    """
    WiseReport(와이즈리포트) 기업 정보 서버에서 특정 ETF의 구성종목(포트폴리오) 데이터를 수집합니다.
    
    :param etf_code: 6자리 ETF 종목코드 (예: '069500')
    :return: 구성종목명, 편입비율이 담긴 딕셔너리 리스트
    """
    # 와이즈리포트 ETF 상세 분석 웹페이지 주소
    url = f"https://navercomp.wisereport.co.kr/v2/company/c1080001.aspx?cmp_cd={etf_code}"
    
    # 웹 브라우저 접속인 것처럼 요청 헤더 설정
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://finance.naver.com/item/main.naver?code={etf_code}"
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            # 웹페이지 전체 HTML 소스를 가져옵니다.
            html = response.read().decode("utf-8", errors="ignore")
            
            # 💡 정규표현식(re)을 사용하여 HTML 코드 속에 포함된 자바스크립트 변수 'var CU_data = {...};' 자산을 찾아냅니다.
            m = re.search(r'var\s+CU_data\s*=\s*(\{.*?\});', html, re.DOTALL)
            if not m:
                return [] # 포트폴리오 정보가 없는 경우 빈 리스트 반환

            # 추출한 텍스트 형태의 자바스크립트 객체를 파이썬 JSON 딕셔너리로 해석
            data = json.loads(m.group(1))
            grid_data = data.get("grid_data", [])

            constituents = []
            for item in grid_data:
                stk_name = item.get("STK_NM_KOR", "").strip() # 한글 종목명 (예: '삼성전자')
                if not stk_name:
                    continue
                
                weight = item.get("ETF_WEIGHT")  # ETF 내 편입 비율(%)
                cnt = item.get("AGMT_STK_CNT")    # 설정 단위당 보유 주식 수

                # 💡 보기 쉽게 편입비율 포맷 정리 (예: '24.50%')
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
        print(f"[⚠️ 경고] ETF 종목코드({etf_code}) 포트폴리오 수집 중 오류: {e}")
        return []

def main():
    """
    [2단계] ETF 상위 구성종목 수집 메인 실행 함수입니다.
    """
    default_input = "data/etf_list.csv" if os.path.exists("data/etf_list.csv") else "etf_list.csv"
    
    parser = argparse.ArgumentParser(description="[2단계] ETF 상위 구성종목(포트폴리오) 수집 스크립트")
    parser.add_argument("--input-csv", type=str, default=default_input, help=f"1단계에서 만든 ETF 목록 CSV 경로 (기본값: {default_input})")
    parser.add_argument("--save-csv", type=str, default="data/etf_dtl_list.csv", help="저장할 CSV 파일 경로 (기본값: data/etf_dtl_list.csv)")
    parser.add_argument("--save-json", type=str, default=None, help="저장할 JSON 파일 경로")
    parser.add_argument("--limit-etf", type=int, default=0, help="수집할 ETF 수 제한 (테스트용, 0이면 전체)")
    parser.add_argument("--top-n", type=int, default=10, help="ETF당 상위 N개 구성종목만 추출 (기본값: 10위까지)")
    parser.add_argument("--delay", type=float, default=0.03, help="요청 간 대기시간(초) (기본값: 0.03초)")
    args = parser.parse_args()

    # 1. 1단계에서 저장한 `data/etf_list.csv` 파일 불러오기
    try:
        with open(args.input_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            etf_list = list(reader)
    except Exception as e:
        print(f"[❌ 오류] '{args.input_csv}' 파일을 읽는 도중 에러가 발생했습니다: {e}")
        print("💡 팁: 1단계 스크립트(getEtfList.py)를 먼저 실행했는지 확인하세요.")
        sys.exit(1)

    print(f"\n🚀 [2단계] '{args.input_csv}' 파일에서 총 {len(etf_list)}개의 ETF 목록을 읽었습니다.")

    # 2. 테스트용 수집 개수 제한이 걸려있으면 제한 적용
    if args.limit_etf > 0:
        etf_list = etf_list[:args.limit_etf]
        print(f"🔍 ETF 처리 제한 적용: {len(etf_list)}개 ETF만 처리합니다.")

    top_n_label = f"상위 1~{args.top_n}위" if args.top_n > 0 else "전체"
    print(f"📊 각 ETF당 {top_n_label} 주요 구성종목(주도주 분석용) 수집을 시작합니다...\n")

    detailed_rows = []
    total_etfs = len(etf_list)
    start_time = time.time()

    # 3. 전체 ETF 목록을 순회하며 와이즈리포트에서 상위 구성종목 수집
    for idx, etf in enumerate(etf_list, 1):
        code = etf.get("종목코드", "").strip()
        name = etf.get("종목명", "").strip()
        cat_code = etf.get("카테고리코드", "").strip()
        cat_name = etf.get("카테고리명", "").strip()
        detail_url = etf.get("상세페이지", "").strip()

        if not code:
            continue

        # 와이즈리포트 API로 포트폴리오 추출
        constituents = fetch_etf_portfolio(code)

        # 💡 주도주 분석 핵심: 각 ETF에서 가장 비중이 큰 상위 N개(기본 1~10위) 종목만 자릅니다.
        if args.top_n > 0:
            constituents = constituents[:args.top_n]

        # 비율 순서대로 순번(1위~N위) 부여하여 결과 저장
        for seq, item in enumerate(constituents, 1):
            detailed_rows.append({
                "종목코드": code,
                "종목명": name,
                "카테고리코드": cat_code,
                "카테고리명": cat_name,
                "상세페이지": detail_url,
                "순번": seq,                    # 순위 (1~10위)
                "구성종목명": item["구성종목명"],  # 구성 주식 종목명 (예: 삼성전자)
                "비율": item["비율"]             # 편입 비중 (예: 21.34%)
            })

        # 20개 단위 및 진행 과정에 대해 실시간 진행상황 로그 출력
        if idx % 20 == 0 or idx == total_etfs or idx == 1:
            elapsed = time.time() - start_time
            pct = (idx / total_etfs) * 100
            avg_per_item = elapsed / idx
            remaining = (total_etfs - idx) * avg_per_item
            print(f"⏳ [{idx:3d}/{total_etfs:3d}] ({pct:5.1f}%) | 처리중: [{code}] {name[:16]:<16} | 누적 구성종목: {len(detailed_rows):4d}개 | 경과: {elapsed:5.1f}초 (남은시간: 약 {remaining:4.1f}초)")

        # 서버 과부하 방지를 위한 짧은 대기시간
        time.sleep(args.delay)

    print(f"\n✅ [수집 완료] 총 {total_etfs}개 ETF에서 {len(detailed_rows)}개의 주도주({top_n_label}) 데이터 수집 완료! (총 소요시간: {time.time() - start_time:.1f}초)")

    # 4. 수집한 결과를 `data/etf_dtl_list.csv` 파일로 저장
    if args.save_csv:
        save_dir = os.path.dirname(args.save_csv)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            
        fieldnames = ["종목코드", "종목명", "카테고리코드", "카테고리명", "상세페이지", "순번", "구성종목명", "비율"]
        with open(args.save_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(detailed_rows)
        print(f"💾 [저장 완료] CSV 파일이 저장되었습니다: {args.save_csv}")

    # JSON 저장 옵션이 있는 경우 저장
    if args.save_json:
        save_json_dir = os.path.dirname(args.save_json)
        if save_json_dir:
            os.makedirs(save_json_dir, exist_ok=True)
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(detailed_rows, f, ensure_ascii=False, indent=2)
        print(f"💾 [저장 완료] JSON 파일이 저장되었습니다: {args.save_json}")

if __name__ == "__main__":
    main()
