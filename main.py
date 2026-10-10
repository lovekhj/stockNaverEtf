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
   - [4단계] `getEtfInvestorFlow.py`: 외인/기관 수급 & 이동평균선(MA) 통합 분석 -> reports/report_YYYYMMDD.csv
   - [5단계] `getEtfAiReport.py`  : AI 추세추종 종합 분석 마크다운/PDF 리포트 자동 생성 -> reports/report_YYYYMMDD.md & reports/pdf/report_YYYYMMDD.pdf

3. 주요 실행 방법 및 옵션 조합:
   - 대화형 메뉴 (추천) : `python3 main.py` (엔터 치면 기본 4+5단계 실행)
   - 전체 파이프라인    : `python3 main.py --all` (1단계부터 5단계까지 순차 실행)
   - 특정 단계 지정     : `python3 main.py --step 4,5`
   - 특정 거래일자 지정: `python3 main.py --date 20261006` (미지정 시 최신 장마감 거래일 자동 감지)
   - PDF 리포트 생성   : `python3 main.py --step 5 --pdf` (MD 및 PDF 리포트 동시 생성)
   - 텔레그램 분석+알림: `python3 main.py --step 4,5 --telegram` (4,5단계 후 매수신호 A 종목 전송)
   - 텔레그램 단독 발송: `python3 main.py --telegram-only` (분석 없이 기존 리포트만 전송)
   - 깃허브 자동 푸시   : `python3 main.py --push-git` (리포트/결과 파일 GitHub Push: "주식분석_자동화_YYYYMMDD")
   - 깃푸시 단독 실행   : `python3 main.py --push-git-only` (분석 없이 Git 커밋 및 Push만 진행)
   - 맥 4시 자동스케줄er: `python3 main.py --step 4,5 --telegram --push-git` (통합 실행)
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
    print("  2. [2단계] ETF 상위 1~10위 구성종목 수집         (`getEtfDtlList.py`)")
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

class TeeLogger:
    """
    터미널 화면 출력(stdout/stderr)을 실시간으로 유지하면서
    reports/log_YYYYMMDD.txt 파일에 동시에 대화식/자동 실행 로그를 기록하는 클래스
    """
    def __init__(self, log_filepath):
        self.terminal = sys.stdout
        self.log_filepath = log_filepath

    def write(self, message):
        self.terminal.write(message)
        try:
            with open(self.log_filepath, "a", encoding="utf-8") as f:
                f.write(message)
        except Exception:
            pass

    def flush(self):
        self.terminal.flush()

import csv
import urllib.request
import urllib.parse
import json

def update_available_dates_js():
    """
    reports/report_YYYYMMDD.csv 파일 목록을 스캔하여 대시보드(index.html)가 읽는
    reports/available_dates.js (window.AVAILABLE_DATES) 파일을 자동 생성합니다.
    """
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    dates = sorted(
        f[len("report_"):-len(".csv")]
        for f in os.listdir(reports_dir)
        if f.startswith("report_") and f.endswith(".csv") and f[len("report_"):-len(".csv")].isdigit()
    )
    js_path = os.path.join(reports_dir, "available_dates.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("// 자동 생성 파일 (main.py) - 직접 수정하지 마세요.\n")
        f.write("window.AVAILABLE_DATES = [\n")
        f.write(",\n".join(f'  "{d}"' for d in dates))
        f.write("\n];\n")
    print(f"🗓️  [대시보드 날짜 목록 갱신] reports/available_dates.js ({len(dates)}개 일자, 최신: {dates[-1] if dates else '-'})")
    return dates

def load_env_file():
    """
    프로젝트 루트의 .env 파일이 존재하는 경우 환경 변수를 읽어오도록 지원하는 보조 함수
    """
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip("'").strip('"')
        except Exception:
            pass

def send_telegram_pdf_document(bot_token, chat_id, pdf_path):
    """
    ============================================================================
    📌 [보조 함수] 텔레그램 PDF 리포트 파일 자동 업로드 및 전송 (sendDocument)
    ============================================================================
    - 텔레그램 봇 API의 'sendDocument' 엔드포인트를 호출하여
      생성된 PDF 리포트 파일(pdf/report_YYYYMMDD.pdf)을 대화방으로 직접 업로드합니다.
    - 외부 라이브러리 없이 파이썬 표준 라이브러리(urllib)로 멀티파트 폼 데이터
      (multipart/form-data) 규격을 조립하여 안전하게 파일 바이너리를 전달합니다.
    """
    if not os.path.exists(pdf_path):
        return False, f"PDF 파일 없음 ({pdf_path})"

    # 텔레그램 문서 전송 API 엔드포인트 URL
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    # HTTP 멀티파트 데이터 구분을 위한 바운더리 스트링
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    filename = os.path.basename(pdf_path)
    
    try:
        # PDF 파일의 바이너리 데이터 읽기
        with open(pdf_path, "rb") as f:
            file_bytes = f.read()

        # HTTP 멀티파트 바디 데이터 조립 시작
        body = []
        # 1) 수신 대화방 ID (chat_id) 필드
        body.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode('utf-8'))
        # 2) 파일 설명/캡션 (caption) 필드
        body.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n📄 [AI 주도주 종합 분석 PDF 리포트]\r\n".encode('utf-8'))
        # 3) PDF 문서 파일 데이터 (document) 필드
        body.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{filename}\"\r\nContent-Type: application/pdf\r\n\r\n".encode('utf-8'))
        body.append(file_bytes)
        body.append(f"\r\n--{boundary}--\r\n".encode('utf-8'))
        
        payload = b"".join(body)
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }

        # HTTP POST 요청 발송
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            if res_body.get("ok"):
                return True, f"PDF 리포트({filename}) 전송 완료"
            else:
                return False, f"텔레그램 API 응답 오류 ({res_body})"
    except Exception as e:
        return False, f"PDF 전송 중 예외 발생 ({e})"

TELEGRAM_MAX_STOCKS = 40  # 메세지 한 통에 싣는 최대 종목 수 (텔레그램 글자 수 제한 4,096자 대비)

def build_signal_message(report_file, date_str):
    """
    4단계 분석 CSV에서 매수신호 A 종목을 뽑아 텔레그램 요약 메세지를 만듭니다.

    :return: (메세지 문자열, 매수신호 A 종목 수)
    """
    signal_stocks = []
    grade_counts = {}
    with open(report_file, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            grade = row.get("투자등급", "").strip()
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
            if row.get("매수신호", "").strip().startswith("A"):
                signal_stocks.append(row)

    lines = [f"🎯 <b>[매수신호 A 알림 - {date_str}]</b>",
             "강한 마감(+3% 이상, 거래량 1.5배 이상) + 정배열(종가 > 5 > 20 > 60일선)", ""]
    if signal_stocks:
        lines.append(f"<b>[매수신호 A 종목 {len(signal_stocks)}개]</b>")
        for idx, row in enumerate(signal_stocks[:TELEGRAM_MAX_STOCKS], 1):
            name = row.get("종목명", "").strip()
            sector = row.get("섹터", "").strip() or "일반 주도주"
            price = row.get("현재가", "").strip() or "0"
            chg = row.get("등락률", "").strip() or "-"
            candle = row.get("차트꼬리", "").strip() or "-"
            lines.append(f"{idx}. <b>{name}</b> / {sector} / {price}원 / {chg} / {candle} / 등급 {row.get('투자등급', '-').strip()}")
        if len(signal_stocks) > TELEGRAM_MAX_STOCKS:
            lines.append(f"... 외 {len(signal_stocks) - TELEGRAM_MAX_STOCKS}개 (대시보드에서 확인)")
    else:
        lines.append("ℹ️ 오늘 매수신호 A 종목이 없습니다.")

    lines.append("")
    lines.append(f"투자등급 분포: A+ {grade_counts.get('A+', 0)}개 / A {grade_counts.get('A', 0)}개 / B {grade_counts.get('B', 0)}개 / C {grade_counts.get('C', 0)}개")
    lines.append("※ 기준일 종가 매수 기준, 검증 중인 후보 규칙입니다. 매도는 종가가 보유 중 최고 종가 -5% 이하일 때. 매수·매도 추천이 아닙니다.")
    return "\n".join(lines), len(signal_stocks)

def send_telegram_notification(bot_token, chat_id, target_date=None, send_pdf=False):
    """
    ============================================================================
    📌 [텔레그램 메세지 및 PDF 리포트 통합 전송 함수]
    ============================================================================
    1. 역할:
       - 4단계 분석 결과에서 매수신호 A 종목 요약 텍스트를 발송합니다.
       - `pdf/report_YYYYMMDD.pdf` 파일이 존재하거나 `--pdf` 옵션이 지정된 경우
         PDF 종합 보고서 파일도 텔레그램 대화방에 자동으로 첨부하여 발송합니다.
    """
    # 1. 텔레그램 인증 정보 확인
    if not bot_token or not chat_id:
        msg = "TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID 미설정"
        print(f"\n⚠️ [텔레그램 경고] --telegram 옵션이 켜졌으나 {msg} 상태입니다.")
        print("💡 사용 방법: .env 파일 설정 또는 --bot-token / --chat-id 옵션으로 전달하세요.")
        return False, msg

    # 2. 대상 분석 결과 CSV 파일(report_YYYYMMDD.csv) 경로 감지
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    if not target_date:
        csv_files = [f for f in os.listdir(reports_dir) if f.startswith("report_") and f.endswith(".csv")]
        if not csv_files:
            msg = "분석 결과 CSV 파일 없음"
            print(f"⚠️ [텔레그램 경고] {msg}")
            return False, msg
        csv_files.sort(reverse=True)
        report_file = os.path.join(reports_dir, csv_files[0])
    else:
        report_file = os.path.join(reports_dir, f"report_{target_date}.csv")
        if not os.path.exists(report_file):
            msg = f"분석 파일 ({report_file}) 없음"
            print(f"⚠️ [텔레그램 경고] {msg}")
            return False, msg

    date_str = os.path.basename(report_file).replace("report_", "").replace(".csv", "")
    
    # 3~4. CSV 파일을 읽어 매수신호 A 종목 요약 메세지 조립
    try:
        message_text, signal_count = build_signal_message(report_file, date_str)
    except Exception as e:
        msg = f"CSV 읽기 예외 ({e})"
        print(f"⚠️ [텔레그램 오류] {msg}")
        return False, msg

    # 5. 텔레그램 요약 메세지 발송 (sendMessage API)
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML"
    }
    
    text_sent = False
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            if res_body.get("ok"):
                desc = f"매수신호 A {signal_count}개 전송 완료"
                print(f"📲 [텔레그램 메세지 전송 성공] {desc}")
                text_sent = True
            else:
                print(f"❌ [텔레그램 메세지 전송 실패] 응답: {res_body}")
    except Exception as e:
        print(f"❌ [텔레그램 메세지 전송 오류] {e}")

    # 6. PDF 리포트 파일(pdf/report_YYYYMMDD.pdf)이 존재하는 경우 PDF 문서 첨부 자동 발송
    pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf", f"report_{date_str}.pdf")
    pdf_status = ""
    if os.path.exists(pdf_path):
        pdf_success, pdf_msg = send_telegram_pdf_document(bot_token, chat_id, pdf_path)
        if pdf_success:
            print(f"📄 [텔레그램 PDF 리포트 전송 성공] {pdf_msg}")
            pdf_status = " + PDF 리포트 첨부 발송 완료"
        else:
            print(f"⚠️ [텔레그램 PDF 전송 경고] {pdf_msg}")

    final_desc = f"매수신호 A {signal_count}개 전송 완료{pdf_status}"
    return text_sent, final_desc

def run_git_auto_push(target_date=None):
    """
    --push-git 옵션이 지정된 경우에만 git add, git commit 및 git push를 전송합니다.
    """
    today_str = target_date or datetime.now().strftime("%Y%m%d")
    commit_msg = f"주식분석_자동화_{today_str}"
    print("\n" + "=" * 90)
    print("🚀 [--push-git] 옵션 활성화: GitHub 원격 저장소로 자동 커밋 및 푸시를 실행합니다...")
    print(f"📌 커밋 메시지: {commit_msg}")
    print("=" * 90)
    
    try:
        res_add = subprocess.run(["git", "add", "-A"], capture_output=True, text=True)
        if res_add.returncode != 0:
            print(f"⚠️ [Git Add 경고] {res_add.stderr}")
            
        res_commit = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)
        is_clean = False
        if res_commit.returncode != 0:
            if "nothing to commit" in res_commit.stdout or "nothing to commit" in res_commit.stderr:
                is_clean = True
                print("💡 [Git Info] 커밋할 변경 파일이 없습니다.")
            else:
                print(f"⚠️ [Git Commit 경고] {res_commit.stdout} {res_commit.stderr}")
        else:
            print(f"✅ [Git Commit 성공] 커밋 메시지: '{commit_msg}'")
            
        res_push = subprocess.run(["git", "push"], capture_output=True, text=True)
        if res_push.returncode == 0:
            desc = "변경 파일 없음 (최신)" if is_clean else f"Push 완료 ({commit_msg})"
            print(f"🎉 [Git Push 성공] {desc}")
            return True, desc
        else:
            desc = f"Push 실패 ({res_push.stderr.strip()})"
            print(f"❌ [Git Push 실패] {desc}")
            return False, desc
    except Exception as e:
        desc = f"Git 실행 예외 ({e})"
        print(f"❌ [Git 실행 오류] {desc}")
        return False, desc

def main():
    """
    통합 파이프라인 실행기의 메인 함수입니다.
    """
    load_env_file()
    
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
    parser.add_argument("--top-n", type=int, default=10, help="2단계 ETF당 상위 N개 종목 수집 (기본값: 10)")
    parser.add_argument("--date", type=str, help="분석 대상 거래일자 (YYYYMMDD 형식, 미지정 시 API 최신 마감 거래일 자동 감지)")
    parser.add_argument("--pdf", action="store_true", help="5단계 리포트 생성 시 PDF 파일(reports/report_YYYYMMDD.pdf)을 함께 생성합니다.")

    # 깃푸시 및 텔레그램 전송 옵션
    parser.add_argument("--push-git", "--git", action="store_true", help="분석 완료 후 Git 커밋 및 Push를 자동으로 실행합니다. (기본값: False)")
    parser.add_argument("--push-git-only", "--git-only", "--only-git", action="store_true", help="1~5단계 수집/분석을 실행하지 않고, Git 커밋 및 Push만 단독으로 실행합니다.")
    parser.add_argument("--telegram", "--notify", action="store_true", help="분석 완료 후 A+ 등급 핵심 주도주 종목명을 텔레그램으로 전송합니다. (기본값: False)")
    parser.add_argument("--telegram-only", "--only-telegram", action="store_true", help="1~5단계 수집/분석을 실행하지 않고 기존 최신 리포트로 텔레그램 알림만 단독 발송합니다.")
    parser.add_argument("--bot-token", type=str, default=os.getenv("TELEGRAM_BOT_TOKEN", ""), help="텔레그램 봇 토큰 (기본값: TELEGRAM_BOT_TOKEN 환경변수)")
    parser.add_argument("--chat-id", type=str, default=os.getenv("TELEGRAM_CHAT_ID", ""), help="텔레그램 대화방/채널 ID (기본값: TELEGRAM_CHAT_ID 환경변수)")

    args = parser.parse_args()

    if args.telegram_only:
        args.telegram = True
    if args.push_git_only:
        args.push_git = True

    steps_to_run = set()

    # 인자 옵션 해석
    if args.telegram_only or args.push_git_only:
        steps_to_run = set()
    elif args.all:
        steps_to_run = {1, 2, 3, 4, 5}
    else:
        if args.step:
            step_str = str(args.step).strip().lower()
            if step_str in ("0", "none", "telegram", "git"):
                steps_to_run = set()
            elif "-" in step_str:
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

    # 옵션 없이 실행할 경우 기본값 4단계 + 5단계 실행 (단, 단독 발송 모드가 아닌 경우)
    is_explicit_standalone = (
        args.telegram_only or 
        args.push_git_only or 
        (args.step and str(args.step).strip().lower() in ("0", "none", "telegram", "git"))
    )
    if not steps_to_run and not is_explicit_standalone:
        print("💡 실행 옵션이 지정되지 않아 기본값으로 4단계(수급 분석) + 5단계(AI 리포트 생성)를 실행합니다.")
        print("   (전체 파이프라인 1~5단계 실행: python3 main.py --all)")
        steps_to_run = {4, 5}

    # 📌 reports/log_YYYYMMDD.txt 로거 설정
    today_ymd = datetime.now().strftime("%Y%m%d")
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    log_filepath = os.path.join(reports_dir, f"log_{today_ymd}.txt")

    sys.stdout = TeeLogger(log_filepath)
    sys.stderr = sys.stdout

    total_start = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 90)
    print(f"📌 [파이프라인 실행 시작 시각: {today_str}] (로그 파일: {log_filepath})")
    print(f"📌 실행 대상 단계: {sorted(list(steps_to_run))}")
    print(f"📌 깃 자동 푸시: {'활성화 (--push-git)' if args.push_git else '비활성화 (수동)'}")
    print(f"📌 텔레그램 전송: {'활성화 (--telegram)' if args.telegram else '비활성화'}")
    print("=" * 90)

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
        extra = []
        if args.limit > 0:
            extra.extend(["--limit", str(args.limit)])
        if args.date:
            extra.extend(["--date", str(args.date)])
        run_step(4, "외국인/기관 수급 & 이동평균선 통합 분석", "getEtfInvestorFlow.py", extra)

    if 5 in steps_to_run:
        extra = []
        if args.date:
            extra.extend(["--date", str(args.date)])
        if args.pdf:
            extra.extend(["--pdf"])
        run_step(5, "AI 추세추종 분석 리포트(MD 및 PDF) 생성", "getEtfAiReport.py", extra)

    # 🗓️ 대시보드 달력/기본 일자용 날짜 목록 자동 갱신
    update_available_dates_js()

    telegram_status_msg = "미실행 (옵션 --telegram 미사용)"
    git_status_msg = "미실행 (옵션 --push-git 미사용)"

    # 📲 텔레그램 알림 발송 옵션이 지정된 경우
    if args.telegram:
        print("\n" + "=" * 90)
        print("📲 [--telegram] 옵션 활성화: A+ 등급 핵심 주도주 텔레그램 알림 및 PDF 리포트 발송을 진행합니다...")
        print("=" * 90)
        success, tg_desc = send_telegram_notification(args.bot_token, args.chat_id, target_date=args.date, send_pdf=args.pdf)
        telegram_status_msg = f"{'성공' if success else '실패/경고'} ({tg_desc})"

    # 🚀 Git 커밋 및 Push 옵션이 지정된 경우
    if args.push_git:
        success, git_desc = run_git_auto_push(target_date=args.date)
        git_status_msg = f"{'성공' if success else '경고/실패'} ({git_desc})"

    total_elapsed = time.time() - total_start
    finish_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 90)
    print(f"🎉 [파이프라인 종료 시각: {finish_str}] 모든 파이프라인 단계 실행 완료!")
    print(f"⏱️  전체 소요시간: {total_elapsed:.1f}초")
    print(f"📁 실행 로그 파일: reports/log_{today_ymd}.txt")
    print(f"📲 텔레그램 알림: {telegram_status_msg}")
    print(f"🚀 Git Auto-Push: {git_status_msg}")
    print("=" * 90)

if __name__ == "__main__":
    main()
