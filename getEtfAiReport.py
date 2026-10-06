#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 [5단계] AI 추세추종 종합 분석 마크다운 리포트 생성 프로그램 (getEtfAiReport.py)
================================================================================
1. 프로그램 역할:
   4단계에서 산출된 분석 결과 CSV(`reports/report_YYYYMMDD.csv`) 데이터를 바탕으로 
   누구나 한눈에 주도주 현황과 매매 전략을 파악할 수 있는 
   아주 예쁜 AI 종합 분석 마크다운 보고서(`reports/report_YYYYMMDD.md`)를 자동 생성합니다.

2. 입력 데이터:
   - CSV 파일: `reports/report_YYYYMMDD.csv` (4단계 실행 결과)

3. 출력 결과:
   - 마크다운 파일: `reports/report_YYYYMMDD.md` (예: `reports/report_20261002.md`)

4. 주요 작성 내용 (리포트에 담기는 내용):
   - 📈 **1. 등급 분포 및 수급 요약**: A+, A, B, C 등급별 종목 수 및 비율표
   - 🏆 **2. A+ 등급 심층 분석**: 최상위 정배열 대세상승주 6종목 집중 조명 및 투자 팁
   - ⭐ **3. A 등급 주요 관심주**: 수급과 20일선 위 조건이 검증된 핵심 종목 목록
   - 🔄 **4. 등급 상향/하향 변동**: 이전 거래일 대비 등급이 오르거나 내린 종목 분석
   - 🎯 **5. 추세추종 실전 전략**: 피라미딩(40%->30%->20%->10%) 매수법 및 -3% 손절칙 가이드
================================================================================
"""

import os                  # 파일 및 디렉토리 확인 라이브러리
import sys                 # 시스템 제어 라이브러리
import glob                # 폴더 내 파일 검색 라이브러리
import csv                 # CSV 파일 파싱 도구
import argparse            # 실행 옵션 파서
from datetime import datetime # 현재 날짜/시간 라이브러리

import urllib.request
import json

def get_latest_market_bizdate(sample_code="005930"):
    """
    네이버 증권 API를 호출하여 가장 최근 주식 시장 마감/거래일자(YYYYMMDD)를 자동 감지합니다.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    # 1) price API (일별 시세 거래일) 우선 감지
    url_price = f"https://m.stock.naver.com/api/stock/{sample_code}/price?page=1&pageSize=1"
    try:
        req = urllib.request.Request(url_price, headers=headers)
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            prices = data if isinstance(data, list) else data.get("result", [])
            if prices and isinstance(prices, list) and len(prices) > 0:
                traded_at = prices[0].get("localTradedAt", "").replace("-", "").strip()
                if traded_at and len(traded_at) == 8 and traded_at.isdigit():
                    return traded_at
    except Exception:
        pass

    # 2) trend API (수급 거래일) 차선 감지
    url_trend = f"https://m.stock.naver.com/api/stock/{sample_code}/trend?page=1&pageSize=1"
    try:
        req = urllib.request.Request(url_trend, headers=headers)
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            trends = data if isinstance(data, list) else data.get("result", [])
            if trends and isinstance(trends, list) and len(trends) > 0:
                bizdate = trends[0].get("bizdate", "").strip()
                if bizdate and len(bizdate) == 8 and bizdate.isdigit():
                    return bizdate
    except Exception:
        pass

    return datetime.now().strftime("%Y%m%d")

def find_target_csv(target_date=None):
    """
    분석 대상이 되는 CSV 파일 경로(`reports/report_YYYYMMDD.csv`)를 찾아내는 함수입니다.
    날짜를 직접 지정하지 않으면 가장 최근 마감 거래일(bizdate)의 CSV 파일을 자동으로 선택합니다.
    """
    anal_dir = "reports"
    if not os.path.exists(anal_dir):
        print(f"❌ '{anal_dir}' 폴더가 존재하지 않습니다.")
        return None

    # 지정 날짜가 없으면 네이버 API 기준 최신 장 마감 거래일자 자동 감지
    if not target_date:
        target_date = get_latest_market_bizdate()

    filename = f"report_{target_date}.csv"
    path = os.path.join(anal_dir, filename)
    if os.path.exists(path):
        return path

    # 해당 날짜의 파일이 없으면 `reports/` 폴더 내 가장 최근 파일 검색
    files = glob.glob(os.path.join(anal_dir, "report_*.csv"))
    if not files:
        print(f"❌ '{anal_dir}' 폴더 내에 report_YYYYMMDD.csv 파일이 없습니다.")
        return None

    files.sort(reverse=True)
    return files[0]

def generate_ai_report(csv_path):
    """
    4단계 분석 CSV 파일 데이터를 파싱하여 가독성 우수한 마크다운(.md) 보고서를 생성합니다.
    
    :param csv_path: 분석 CSV 파일 경로 (예: 'reports/report_20261002.csv')
    :return: True(성공), False(실패)
    """
    base_name = os.path.basename(csv_path)
    date_part = base_name.replace("report_", "").replace(".csv", "")
    md_path = os.path.join(os.path.dirname(csv_path), f"report_{date_part}.md")

    print(f"📖 CSV 데이터 읽기 중: {csv_path}")
    
    rows = []
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        print(f"❌ CSV 읽기 실패: {e}")
        return False

    total_count = len(rows)
    if total_count == 0:
        print("❌ CSV 파일에 데이터가 없습니다.")
        return False

    # 1. 투자등급별 데이터 분류
    a_plus_list = [r for r in rows if r['투자등급'] == 'A+']
    a_list = [r for r in rows if r['투자등급'] == 'A']
    b_list = [r for r in rows if r['투자등급'] == 'B']
    c_list = [r for r in rows if r['투자등급'] == 'C']

    # 2. 등급 변동(상향/하향/신규) 데이터 분류
    upgraded = [r for r in rows if '상향' in r.get('등급변동', '')]
    downgraded = [r for r in rows if '하향' in r.get('등급변동', '')]
    new_captured = [r for r in rows if 'NEW' in r.get('등급변동', '')]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 3. 마크다운 리포트 문맥 작성 시작
    md = []
    md.append(f"# 📊 ETF 주도주 수급 & 추세추종 AI 종합 분석 리포트")
    md.append(f"")
    md.append(f"- **분석 일자**: {date_part[:4]}년 {date_part[4:6]}월 {date_part[6:8]}일")
    md.append(f"- **생성 일시**: {now_str}")
    md.append(f"- **분석 대상 종목**: 총 {total_count:,}개 주도주")
    md.append(f"")
    
    md.append(f"> [!IMPORTANT]")
    md.append(f"> **추세추종 핵심 원칙**: 상승 추세(20일선 위) 및 수급(외인/기관 쌍끌이)이 검증된 **A+ 및 A 등급 종목** 중심 매매. 손절선 -3% 엄수 및 피라미딩(40% → 30% → 20% → 10%) 분할 매수 수립.")
    md.append(f"")

    # [섹션 1] 종합 시장 등급 요약 표
    md.append(f"## 1. 📈 등급 분포 및 수급 현황 요약")
    md.append(f"")
    md.append(f"| 투자등급 | 종목 수 | 비율 (%) | 주요 조건 기준 |")
    md.append(f"| :---: | :---: | :---: | :--- |")
    md.append(f"| 🔥 **A+** | **{len(a_plus_list):,}개** | {len(a_plus_list)/total_count*100:.1f}% | 쌍끌이(O) + 20일선위(O) + 정배열(O) (MA5≥20≥60≥120) |")
    md.append(f"| ⭐ **A** | **{len(a_list):,}개** | {len(a_list)/total_count*100:.1f}% | 쌍끌이(O) + 20일선위(O) |")
    md.append(f"| 🟡 **B** | **{len(b_list):,}개** | {len(b_list)/total_count*100:.1f}% | 쌍끌이(O) 또는 20일선위(O) 중 1가지 만족 |")
    md.append(f"| ⚪ **C** | **{len(c_list):,}개** | {len(c_list)/total_count*100:.1f}% | 조건을 만족하지 못함 (20일선 미달 등) |")
    md.append(f"")

    # [섹션 1-2] 주도 섹터별 수급 및 A+ 종목 분포 요약
    from collections import Counter
    sector_counter = Counter(r.get('섹터', '일반 주도주') for r in rows)
    sector_aplus = Counter(r.get('섹터', '일반 주도주') for r in a_plus_list)
    sector_a = Counter(r.get('섹터', '일반 주도주') for r in a_list)

    # 섹터 모멘텀 순위 계산 (A+ * 3.0 + A * 1.0)
    sorted_sectors = sorted(
        sector_counter.keys(),
        key=lambda s: ((sector_aplus.get(s, 0) * 3.0) + (sector_a.get(s, 0) * 1.0), sector_aplus.get(s, 0), sector_a.get(s, 0)),
        reverse=True
    )

    md.append(f"### 🏭 주요 섹터/테마별 A+/A 주도주 수급 현황 (모멘텀 순위)")
    md.append(f"| 순위 | 대표 섹터/테마 | A+ 등급 | A 등급 | 전체 종목수 | 주요 A+ 주도주 |")
    md.append(f"| :---: | :--- | :---: | :---: | :---: | :--- |")
    for idx, sec_name in enumerate(sorted_sectors, 1):
        total_sec = sector_counter.get(sec_name, 0)
        ap_cnt = sector_aplus.get(sec_name, 0)
        a_cnt = sector_a.get(sec_name, 0)
        top_names = [r['종목명'] for r in a_plus_list if r.get('섹터') == sec_name][:3]
        top_str = ", ".join(top_names) if top_names else "-"
        rank_badge = "🥇 1위" if idx == 1 else ("🥈 2위" if idx == 2 else ("🥉 3위" if idx == 3 else f"{idx}위"))
        md.append(f"| {rank_badge} | **{sec_name}** | **{ap_cnt}개** | {a_cnt}개 | {total_sec}개 | {top_str} |")
    md.append(f"")

    # 등급 변동 현황
    md.append(f"### 🔄 이전 거래일 대비 등급 변동 현황")
    if upgraded or downgraded:
        md.append(f"- ⬆️ **등급 상향 종목**: 총 **{len(upgraded)}개**")
        md.append(f"- ⬇️ **등급 하향 종목**: 총 **{len(downgraded)}개**")
    else:
        md.append(f"- ℹ️ 기준일 최초 분석 실행 (신규 포착 종목 총 **{len(new_captured)}개**)")
    md.append(f"")

    # [섹션 2] A+ 등급 종목 심층 분석
    md.append(f"## 2. 🏆 A+ 등급 핵심 주도주 심층 분석 ({len(a_plus_list)}종목)")
    md.append(f"A+ 등급은 **외국인/기관 동시 연속 순매수**, **20일 이동평균선 상회**, **5/20/60/120일선 완벽 정배열**을 갖춘 최상위 주도주입니다.")
    md.append(f"")

    if a_plus_list:
        md.append(f"| 종목코드 | 종목명 | 대표섹터 | 현재가 | 외국인연속 | 기관연속 | 外보유율 | 변동이유 | 상세페이지 |")
        md.append(f"| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :---: |")
        for r in a_plus_list:
            code = r['종목코드']
            name = r['종목명']
            sector = r.get('섹터', '일반 주도주')
            price = r['현재가']
            f_seq = f"{r['외국인연속매수(일)']}일"
            i_seq = f"{r['기관연속매수(일)']}일"
            f_rate = r['외국인보유율']
            reason = r['변동이유']
            link = f"[네이버증권]({r['상세페이지']})"
            md.append(f"| `{code}` | **{name}** | `{sector}` | {price}원 | {f_seq} | {i_seq} | {f_rate} | {reason} | {link} |")
        md.append(f"")
        
        md.append(f"### 💡 A+ 종목별 핵심 투자 팁")
        for r in a_plus_list:
            md.append(f"- **{r['종목명']} ({r['종목코드']}) - {r.get('섹터', '일반 주도주')}**:")
            md.append(f"  - 현재가 {r['현재가']}원 / MA5: {r['MA5']}원 / MA20: {r['MA20']}원")
            md.append(f"  - 외국인 {r['외국인연속매수(일)']}일, 기관 {r['기관연속매수(일)']}일 연속 순매수세 지속중.")
            md.append(f"  - 완전 정배열 상태로 눌림목 발생 시 1차 비중(40%) 진입 후보 1순위.")
    else:
        md.append(f"> 현재 A+ 등급 조건을 완벽히 충족하는 종목이 없습니다. 시장 관망 또는 A 등급 우량주에 주목하세요.")
    md.append(f"")

    # [섹션 3] A 등급 주요 관찰 종목
    md.append(f"## 3. ⭐ A 등급 주요 관찰 종목 (상위 15개 요약)")
    md.append(f"A 등급은 **쌍끌이 수급**과 **20일선 위** 조건을 확보한 정배열 직전/진행 중인 강력한 주도주 후보입니다.")
    md.append(f"")

    top_a = a_list[:15]
    if top_a:
        md.append(f"| 종목코드 | 종목명 | 대표섹터 | 현재가 | 쌍끌이 | 20일선위 | 정배열 | 외인연속 | 기관연속 | 상세링크 |")
        md.append(f"| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        for r in top_a:
            code = r['종목코드']
            name = r['종목명']
            sector = r.get('섹터', '일반 주도주')
            price = r['현재가']
            bi = r['쌍끌이여부']
            ma20 = r['20일선위']
            align = r['정배열여부']
            f_seq = f"{r['외국인연속매수(일)']}일"
            i_seq = f"{r['기관연속매수(일)']}일"
            link = f"[보기]({r['상세페이지']})"
            md.append(f"| `{code}` | {name} | `{sector}` | {price}원 | {bi} | {ma20} | {align} | {f_seq} | {i_seq} | {link} |")
        md.append(f"")
    else:
        md.append(f"> A 등급 종목이 없습니다.")
    md.append(f"")

    # [섹션 4] 등급 상향/하향 종목 하이라이트
    md.append(f"## 4. 🔄 등급 상향 / 하향 변동 종목 분석")
    md.append(f"")
    if upgraded:
        md.append(f"### ⬆️ 등급 상향 종목 ({len(upgraded)}개)")
        md.append(f"| 종목코드 | 종목명 | 현재가 | 등급변동 | 변동이유 |")
        md.append(f"| :---: | :--- | :---: | :---: | :--- |")
        for r in upgraded:
            md.append(f"| `{r['종목코드']}` | **{r['종목명']}** | {r['현재가']}원 | {r['등급변동']} | {r['변동이유']} |")
        md.append(f"")
    
    if downgraded:
        md.append(f"### ⬇️ 등급 하향 종목 ({len(downgraded)}개)")
        md.append(f"| 종목코드 | 종목명 | 현재가 | 등급변동 | 변동이유 |")
        md.append(f"| :---: | :--- | :---: | :---: | :--- |")
        for r in downgraded:
            md.append(f"| `{r['종목코드']}` | {r['종목명']} | {r['현재가']}원 | {r['등급변동']} | {r['변동이유']} |")
        md.append(f"")

    if not upgraded and not downgraded:
        md.append(f"> ℹ️ 이전 분석 대비 변동 내역이 없거나, 오늘 최초 신규 포착된 종목들입니다.")
        md.append(f"")

    # [섹션 5] 추세추종 매매 실전 가이드
    md.append(f"## 5. 🎯 AI 추세추종 매매 실전 전략 가이드")
    md.append(f"")
    md.append(f"### 1️⃣ 피라미딩(Pyramiding) 분할 매수 규칙")
    md.append(f"- **1차 매수 (40%)**: A+ 또는 A 등급 종목이 20일선 지지 후 반등할 때 진입.")
    md.append(f"- **2차 매수 (30%)**: 1차 매수가 대비 **+3%~+5%** 수익 발생 시 주도주 확신으로 추매.")
    md.append(f"- **3차 매수 (20%)**: 전고점 돌파 및 거래량 동반 시 추가 매수.")
    md.append(f"- **4차 매수 (10%)**: 완벽한 추세 분출 구간 불타기 마무리.")
    md.append(f"")
    md.append(f"### 2️⃣ 리스크 관리 & 손절 규칙")
    md.append(f"- **-3% 손절 원칙**: 매수가 대비 **-3%** 도달 시 즉시 기계적 손절매 시행.")
    md.append(f"- **등급 하향 시 대응**: A+/A 등급 종목이 **B 또는 C 등급으로 하향**되거나 **20일선을 이탈**하면 절반 이상 이익실현 또는 손절 정리를 권장합니다.")
    md.append(f"")
    md.append(f"> [!TIP]")
    md.append(f"> **리포트 활용법**: 본 마크다운 리포트는 매일 4단계 수급 분석 완료 후 5단계 AI 분석을 통해 자동으로 업데이트됩니다. 최신 `report_YYYYMMDD.md` 파일을 통해 주도주의 등급 변동 추이를 체크하세요.")

    # 마크다운 파일로 저장
    report_content = "\n".join(md)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"💾 [성공] AI 추세추종 분석 마크다운 리포트가 생성되었습니다: {md_path}")
    
    # PDF 리포트도 함께 생성
    generate_pdf_report(csv_path)
    return True

def generate_pdf_report(csv_path):
    """
    ============================================================================
    📌 [웹 대시보드 스타일] PDF 리포트 자동 생성 함수 (pdf/report_YYYYMMDD.pdf)
    ============================================================================
    1. 구성 요소 (요청사항 반영):
       - [표 1] 🔥 A+ 등급 핵심 주도주 (정배열 대세상승)
       - [표 2] 🚀 신규 승격 & A+ 등급 상향 종목
       - [표 3] 🔻 A+ 등급 하향 & 리스크 관리 주의 종목
       - [설명 1] 📈 등급 분포 및 수급 현황 산출 기준
       - [설명 2] 🎯 20일 이격도 & 과열 판정 가이드
       - [설명 3] 🛡️ AI 추세추종 매매 실전 전략 수칙
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        print("⚠️ ReportLab 라이브러리가 존재하지 않아 PDF 생성은 건너땁니다.")
        return False

    font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
    if not os.path.exists(font_path):
        font_path = "/Library/Fonts/Arial Unicode.ttf"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

    try:
        pdfmetrics.registerFont(TTFont('AppleGothic', font_path))
    except Exception as e:
        print(f"⚠️ PDF 폰트 등록 실패 ({e})")
        return False

    base_name = os.path.basename(csv_path)
    date_part = base_name.replace("report_", "").replace(".csv", "")
    project_root = os.path.dirname(os.path.abspath(__file__))
    pdf_dir = os.path.join(project_root, "pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"report_{date_part}.pdf")

    rows = []
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        print(f"❌ PDF 생성 중 CSV 읽기 실패: {e}")
        return False

    total_count = len(rows)
    if total_count == 0:
        return False

    # 1. 투자등급 및 변동 데이터 분류
    a_plus_list = [r for r in rows if r.get('투자등급') == 'A+']
    a_list = [r for r in rows if r.get('투자등급') == 'A']
    b_list = [r for r in rows if r.get('투자등급') == 'B']
    c_list = [r for r in rows if r.get('투자등급') == 'C']

    upgraded_list = [r for r in rows if r.get('투자등급') == 'A+' and ('상향' in r.get('등급변동', '') or 'NEW' in r.get('등급변동', ''))]
    downgraded_list = [r for r in rows if 'A+ ->' in r.get('등급변동', '') or 'A+ →' in r.get('등급변동', '') or ('하향' in r.get('등급변동', '') and 'A+' in r.get('변동이유', ''))]

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=25,
        leftMargin=25,
        topMargin=25,
        bottomMargin=25
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'PdfTitle', parent=styles['Heading1'],
        fontName='AppleGothic', fontSize=15, leading=19,
        textColor=colors.HexColor('#0f172a'), spaceAfter=4
    )
    meta_style = ParagraphStyle(
        'PdfMeta', parent=styles['Normal'],
        fontName='AppleGothic', fontSize=8.5, leading=12,
        textColor=colors.HexColor('#475569'), spaceAfter=8
    )
    section_style = ParagraphStyle(
        'PdfSection', parent=styles['Heading2'],
        fontName='AppleGothic', fontSize=11, leading=15,
        textColor=colors.HexColor('#1e293b'), spaceBefore=10, spaceAfter=4
    )
    section_desc = ParagraphStyle(
        'PdfSecDesc', parent=styles['Normal'],
        fontName='AppleGothic', fontSize=8, leading=11,
        textColor=colors.HexColor('#64748b'), spaceAfter=6
    )
    normal_style = ParagraphStyle(
        'PdfNormal', parent=styles['Normal'],
        fontName='AppleGothic', fontSize=8, leading=12,
        textColor=colors.HexColor('#334155')
    )
    th_style = ParagraphStyle(
        'PdfTH', parent=styles['Normal'],
        fontName='AppleGothic', fontSize=7.5, leading=10,
        textColor=colors.white, alignment=1
    )
    td_style = ParagraphStyle(
        'PdfTD', parent=styles['Normal'],
        fontName='AppleGothic', fontSize=7.5, leading=10,
        textColor=colors.HexColor('#1e293b'), alignment=1
    )
    td_bold = ParagraphStyle(
        'PdfTDBold', parent=styles['Normal'],
        fontName='AppleGothic', fontSize=7.5, leading=10,
        textColor=colors.HexColor('#0f172a'), alignment=1
    )
    td_left = ParagraphStyle(
        'PdfTDLeft', parent=styles['Normal'],
        fontName='AppleGothic', fontSize=7.5, leading=10,
        textColor=colors.HexColor('#1e293b'), alignment=0
    )
    td_red = ParagraphStyle(
        'PdfTDRed', parent=styles['Normal'],
        fontName='AppleGothic', fontSize=7.5, leading=10,
        textColor=colors.HexColor('#dc2626'), alignment=1
    )
    td_blue = ParagraphStyle(
        'PdfTDBlue', parent=styles['Normal'],
        fontName='AppleGothic', fontSize=7.5, leading=10,
        textColor=colors.HexColor('#2563eb'), alignment=1
    )

    story = []
    
    # Header Banner
    story.append(Paragraph('📊 ETF 주도주 수급 & 추세추종 AI 종합 분석 리포트', title_style))
    story.append(HRFlowable(width='100%', thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=6))
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_text = f"<b>분석 일자</b>: {date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} | <b>생성 일시</b>: {now_str} | <b>분석 종목</b>: 총 {total_count:,}개 | <b>A+등급</b>: {len(a_plus_list)}개 / <b>A등급</b>: {len(a_list)}개"
    story.append(Paragraph(meta_text, meta_style))

    # 12개 전체 주요 섹터/테마별 모멘텀 순위 2열 배너 추가
    from collections import Counter
    sec_counter_pdf = Counter(r.get('섹터', '일반 주도주') for r in rows)
    sec_aplus_pdf = Counter(r.get('섹터', '일반 주도주') for r in a_plus_list)
    sec_a_pdf = Counter(r.get('섹터', '일반 주도주') for r in a_list)
    sorted_sec_pdf = sorted(
        sec_counter_pdf.keys(),
        key=lambda s: ((sec_aplus_pdf.get(s, 0) * 3.0) + (sec_a_pdf.get(s, 0) * 1.0), sec_aplus_pdf.get(s, 0), sec_a_pdf.get(s, 0)),
        reverse=True
    )
    
    sec_banner_data = [
        [Paragraph('🔥 <b>[주요 섹터/테마별 주도주 분포 현황 (모멘텀 순위)]</b>', ParagraphStyle('SecBannerTitle', parent=styles['Normal'], fontName='AppleGothic', fontSize=8.5, leading=11, textColor=colors.HexColor('#1e3a8a'))), '']
    ]
    half = (len(sorted_sec_pdf) + 1) // 2
    col1 = sorted_sec_pdf[:half]
    col2 = sorted_sec_pdf[half:]
    
    for i in range(half):
        s1 = col1[i]
        s1_rank = "🥇 1위" if i == 0 else ("🥈 2위" if i == 1 else ("🥉 3위" if i == 2 else f"{i+1}위"))
        s1_text = f"• <b>{s1_rank}</b>: {s1} (A+ {sec_aplus_pdf.get(s1,0)}개 / A {sec_a_pdf.get(s1,0)}개)"
        
        if i < len(col2):
            s2 = col2[i]
            idx2 = half + i
            s2_rank = f"{idx2+1}위"
            s2_text = f"• <b>{s2_rank}</b>: {s2} (A+ {sec_aplus_pdf.get(s2,0)}개 / A {sec_a_pdf.get(s2,0)}개)"
        else:
            s2_text = ""
            
        sec_banner_data.append([
            Paragraph(s1_text, ParagraphStyle('SecB1', parent=styles['Normal'], fontName='AppleGothic', fontSize=7.5, leading=10, textColor=colors.HexColor('#1e293b'))),
            Paragraph(s2_text, ParagraphStyle('SecB2', parent=styles['Normal'], fontName='AppleGothic', fontSize=7.5, leading=10, textColor=colors.HexColor('#1e293b')))
        ])
        
    t_sec_banner = Table(sec_banner_data, colWidths=[270, 275])
    t_sec_banner.setStyle(TableStyle([
        ('SPAN', (0,0), (1,0)),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_sec_banner)
    story.append(Spacer(1, 6))

    th_sm = ParagraphStyle('PdfTHSm', parent=styles['Normal'], fontName='AppleGothic', fontSize=6.0, leading=7.5, textColor=colors.white, alignment=1)
    td_sm = ParagraphStyle('PdfTDSm', parent=styles['Normal'], fontName='AppleGothic', fontSize=6.0, leading=7.5, textColor=colors.HexColor('#1e293b'), alignment=1)
    td_bold_sm = ParagraphStyle('PdfTDBoldSm', parent=styles['Normal'], fontName='AppleGothic', fontSize=6.0, leading=7.5, textColor=colors.HexColor('#0f172a'), alignment=1)
    td_left_sm = ParagraphStyle('PdfTDLeftSm', parent=styles['Normal'], fontName='AppleGothic', fontSize=6.0, leading=7.5, textColor=colors.HexColor('#1e293b'), alignment=0)
    td_red_sm = ParagraphStyle('PdfTDRedSm', parent=styles['Normal'], fontName='AppleGothic', fontSize=6.0, leading=7.5, textColor=colors.HexColor('#dc2626'), alignment=1)
    td_blue_sm = ParagraphStyle('PdfTDBlueSm', parent=styles['Normal'], fontName='AppleGothic', fontSize=6.0, leading=7.5, textColor=colors.HexColor('#2563eb'), alignment=1)

    # =========================================================================
    # 📌 [표 1] 🔥 A+ 등급 핵심 주도주 (정배열 대세상승)
    # =========================================================================
    story.append(Paragraph(f'🔥 A+ 등급 핵심 주도주 (정배열 대세상승) - {len(a_plus_list)}종목', section_style))
    story.append(Paragraph('쌍끌이 수급 + 20일선 위 + 5/20/60/120일선 완전 정배열 검증 종목', section_desc))
    
    if a_plus_list:
        t1_data = [
            [
                Paragraph('코드', th_sm), Paragraph('종목명', th_sm), Paragraph('대표 섹터', th_sm),
                Paragraph('20일이격도', th_sm), Paragraph('과열여부', th_sm), Paragraph('추세단계', th_sm),
                Paragraph('권장진입가', th_sm), Paragraph('현재가', th_sm), Paragraph('등락률', th_sm),
                Paragraph('쌍끌이', th_sm), Paragraph('외인연속', th_sm), Paragraph('기관연속', th_sm),
                Paragraph('20일선위', th_sm), Paragraph('정배열', th_sm)
            ]
        ]
        for r in a_plus_list:
            chg_val = r.get('등락률', '')
            c_style = td_red_sm if '+' in chg_val else (td_blue_sm if '-' in chg_val else td_sm)
            t1_data.append([
                Paragraph(r.get('종목코드',''), td_sm),
                Paragraph(r.get('종목명',''), td_bold_sm),
                Paragraph(r.get('섹터','일반 주도주'), td_left_sm),
                Paragraph(r.get('20일이격도','100.0%'), td_sm),
                Paragraph(r.get('과열여부','적정(안전)'), td_sm),
                Paragraph(r.get('추세단계','정배열가속(A+)'), td_sm),
                Paragraph(r.get('추천매수가',''), td_sm),
                Paragraph(f"{r.get('현재가','')}원", td_sm),
                Paragraph(chg_val, c_style),
                Paragraph(r.get('쌍끌이여부',''), td_sm),
                Paragraph(f"{r.get('외국인연속매수(일)','')}일", td_sm),
                Paragraph(f"{r.get('기관연속매수(일)','')}일", td_sm),
                Paragraph(r.get('20일선위','O'), td_sm),
                Paragraph(r.get('정배열여부','O'), td_sm)
            ])
        t1 = Table(t1_data, colWidths=[36, 62, 62, 38, 42, 48, 60, 44, 36, 25, 24, 24, 22, 22])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f1f5f9')]),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(t1)
    else:
        story.append(Paragraph('ℹ️ 오늘 A+ 등급 조건(쌍끌이+20일선위+정배열)을 완벽히 충족하는 종목이 없습니다.', normal_style))
    
    story.append(Spacer(1, 10))

    # =========================================================================
    # 📌 [표 2] 🚀 신규 승격 & A+ 등급 상향 종목
    # =========================================================================
    story.append(Paragraph(f'🚀 신규 승격 & A+ 등급 상향 종목 - {len(upgraded_list)}종목', section_style))
    story.append(Paragraph('이전 거래일 대비 수급/차트 조건 개선으로 A+ 등급으로 승격되었거나 신규 포착된 최상위 주도주', section_desc))
    
    if upgraded_list:
        t2_data = [
            [Paragraph('코드', th_style), Paragraph('종목명', th_style), Paragraph('대표 섹터', th_style), Paragraph('등급변동', th_style), Paragraph('변동이유', th_style), Paragraph('현재가', th_style), Paragraph('등락률', th_style), Paragraph('쌍끌이', th_style), Paragraph('20일선위', th_style)]
        ]
        for r in upgraded_list:
            chg_val = r.get('등락률', '')
            c_style = td_red if '+' in chg_val else (td_blue if '-' in chg_val else td_style)
            t2_data.append([
                Paragraph(r.get('종목코드',''), td_style),
                Paragraph(r.get('종목명',''), td_bold),
                Paragraph(r.get('섹터','일반 주도주'), td_left),
                Paragraph(r.get('등급변동',''), td_bold),
                Paragraph(r.get('변동이유',''), td_left),
                Paragraph(f"{r.get('현재가','')}원", td_style),
                Paragraph(chg_val, c_style),
                Paragraph(r.get('쌍끌이여부',''), td_style),
                Paragraph(r.get('20일선위',''), td_style)
            ])
        t2 = Table(t2_data, colWidths=[45, 80, 85, 75, 95, 55, 45, 33, 32])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0369a1')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0f9ff')]),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t2)
    else:
        story.append(Paragraph('ℹ️ 오늘 신규 승격 또는 A+ 등급으로 상향된 종목이 없습니다.', normal_style))

    story.append(Spacer(1, 10))

    # =========================================================================
    # 📌 [표 3] 🔻 A+ 등급 하향 & 리스크 관리 주의 종목
    # =========================================================================
    story.append(Paragraph(f'🔻 A+ 등급 하향 & 리스크 관리 주의 종목 - {len(downgraded_list)}종목', section_style))
    story.append(Paragraph('이전 거래일 대비 수급 약화 또는 정배열 이탈로 등급이 하향 조정된 주의 필요 종목', section_desc))
    
    if downgraded_list:
        t3_data = [
            [Paragraph('코드', th_style), Paragraph('종목명', th_style), Paragraph('대표 섹터', th_style), Paragraph('등급변동', th_style), Paragraph('변동이유', th_style), Paragraph('현재가', th_style), Paragraph('등락률', th_style), Paragraph('쌍끌이', th_style), Paragraph('20일선위', th_style)]
        ]
        for r in downgraded_list:
            chg_val = r.get('등락률', '')
            c_style = td_red if '+' in chg_val else (td_blue if '-' in chg_val else td_style)
            t3_data.append([
                Paragraph(r.get('종목코드',''), td_style),
                Paragraph(r.get('종목명',''), td_bold),
                Paragraph(r.get('섹터','일반 주도주'), td_left),
                Paragraph(r.get('등급변동',''), td_bold),
                Paragraph(r.get('변동이유',''), td_left),
                Paragraph(f"{r.get('현재가','')}원", td_style),
                Paragraph(chg_val, c_style),
                Paragraph(r.get('쌍끌이여부',''), td_style),
                Paragraph(r.get('20일선위',''), td_style)
            ])
        t3 = Table(t3_data, colWidths=[45, 85, 95, 75, 90, 60, 50, 45, 45])
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#991b1b')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#fef2f2')]),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t3)
    else:
        story.append(Paragraph('ℹ️ 오늘 등급이 하향 조정된 리스크 주의 종목이 없습니다. (수급 유지중)', normal_style))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=10))

    # =========================================================================
    # 📌 [설명 섹션] 등급분포 및 수급현황 + 20일 이격도 설명
    # =========================================================================
    story.append(Paragraph('📘 주도주 수급 분석 및 추세 판단 가이드 (설명)', section_style))
    
    # 1) 등급분포 및 수급현황
    story.append(Paragraph('1. 등급 분포 및 수급 현황 산출 기준', ParagraphStyle('SubSec', parent=styles['Heading3'], fontName='AppleGothic', fontSize=9.5, leading=13, textColor=colors.HexColor('#0f172a'), spaceBefore=4, spaceAfter=3)))
    
    g_data = [
        [Paragraph('투자등급', th_style), Paragraph('종목 수', th_style), Paragraph('비율 (%)', th_style), Paragraph('주요 수급 및 차트 정배열 조건 기준', th_style)],
        [Paragraph('🔥 A+', td_bold), Paragraph(f'{len(a_plus_list):,}개', td_style), Paragraph(f'{len(a_plus_list)/total_count*100:.1f}%', td_style), Paragraph('쌍끌이(O) + 20일선위(O) + 5/20/60/120일선 완벽 정배열(O)', td_left)],
        [Paragraph('⭐ A', td_bold), Paragraph(f'{len(a_list):,}개', td_style), Paragraph(f'{len(a_list)/total_count*100:.1f}%', td_style), Paragraph('쌍끌이(O) + 20일선위(O) (정배열 진행 중 수급주)', td_left)],
        [Paragraph('🟡 B', td_style), Paragraph(f'{len(b_list):,}개', td_style), Paragraph(f'{len(b_list)/total_count*100:.1f}%', td_style), Paragraph('쌍끌이(O) 또는 20일선위(O) 중 1가지 만족 (관심주)', td_left)],
        [Paragraph('⚪ C', td_style), Paragraph(f'{len(c_list):,}개', td_style), Paragraph(f'{len(c_list)/total_count*100:.1f}%', td_style), Paragraph('조건 미달 (20일선 이하 및 수급 미흡 종목)', td_left)],
    ]
    t_g = Table(g_data, colWidths=[60, 60, 60, 365])
    t_g.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_g)
    story.append(Spacer(1, 8))

    # 2) 20일 이격도 설명
    story.append(Paragraph('2. 20일 이격도 & 과열 판정 가이드', ParagraphStyle('SubSec2', parent=styles['Heading3'], fontName='AppleGothic', fontSize=9.5, leading=13, textColor=colors.HexColor('#0f172a'), spaceBefore=4, spaceAfter=3)))
    
    disparity_text = """
    • <b>🟢 적정 (97% ~ 108%)</b>: 20일 이동평균선 부근 안심 1차 진입 적기 (추세추종 매수 권장 구간)<br/>
    • <b>🟡 상승과열 (108% ~ 115%)</b>: 단기 상승 폭 확대 구간. 신규 추격 매수 자제 및 본전 스탑로스 설정<br/>
    • <b>🔴 단기과열 (115% 이상)</b>: 🚨 <b>추가 매수 및 불타기 절대 금지!</b> (단기 차익실현 및 이익 확보 권장)<br/>
    • <b>🔵 이격과도 (&lt; 97%)</b>: 20일 이동평균선 이탈 구간 (관망 및 비중 축소 대응)
    """
    story.append(Paragraph(disparity_text, normal_style))
    story.append(Spacer(1, 8))

    # 3) 실전 매매 수칙
    story.append(Paragraph('3. AI 추세추종 매매 실전 전략 수칙', ParagraphStyle('SubSec3', parent=styles['Heading3'], fontName='AppleGothic', fontSize=9.5, leading=13, textColor=colors.HexColor('#0f172a'), spaceBefore=4, spaceAfter=3)))
    strat_text = """
    • <b>피라미딩(Pyramiding) 분할 매수</b>: 1차(40%) 20일선 반등 → 2차(30%) +3%~+5% 수익 시 추매 → 3차(20%) 전고점 돌파 → 4차(10%) 불타기<br/>
    • <b>리스크 관리 & 손절 원칙</b>: 매수가 대비 <b>-3% 손절선 기계적 적용</b> | B/C 등급 하향 또는 20일선 이탈 시 수급 악화 판단 후 정량 대응
    """
    story.append(Paragraph(strat_text, normal_style))

    try:
        doc.build(story)
        print(f"💾 [성공] AI 추세추종 분석 PDF 리포트가 생성되었습니다: {pdf_path}")
        return True
    except Exception as e:
        print(f"❌ PDF 생성 실패: {e}")
        return False

def main():
    """
    [5단계] AI 추세추종 분석 리포트 생성기 메인 함수입니다.
    """
    parser = argparse.ArgumentParser(description="[5단계] ETF 주도주 AI 추세추종 분석 마크다운 리포트 생성기")
    parser.add_argument("--date", type=str, help="분석 대상 날짜 (YYYYMMDD 형식, 예: 20261003)")
    parser.add_argument("--pdf", action="store_true", help="PDF 리포트도 함께 생성합니다.")
    args = parser.parse_args()

    # 대상 CSV 파일 찾기
    target_csv = find_target_csv(args.date)
    if not target_csv:
        sys.exit(1)

    # 리포트 생성 실행
    success = generate_ai_report(target_csv)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
