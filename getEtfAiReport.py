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
    네이버 증권 API를 호출하여 가장 최근 주식 시장 마감 거래일자(YYYYMMDD)를 자동 감지합니다.
    """
    url = f"https://m.stock.naver.com/api/stock/{sample_code}/trend?page=1&pageSize=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
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

    md.append(f"### 🏭 주요 섹터/테마별 A+/A 주도주 수급 현황")
    md.append(f"| 대표 섹터/테마 | A+ 등급 | A 등급 | 전체 종목수 | 주요 A+ 주도주 |")
    md.append(f"| :--- | :---: | :---: | :---: | :--- |")
    for sec_name, total_sec in sector_counter.most_common():
        ap_cnt = sector_aplus.get(sec_name, 0)
        a_cnt = sector_a.get(sec_name, 0)
        top_names = [r['종목명'] for r in a_plus_list if r.get('섹터') == sec_name][:3]
        top_str = ", ".join(top_names) if top_names else "-"
        md.append(f"| **{sec_name}** | **{ap_cnt}개** | {a_cnt}개 | {total_sec}개 | {top_str} |")
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
    CSV 분석 데이터를 바탕으로 가독성 우수한 PDF 리포트(`reports/report_YYYYMMDD.pdf`)를 생성합니다.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
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

    a_plus_list = [r for r in rows if r.get('투자등급') == 'A+']
    a_list = [r for r in rows if r.get('투자등급') == 'A']
    b_list = [r for r in rows if r.get('투자등급') == 'B']
    c_list = [r for r in rows if r.get('투자등급') == 'C']

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'PdfTitle', parent=styles['Heading1'],
        fontName='AppleGothic', fontSize=15, leading=19,
        textColor=colors.HexColor('#0f172a'), spaceAfter=6
    )
    meta_style = ParagraphStyle(
        'PdfMeta', parent=styles['Normal'],
        fontName='AppleGothic', fontSize=8.5, leading=12,
        textColor=colors.HexColor('#475569'), spaceAfter=10
    )
    section_style = ParagraphStyle(
        'PdfSection', parent=styles['Heading2'],
        fontName='AppleGothic', fontSize=11, leading=15,
        textColor=colors.HexColor('#1e293b'), spaceBefore=10, spaceAfter=5
    )
    normal_style = ParagraphStyle(
        'PdfNormal', parent=styles['Normal'],
        fontName='AppleGothic', fontSize=8, leading=12,
        textColor=colors.HexColor('#334155')
    )
    th_style = ParagraphStyle(
        'PdfTH', parent=styles['Normal'],
        fontName='AppleGothic', fontSize=8, leading=10,
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

    story = []
    
    # Title & Header
    story.append(Paragraph('📊 ETF 주도주 수급 & 추세추종 AI 종합 분석 리포트', title_style))
    story.append(HRFlowable(width='100%', thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=8))
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_text = f"<b>분석 일자</b>: {date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} | <b>생성 일시</b>: {now_str} | <b>분석 종목</b>: 총 {total_count:,}개 주도주"
    story.append(Paragraph(meta_text, meta_style))

    # Section 1: Summary Table
    story.append(Paragraph('1. 📈 등급 분포 및 수급 현황 요약', section_style))
    summary_data = [
        [Paragraph('투자등급', th_style), Paragraph('종목 수', th_style), Paragraph('비율 (%)', th_style), Paragraph('주요 조건 기준', th_style)],
        [Paragraph('🔥 A+', td_bold), Paragraph(f'{len(a_plus_list):,}개', td_style), Paragraph(f'{len(a_plus_list)/total_count*100:.1f}%', td_style), Paragraph('쌍끌이(O) + 20일선위(O) + 정배열(O)', td_left)],
        [Paragraph('⭐ A', td_bold), Paragraph(f'{len(a_list):,}개', td_style), Paragraph(f'{len(a_list)/total_count*100:.1f}%', td_style), Paragraph('쌍끌이(O) + 20일선위(O)', td_left)],
        [Paragraph('🟡 B', td_style), Paragraph(f'{len(b_list):,}개', td_style), Paragraph(f'{len(b_list)/total_count*100:.1f}%', td_style), Paragraph('쌍끌이(O) 또는 20일선위(O) 중 1개 만족', td_left)],
        [Paragraph('⚪ C', td_style), Paragraph(f'{len(c_list):,}개', td_style), Paragraph(f'{len(c_list)/total_count*100:.1f}%', td_style), Paragraph('조건 미달', td_left)],
    ]
    t_sum = Table(summary_data, colWidths=[65, 65, 65, 335])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_sum)
    story.append(Spacer(1, 8))

    # Section 2: A+ Grade Table
    story.append(Paragraph(f'2. 🏆 A+ 등급 핵심 주도주 심층 분석 ({len(a_plus_list)}종목)', section_style))
    if a_plus_list:
        aplus_table_data = [
            [Paragraph('코드', th_style), Paragraph('종목명', th_style), Paragraph('섹터', th_style), Paragraph('현재가', th_style), Paragraph('외인연속', th_style), Paragraph('기관연속', th_style), Paragraph('외인보유율', th_style)]
        ]
        for r in a_plus_list:
            aplus_table_data.append([
                Paragraph(r.get('종목코드',''), td_style),
                Paragraph(r.get('종목명',''), td_bold),
                Paragraph(r.get('섹터','일반 주도주'), td_left),
                Paragraph(f"{r.get('현재가','')}원", td_style),
                Paragraph(f"{r.get('외국인연속매수(일)','')}일", td_style),
                Paragraph(f"{r.get('기관연속매수(일)','')}일", td_style),
                Paragraph(r.get('외국인보유율',''), td_style)
            ])
        t_ap = Table(aplus_table_data, colWidths=[50, 100, 120, 80, 60, 60, 60])
        t_ap.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f1f5f9')]),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_ap)
    else:
        story.append(Paragraph('현재 A+ 등급 조건 종목이 없습니다.', normal_style))
    story.append(Spacer(1, 8))

    # Section 3: A Grade Table (Top 15)
    story.append(Paragraph(f'3. ⭐ A 등급 주요 관찰 종목 (상위 15개 요약)', section_style))
    top_a = a_list[:15]
    if top_a:
        a_table_data = [
            [Paragraph('코드', th_style), Paragraph('종목명', th_style), Paragraph('섹터', th_style), Paragraph('현재가', th_style), Paragraph('쌍끌이', th_style), Paragraph('20일선위', th_style), Paragraph('외인연속', th_style), Paragraph('기관연속', th_style)]
        ]
        for r in top_a:
            a_table_data.append([
                Paragraph(r.get('종목코드',''), td_style),
                Paragraph(r.get('종목명',''), td_bold),
                Paragraph(r.get('섹터','일반 주도주'), td_left),
                Paragraph(f"{r.get('현재가','')}원", td_style),
                Paragraph(r.get('쌍끌이여부',''), td_style),
                Paragraph(r.get('20일선위',''), td_style),
                Paragraph(f"{r.get('외국인연속매수(일)','')}일", td_style),
                Paragraph(f"{r.get('기관연속매수(일)','')}일", td_style)
            ])
        t_a = Table(a_table_data, colWidths=[50, 100, 120, 80, 45, 45, 45, 45])
        t_a.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#334155')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0,0), (-1,-1), 3.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ]))
        story.append(t_a)
    else:
        story.append(Paragraph('A 등급 종목이 없습니다.', normal_style))
    story.append(Spacer(1, 8))

    # Section 4: Strategy
    story.append(Paragraph('4. 🎯 AI 추세추종 매매 실전 전략 가이드', section_style))
    strat_text = """
    • <b>피라미딩 분할 매수</b>: 1차(40%) 20일선 지지반등 → 2차(30%) +3%~+5% 수익 시 추매 → 3차(20%) 전고점 돌파 → 4차(10%) 불타기<br/>
    • <b>리스크 관리 규칙</b>: -3% 손절선 기계적 적용 | B/C 등급 하향 또는 20일선 이탈 시 수급 악화 판단 후 정리
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
