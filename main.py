import sys
import argparse
import subprocess
import time
import os
from datetime import datetime

def run_step(step_num, title, script_name, extra_args=None):
    """
    특정 단계 스크립트를 파이썬 서브프로세스로 실행하고 진행 상황을 모니터링합니다.
    """
    print("\n" + "=" * 90)
    print(f"🚀 [{step_num}단계] {title} 시작 (`{script_name}`)")
    print("=" * 90)
    
    cmd = [sys.executable, script_name]
    if extra_args:
        cmd.extend(extra_args)
        
    start_time = time.time()
    result = subprocess.run(cmd)
    elapsed = time.time() - start_time
    
    if result.returncode != 0:
        print(f"\n❌ [{step_num}단계] {script_name} 실행 중 오류가 발생했습니다. (종료 코드: {result.returncode})")
        sys.exit(result.returncode)
    else:
        print(f"\n✅ [{step_num}단계] {title} 완료 (소요시간: {elapsed:.1f}초)")

def show_interactive_menu():
    """
    CLI 터미널에서 터미널 사용자가 실행 번호를 선택할 수 있는 대화형 메뉴를 출력합니다.
    """
    print("\n" + "=" * 90)
    print("📊 [네이버 주식 ETF 주도주 분석 파이프라인] 대화형 실행 메뉴")
    print("=" * 90)
    print("  1. [1단계] ETF 전체 목록 수집                  (`getEtfList.py`)")
    print("  2. [2단계] ETF 상위 1~5위 구성종목 수집          (`getEtfDtlList.py`)")
    print("  3. [3단계] 주도주 6자리 종목코드/상세페이지 추출 (`getEtfTopStockList.py`)")
    print("  4. [4단계] 외국인/기관 수급 & 이동평균선 통합 분석 (`getEtfInvestorFlow.py`)")
    print("  0. [전체]  1단계부터 4단계까지 전체 파이프라인 순차 실행")
    print("=" * 90)
    print("💡 팁: 쉼표나 하이픈으로 여러 단계를 지정할 수 있습니다 (예: 1,2 또는 1-4 또는 4)")
    print("=" * 90)
    
    try:
        user_input = input("👉 실행할 단계 번호를 입력하세요 (예: 1 / 4 / 1,2 / 0 / q:종료): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n[알림] 프로그램을 종료합니다.")
        sys.exit(0)
        
    if not user_input or user_input.lower() in ('q', 'quit', 'exit'):
        print("[알림] 프로그램을 종료합니다.")
        sys.exit(0)
        
    if user_input == "0" or user_input.lower() in ('all', 'a'):
        return {1, 2, 3, 4}
        
    steps = set()
    if "-" in user_input:
        parts = user_input.split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            s_start, s_end = int(parts[0]), int(parts[1])
            for s in range(s_start, s_end + 1):
                if 1 <= s <= 4:
                    steps.add(s)
    else:
        for p in user_input.split(","):
            p = p.strip()
            if p.isdigit() and 1 <= int(p) <= 4:
                steps.add(int(p))
                
    if not steps:
        print("⚠️ 잘못된 입력이거나 범위 미초과로 인해 1~4단계 전체 파이프라인을 실행합니다.")
        return {1, 2, 3, 4}
        
    return steps

def main():
    parser = argparse.ArgumentParser(
        description="네이버 주식 ETF 주도주 수급 및 이동평균선(추세추종) 분석 파이프라인 통합 실행기"
    )
    parser.add_argument("--all", action="store_true", help="1~4단계 전체 파이프라인을 순차적으로 실행합니다.")
    parser.add_argument("--step", type=str, help="실행할 단계 지정 (예: --step 1 또는 --step 4 또는 --step 1,2 또는 --step 1-4)")
    
    # 각각의 실행구분 개별 옵션
    parser.add_argument("--step1", "--etf-list", action="store_true", help="1단계: ETF 전체 목록 수집 (getEtfList.py)")
    parser.add_argument("--step2", "--etf-dtl", action="store_true", help="2단계: ETF 상위 구성종목 수집 (getEtfDtlList.py)")
    parser.add_argument("--step3", "--top-stocks", action="store_true", help="3단계: 주도주 6자리 종목코드 추출 (getEtfTopStockList.py)")
    parser.add_argument("--step4", "--investor-flow", action="store_true", help="4단계: 외국인/기관 수급 및 이동평균선 분석 (getEtfInvestorFlow.py)")
    
    # 추가 제어 옵션
    parser.add_argument("--limit", type=int, default=0, help="스크립트별 처리 종목 수 제한 (테스트용)")
    parser.add_argument("--top-n", type=int, default=5, help="2단계 ETF당 상위 N개 종목 수집 (기본값: 5)")
    args = parser.parse_args()

    steps_to_run = set()

    if args.all:
        steps_to_run = {1, 2, 3, 4}
    else:
        if args.step:
            step_str = str(args.step).strip()
            if "-" in step_str:
                parts = step_str.split("-")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    s_start, s_end = int(parts[0]), int(parts[1])
                    for s in range(s_start, s_end + 1):
                        if 1 <= s <= 4:
                            steps_to_run.add(s)
            else:
                for p in step_str.split(","):
                    p = p.strip()
                    if p.isdigit() and 1 <= int(p) <= 4:
                        steps_to_run.add(int(p))
                        
        if args.step1: steps_to_run.add(1)
        if args.step2: steps_to_run.add(2)
        if args.step3: steps_to_run.add(3)
        if args.step4: steps_to_run.add(4)

    # CLI 인자가 주어지지 않고 대화형 터미널인 경우 대화형 메뉴 띄우기
    if not steps_to_run and sys.stdin.isatty() and len(sys.argv) == 1:
        steps_to_run = show_interactive_menu()

    # 터미널이 아니거나 인자 없이 커맨드라인에서 실행할 경우 기본값 1~4 전체 실행
    if not steps_to_run:
        print("💡 실행 옵션이 지정되지 않아 1~4단계 전체 파이프라인을 순차적으로 실행합니다.")
        print("   (도움말 확인: python3 main.py --help)")
        steps_to_run = {1, 2, 3, 4}

    total_start = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[시작 시각: {today_str}] 선택된 네이버 주식 ETF 분석 파이프라인을 시작합니다 (실행 단계: {sorted(list(steps_to_run))}).")

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

    total_elapsed = time.time() - total_start
    print("\n" + "=" * 90)
    print(f"🎉 모든 파이프라인 단계 실행 완료! (전체 소요시간: {total_elapsed:.1f}초)")
    print("=" * 90)

if __name__ == "__main__":
    main()
