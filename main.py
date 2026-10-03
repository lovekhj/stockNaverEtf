#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 [통합 실행기] 네이버 주식 ETF 주도주 분석 파이프라인 매니저 (main.py)
================================================================================
1. 프로그램 역할:
   1단계부터 5단계까지의 개별 데이터 수집 및 분석 스크립트를 하나로 통합하여
   터미널에서 번호 선택(대화형 메뉴) 또는 옵션 명령어로 손쉽게 실행할 수 있게 
   해주는 전체 파이프라인 관리 메인 프로그램입니다.

2. 파이프라인 구성 단계:
   - [1단계] `getEtfList.py`      : 네이버 금융 ETF 전체 목록 수집 -> data/etf_list.csv
   - [2단계] `getEtfDtlList.py`   : ETF별 상위 1~5위 주요 구성종목 수집 -> data/etf_dtl_list.csv
   - [3단계] `getEtfTopStockList.py`: 순수 국내주식 320개 정제 및 6자리 종목코드 매핑 -> data/etf_top_stocks.csv
   - [4단계] `getEtfInvestorFlow.py`: 외인/기관 수급 & 이동평균선(MA) 통합 분석 -> 분석/분석_YYYYMMDD.csv
   - [5단계] `getEtfAiReport.py`  : AI 추세추종 종합 분석 마크다운 리포트 자동 생성 -> 분석/분석_YYYYMMDD.md

3. 주요 실행 방법:
   - 대화형 메뉴 (추천) : `python3 main.py` 실행 후 엔터(기본값 4+5단계 자동실행) 또는 번호 선택
   - 전체 자동 실행     : `python3 main.py --all` (1단계부터 5단계까지 전체 순차 실행)
   - 특정 단계만 실행   : `python3 main.py --step 5` 또는 `python3 main.py --step 4,5`
================================================================================
"""

import sys             # 파이썬 시스템 및 명령행 인자 제어 라이브러리
import argparse        # 명령행 인자 파서
import subprocess      # 파이썬 서브 프로세스로 각 단계별 스크립트를 실행해주는 도구
import time            # 소요 시간 측정을 위한 타임 라이브러리
import os              # 파일 및 폴더 제어 라이브러리
from datetime import datetime # 실행 시각 기록 라이브러리

def run_step(step_num, title, script_name, extra_args=None):
    """
    특정 단계 스크립트(예: getEtfList.py)를 서브프로세스로 안전하게 실행하고 
    화면에 실시간 진행 상황 및 단계별 소요 시간을 보여주는 보조 함수입니다.
    
    :param step_num: 단계 번호 (1~5)
    :param title: 단계 제목 설명
    :param script_name: 실행할 파이썬 파일명 (예: 'getEtfList.py')
    :param extra_args: 스크립트에 전달할 추가 명령어 인자 리스트
    """
    print("\n" + "=" * 90)
    print(f"🚀 [{step_num}단계] {title} 시작 (`{script_name}`)")
    print("=" * 90)
    
    # 현재 실행 중인 파이프라인 파이썬 엔진(sys.executable)으로 하위 스크립트 실행
    cmd = [sys.executable, script_name]
    if extra_args:
        cmd.extend(extra_args)
        
    start_time = time.time()
    # 서브프로세스 실행 (종료될 때까지 대기)
    result = subprocess.run(cmd)
    elapsed = time.time() - start_time
    
    if result.returncode != 0:
        print(f"\n❌ [{step_num}단계] {script_name} 실행 중 오류가 발생했습니다. (종료 코드: {result.returncode})")
        sys.exit(result.returncode)
    else:
        print(f"\n✅ [{step_num}단계] {title} 완료! (소요시간: {elapsed:.1f}초)")

def show_interactive_menu():
    """
    사용자가 CLI 터미널 창에서 직접 실행 번호(1~5, 0:전체)를 선택할 수 있는
    직관적인 대화형 메뉴판을 출력합니다.
    """
    print("\n" + "=" * 90)
    print("📊 [네이버 주식 ETF 주도주 분석 파이프라인] 대화형 실행 메뉴")
    print("=" * 90)
    print("  1. [1단계] ETF 전체 목록 수집                  (`getEtfList.py`)")
    print("  2. [2단계] ETF 상위 1~5위 구성종목 수집          (`getEtfDtlList.py`)")
    print("  3. [3단계] 주도주 6자리 종목코드/상세페이지 추출 (`getEtfTopStockList.py`)")
    print("  4. [4단계] 외국인/기관 수급 & 이동평균선 통합 분석 (`getEtfInvestorFlow.py`)")
    print("  5. [5단계] AI 추세추종 분석 마크다운 리포트 생성 (`getEtfAiReport.py`)")
    print("  0. [전체]  1단계부터 5단계까지 전체 파이프라인 순차 실행")
    print("=" * 90)
    print("💡 팁: 쉼표나 하이픈으로 여러 단계를 지정할 수 있습니다 (예: 4,5 또는 1-5 또는 기본 엔터: 4+5단계)")
    print("=" * 90)
    
    try:
        user_input = input("👉 실행할 단계 번호를 입력하세요 [기본값: 4,5] (엔터 치면 4,5단계 / 0:전체 / q:종료): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n[알림] 프로그램을 종료합니다.")
        sys.exit(0)
        
    if user_input.lower() in ('q', 'quit', 'exit'):
        print("[알림] 프로그램을 종료합니다.")
        sys.exit(0)
        
    # 아무것도 입력하지 않고 엔터를 치거나 4를 입력한 경우 -> 매일 필수인 4단계+5단계 자동 지정
    if not user_input or user_input in ("4", "4,5", "4-5"):
        print("💡 기본값인 4단계(수급&이평선 분석) + 5단계(AI 리포트 생성)를 순차 실행합니다.")
        return {4, 5}
        
    # 0번 또는 all 입력 시 1~5단계 전체 실행
    if user_input == "0" or user_input.lower() in ('all', 'a'):
        return {1, 2, 3, 4, 5}
        
    # 숫자를 구분하여 집합(set)으로 변환
    steps = set()
    if "-" in user_input:
        parts = user_input.split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            s_start, s_end = int(parts[0]), int(parts[1])
            for s in range(s_start, s_end + 1):
                if 1 <= s <= 5:
                    steps.add(s)
    else:
        for p in user_input.split(","):
            p = p.strip()
            if p.isdigit() and 1 <= int(p) <= 5:
                steps.add(int(p))
                
    if not steps:
        print("💡 기본값인 4단계 + 5단계를 실행합니다.")
        return {4, 5}
        
    return steps

def main():
    """
    통합 파이프라인 실행기의 메인 함수입니다.
    """
    parser = argparse.ArgumentParser(
        description="네이버 주식 ETF 주도주 수급 및 이동평균선(추세추종) 분석 파이프라인 통합 실행기"
    )
    # 옵션 파서 등록
    parser.add_argument("--all", action="store_true", help="1~5단계 전체 파이프라인을 순차적으로 실행합니다.")
    parser.add_argument("--step", type=str, help="실행할 단계 지정 (예: --step 4,5 또는 --step 5 또는 --step 1-5)")
    
    # 각각의 실행구분 개별 옵션
    parser.add_argument("--step1", "--etf-list", action="store_true", help="1단계: ETF 전체 목록 수집 (getEtfList.py)")
    parser.add_argument("--step2", "--etf-dtl", action="store_true", help="2단계: ETF 상위 구성종목 수집 (getEtfDtlList.py)")
    parser.add_argument("--step3", "--top-stocks", action="store_true", help="3단계: 주도주 6자리 종목코드 추출 (getEtfTopStockList.py)")
    parser.add_argument("--step4", "--investor-flow", action="store_true", help="4단계: 외국인/기관 수급 및 이동평균선 분석 (getEtfInvestorFlow.py)")
    parser.add_argument("--step5", "--ai-report", action="store_true", help="5단계: AI 추세추종 분석 마크다운 리포트 생성 (getEtfAiReport.py)")
    
    # 추가 제어 옵션
    parser.add_argument("--limit", type=int, default=0, help="스크립트별 처리 종목 수 제한 (테스트용)")
    parser.add_argument("--top-n", type=int, default=5, help="2단계 ETF당 상위 N개 종목 수집 (기본값: 5)")
    args = parser.parse_args()

    steps_to_run = set()

    # 인자 옵션 해석
    if args.all:
        steps_to_run = {1, 2, 3, 4, 5}
    else:
        if args.step:
            step_str = str(args.step).strip()
            if "-" in step_str:
                parts = step_str.split("-")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    s_start, s_end = int(parts[0]), int(parts[1])
                    for s in range(s_start, s_end + 1):
                        if 1 <= s <= 5:
                            steps_to_run.add(s)
            else:
                for p in step_str.split(","):
                    p = p.strip()
                    if p.isdigit() and 1 <= int(p) <= 5:
                        steps_to_run.add(int(p))
                        
        if args.step1: steps_to_run.add(1)
        if args.step2: steps_to_run.add(2)
        if args.step3: steps_to_run.add(3)
        if args.step4: steps_to_run.add(4)
        if args.step5: steps_to_run.add(5)

    # CLI 인자가 주어지지 않고 대화형 터미널인 경우 대화형 메뉴 띄우기
    if not steps_to_run and sys.stdin.isatty() and len(sys.argv) == 1:
        steps_to_run = show_interactive_menu()

    # 옵션 없이 실행할 경우 기본값 4단계 + 5단계 실행
    if not steps_to_run:
        print("💡 실행 옵션이 지정되지 않아 기본값으로 4단계(수급 분석) + 5단계(AI 리포트 생성)를 실행합니다.")
        print("   (전체 파이프라인 1~5단계 실행: python3 main.py --all)")
        steps_to_run = {4, 5}

    total_start = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[시작 시각: {today_str}] 선택된 네이버 주식 ETF 분석 파이프라인을 시작합니다 (실행 단계: {sorted(list(steps_to_run))}).")

    # 선택된 단계 순차 실행
    if 1 in steps_to_run:
        extra = ["--limit", str(args.limit)] if args.limit > 0 else []
        run_step(1, "ETF 전체 목록 수집", "getEtfList.py", extra)

    if 2 in steps_to_run:
        extra = []
        if args.limit > 0:
            extra.extend(["--limit-etf", str(args.limit)])
        if args.top_n > 0:
            extra.extend(["--top-n", str(args.top_n)])
        run_step(2, "ETF 상위 구성종목 수집", "getEtfDtlList.py", extra)

    if 3 in steps_to_run:
        extra = []
        run_step(3, "주도주 6자리 종목코드/상세페이지 추출", "getEtfTopStockList.py", extra)

    if 4 in steps_to_run:
        extra = ["--limit", str(args.limit)] if args.limit > 0 else []
        run_step(4, "외국인/기관 수급 & 이동평균선 통합 분석", "getEtfInvestorFlow.py", extra)

    if 5 in steps_to_run:
        extra = []
        run_step(5, "AI 추세추종 분석 마크다운 리포트 생성", "getEtfAiReport.py", extra)

    total_elapsed = time.time() - total_start
    print("\n" + "=" * 90)
    print(f"🎉 모든 파이프라인 단계 실행 완료! (전체 소요시간: {total_elapsed:.1f}초)")
    print("=" * 90)

if __name__ == "__main__":
    main()
