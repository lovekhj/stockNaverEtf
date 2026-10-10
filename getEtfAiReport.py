#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 [5단계] 추세추종 분석 리포트(마크다운·PDF) 생성 프로그램 (getEtfAiReport.py)
================================================================================
1. 프로그램 역할:
   4단계에서 산출된 분석 결과 CSV(`reports/report_YYYYMMDD.csv`)로
   마크다운 리포트(`reports/report_YYYYMMDD.md`)와 PDF 리포트(`pdf/report_YYYYMMDD.pdf`)를 만듭니다.

2. 입력 데이터:
   - CSV 파일: `reports/report_YYYYMMDD.csv` (4단계 실행 결과)

3. 리포트에 담기는 내용:
   - 1. 매수신호 A 종목 (강한 마감 + 추세 통과)
   - 2. 섹터 순위 (통과 종목 수가 많은 순서)
   - 3. 주도주 (순위가 높은 섹터의 통과 종목, 3개월 상승률 순)
   - 4. 매매 규칙 안내 (검증 중인 후보 규칙과 한계)

4. 주의:
   - 섹터 순위와 주도주 기준은 대시보드(app.js)와 같아야 합니다.
   - 검증 중인 기준이며 매수·매도 추천이 아닙니다.
================================================================================
"""

import os                  # 파일 및 디렉토리 확인 라이브러리
import sys                 # 시스템 제어 라이브러리
import glob                # 폴더 내 파일 검색 라이브러리
import csv                 # CSV 파일 파싱 도구
import argparse            # 실행 옵션 파서
import statistics          # 중앙값 계산
from datetime import datetime # 현재 날짜/시간 라이브러리

import urllib.request
import json

LEADER_SECTORS = 4   # 리포트에 싣는 주도주: 순위가 높은 섹터 수 (대시보드 주도주 화면의 기본값과 같다)
LEADER_STOCKS = 5    # 주도주: 섹터당 종목 수

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

def parse_percent(text):
    """
    "+12.3%" 같은 글자를 숫자로 바꿉니다. 바꿀 수 없으면 None
    """
    try:
        return float(str(text).replace("%", "").replace(",", ""))
    except ValueError:
        return None

def has_sector_stats(rows):
    """
    섹터 순위에 쓰는 추세통과 열이 있는 리포트인지 돌려줍니다. (2026-10-10 이전에 만든 CSV에는 없다)
    """
    return any(r.get('추세통과') in ('O', 'X') for r in rows)

def rank_sectors(rows):
    """
    섹터 순위를 매깁니다. 통과 종목 수가 많은 순서, 같으면 통과 비율이 높은 순서입니다.
    (대시보드 app.js 의 buildSectorRanking 과 같은 기준)

    :return: [{"섹터", "종목수", "통과", "통과비율", "3개월중앙값"(통과 종목이 없으면 None), "신호"}, ...]
    """
    sectors = {}
    for r in rows:
        sec = sectors.setdefault(r.get('섹터', '-'), {"섹터": r.get('섹터', '-'), "종목수": 0, "수익률": [], "신호": 0})
        sec["종목수"] += 1
        if r.get('추세통과') == 'O':
            sec["수익률"].append(parse_percent(r.get('3개월수익률')) or 0.0)
            if r.get('강한마감') == 'O':
                sec["신호"] += 1

    ranking = []
    for sec in sectors.values():
        returns = sec.pop("수익률")
        sec["통과"] = len(returns)
        sec["통과비율"] = len(returns) / sec["종목수"]
        sec["3개월중앙값"] = statistics.median(returns) if returns else None
        ranking.append(sec)
    ranking.sort(key=lambda sec: (-sec["통과"], -sec["통과비율"], sec["섹터"]))
    return ranking

def pick_leaders(rows, sector, limit=LEADER_STOCKS):
    """
    한 섹터의 주도주(통과 종목 중 3개월 상승률이 큰 순서)를 돌려줍니다.
    """
    passed = [r for r in rows if r.get('섹터') == sector and r.get('추세통과') == 'O']
    passed.sort(key=lambda r: parse_percent(r.get('3개월수익률')) or 0.0, reverse=True)
    return passed[:limit]

def read_report_rows(csv_path):
    """
    4단계 분석 CSV를 읽어 행 리스트로 돌려줍니다. 읽지 못하면 빈 리스트
    """
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"❌ CSV 읽기 실패: {e}")
        return []

def generate_ai_report(csv_path):
    """
    4단계 분석 CSV 파일 데이터를 파싱하여 마크다운(.md) 보고서를 생성합니다.
    
    :param csv_path: 분석 CSV 파일 경로 (예: 'reports/report_20261002.csv')
    :return: True(성공), False(실패)
    """
    base_name = os.path.basename(csv_path)
    date_part = base_name.replace("report_", "").replace(".csv", "")
    md_path = os.path.join(os.path.dirname(csv_path), f"report_{date_part}.md")

    print(f"📖 CSV 데이터 읽기 중: {csv_path}")
    rows = read_report_rows(csv_path)
    total_count = len(rows)
    if total_count == 0:
        print("❌ CSV 파일에 데이터가 없습니다.")
        return False

    # 매수신호 A 종목 (매수신호 열이 없는 예전 CSV에서는 빈 목록)
    signal_list = [r for r in rows if r.get('매수신호', '').startswith('A')]
    ranking = rank_sectors(rows) if has_sector_stats(rows) else []

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = []
    md.append(f"# 📊 ETF 주도주 섹터 순위 & 추세추종 리포트")
    md.append(f"")
    md.append(f"- **분석 일자**: {date_part[:4]}년 {date_part[4:6]}월 {date_part[6:8]}일")
    md.append(f"- **생성 일시**: {now_str}")
    md.append(f"- **분석 대상 종목**: 총 {total_count:,}개")
    md.append(f"- **데이터**: 네이버 증권 일봉(수정주가), 장 마감 후 확정치")
    md.append(f"")
    md.append(f"> [!IMPORTANT]")
    md.append(f"> 섹터 순위와 주도주는 \"무엇을 볼지\", 매수신호는 \"언제 살지\"를 봅니다. 검증 중인 기준이며 매수·매도 추천이 아닙니다.")
    md.append(f"")

    # [섹션 1] 매수신호 A 종목 (강한 마감 + 추세 통과)
    md.append(f"## 1. 🎯 매수신호 A 종목 ({len(signal_list)}종목)")
    md.append(f"**강한 마감**(+3% 이상, 거래량 1.5배 이상)과 **추세 통과**(종가 > 60일선, 60일선 상승, 1년 최고 종가의 -15% 이내)를 함께 채운 종목입니다. 기준일 종가 매수 기준입니다.")
    md.append(f"")
    if signal_list:
        md.append(f"| 종목코드 | 종목명 | 시장 | 섹터 | 현재가 | 등락률 | 3개월 | 고점 대비 | 차트 꼬리 | 판정 사유 | 상세페이지 |")
        md.append(f"| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :---: |")
        for r in signal_list:
            md.append(f"| `{r['종목코드']}` | **{r['종목명']}** | {r.get('시장', '-')} | `{r.get('섹터', '-')}` | {r['현재가']}원 | {r.get('등락률', '-')} | {r.get('3개월수익률', '-')} | {r.get('고점대비', '-')} | {r.get('차트꼬리', '') or '-'} | {r.get('매수신호사유', '')} | [네이버증권]({r['상세페이지']}) |")
    else:
        md.append(f"> 기준일에 매수신호 A 종목이 없습니다.")
    md.append(f"")

    # [섹션 2] 섹터 순위
    md.append(f"## 2. 🏭 섹터 순위")
    md.append(f"**통과** = 종가가 60일선 위, 60일선 상승, 1년 최고 종가의 -15% 이내. 통과 종목이 많은 섹터가 위에 옵니다.")
    md.append(f"")
    if ranking:
        md.append(f"| 순위 | 섹터 | 통과 | 종목 수 | 통과 비율 | 통과 종목 3개월 | ★ 오늘 신호 |")
        md.append(f"| :---: | :--- | :---: | :---: | :---: | :---: | :---: |")
        for idx, sec in enumerate(ranking, 1):
            median = f"{sec['3개월중앙값']:+.1f}%" if sec['3개월중앙값'] is not None else "-"
            signals = f"★ {sec['신호']}" if sec['신호'] else "-"
            md.append(f"| {idx} | **{sec['섹터']}** | **{sec['통과']}** | {sec['종목수']} | {sec['통과비율'] * 100:.0f}% | {median} | {signals} |")
    else:
        md.append(f"> 이 날짜의 분석 파일에는 섹터 통계가 없습니다.")
    md.append(f"")

    # [섹션 3] 주도주
    md.append(f"## 3. 👑 주도주 (섹터 상위 {LEADER_SECTORS}개, 섹터당 {LEADER_STOCKS}종목)")
    md.append(f"순위가 높은 섹터의 통과 종목을 3개월(60거래일) 상승률이 큰 순서로 보여 줍니다. ★ = 기준일 강한 마감.")
    md.append(f"")
    leader_sectors = [sec for sec in ranking if sec['통과'] > 0][:LEADER_SECTORS]
    for idx, sec in enumerate(leader_sectors, 1):
        md.append(f"### {idx}위 {sec['섹터']} (통과 {sec['통과']}개 / 전체 {sec['종목수']}개)")
        md.append(f"| 순위 | 종목코드 | 종목명 | 시장 | 3개월 | 고점 대비 | 오늘 신호 | 현재가 | 등락률 | 매수신호 | 상세페이지 |")
        md.append(f"| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        for rank, r in enumerate(pick_leaders(rows, sec['섹터']), 1):
            star = "★" if r.get('강한마감') == 'O' else "-"
            md.append(f"| {rank} | `{r['종목코드']}` | **{r['종목명']}** | {r.get('시장', '-')} | {r.get('3개월수익률', '-')} | {r.get('고점대비', '-')} | {star} | {r['현재가']}원 | {r.get('등락률', '-')} | {r.get('매수신호', '-') or '-'} | [네이버증권]({r['상세페이지']}) |")
        md.append(f"")
    if not leader_sectors:
        md.append(f"> 통과 종목이 있는 섹터가 없습니다.")
        md.append(f"")

    # [섹션 4] 매매 규칙 안내
    md.append(f"## 4. ⚖️ 매매 규칙 (검증 중인 후보)")
    md.append(f"")
    md.append(f"| 구분 | 내용 |")
    md.append(f"| :--- | :--- |")
    md.append(f"| 매수 | 매수신호 A인 날의 종가에 한 번 매수 |")
    md.append(f"| 강한 마감 | 당일 등락률 +3% 이상, 거래량이 직전 20거래일 평균의 1.5배 이상 |")
    md.append(f"| 매도 | 종가가 보유 중 최고 종가의 -5% 이하이면 그날 종가에 전량 |")
    md.append(f"| 추세 통과 | 종가 > 60일선, 60일선 상승, 종가가 1년 최고 종가의 -15% 이내 |")
    md.append(f"")
    md.append(f"- 매수신호 규칙은 과거 약 4년(2022-10 ~ 2026-10) 백테스트에서 승률 약 38%, 손익비 약 2.6, 매매당 평균 +2.2%(비용 0.25% 차감)였습니다. 세 번 중 두 번 가까이는 손절로 끝납니다.")
    md.append(f"- 강세장 구간만 검증했고 하락장은 검증하지 않았습니다. 종가에 정확히 체결된다고 가정한 숫자입니다.")
    md.append(f"- 매수신호는 기준일 종가 매수를 뜻합니다. 이 리포트는 장 마감 후에 만들어지므로, 리포트를 보고 다음 날 사면 다른 매매입니다.")
    md.append(f"- 섹터 순위와 주도주의 줄 세우기(통과 종목 수, 3개월 상승률 순)는 과거 데이터로 검증하지 않았습니다.")
    md.append(f"")
    md.append(f"> [!WARNING]")
    md.append(f"> 검증 중인 후보 규칙이며 과거 데이터 분석입니다. 매수·매도 추천이 아닙니다. 데이터: 네이버 증권, 장 마감 후 확정치.")

    # 마크다운 파일로 저장
    report_content = "\n".join(md)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"💾 [성공] 추세추종 분석 마크다운 리포트가 생성되었습니다: {md_path}")
    
    # PDF 리포트도 함께 생성
    generate_pdf_report(csv_path)
    return True

def generate_pdf_report(csv_path):
    """
    PDF 리포트(pdf/report_YYYYMMDD.pdf)를 만듭니다. 내용은 마크다운 리포트와 같습니다.
    (매수신호 A 종목, 섹터 순위, 주도주, 매매 규칙 안내)
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

    rows = read_report_rows(csv_path)
    total_count = len(rows)
    if total_count == 0:
        return False

    signal_list = [r for r in rows if r.get('매수신호', '').startswith('A')]
    ranking = rank_sectors(rows) if has_sector_stats(rows) else []
    leader_sectors = [sec for sec in ranking if sec['통과'] > 0][:LEADER_SECTORS]

    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    styles = getSampleStyleSheet()

    def style(name, parent='Normal', size=7, leading=9.5, color='#1e293b', align=0, **extra):
        return ParagraphStyle(name, parent=styles[parent], fontName='AppleGothic', fontSize=size, leading=leading,
                              textColor=colors.HexColor(color), alignment=align, **extra)

    title_style = style('PdfTitle', 'Heading1', 15, 19, '#0f172a', spaceAfter=4)
    meta_style = style('PdfMeta', size=8.5, leading=12, color='#475569', spaceAfter=8)
    section_style = style('PdfSection', 'Heading2', 11, 15, '#1e293b', spaceBefore=10, spaceAfter=4)
    section_desc = style('PdfSecDesc', size=8, leading=11, color='#64748b', spaceAfter=6)
    normal_style = style('PdfNormal', size=8, leading=12, color='#334155')
    th = style('PdfTH', color='#ffffff', align=1)
    td = style('PdfTD', align=1)
    td_left = style('PdfTDLeft')
    td_red = style('PdfTDRed', color='#dc2626', align=1)
    td_blue = style('PdfTDBlue', color='#2563eb', align=1)

    def signed(text):
        """등락률·상승률 글자를 부호에 따라 빨강/파랑 칸으로 만든다"""
        text = text or '-'
        return Paragraph(text, td_red if '+' in text else (td_blue if '-' in text and text != '-' else td))

    def build_table(header, body, widths, header_color, stripe_color):
        table = Table([[Paragraph(h, th) for h in header]] + body, colWidths=widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor(header_color)),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor(stripe_color)]),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ]))
        return table

    story = []
    story.append(Paragraph('ETF 주도주 섹터 순위 & 추세추종 리포트', title_style))
    story.append(HRFlowable(width='100%', thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=6))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_text = (f"<b>분석 일자</b>: {date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} | <b>생성 일시</b>: {now_str} | "
                 f"<b>분석 종목</b>: 총 {total_count:,}개 | <b>매수신호 A</b>: {len(signal_list)}개 | 네이버 증권 일봉(수정주가), 장 마감 후 확정치")
    story.append(Paragraph(meta_text, meta_style))

    # [표 1] 매수신호 A 종목
    story.append(Paragraph(f'1. 매수신호 A 종목 (강한 마감 + 추세 통과) - {len(signal_list)}종목', section_style))
    story.append(Paragraph('당일 +3% 이상, 거래량 1.5배 이상 + 추세 통과(60일선 위, 60일선 상승, 1년 최고 종가의 -15% 이내). 기준일 종가 매수 기준이며 검증 중인 후보 규칙입니다. 매수·매도 추천이 아닙니다.', section_desc))
    if signal_list:
        body = [[
            Paragraph(r.get('종목코드', ''), td), Paragraph(r.get('종목명', ''), td_left), Paragraph(r.get('시장', '-'), td),
            Paragraph(r.get('섹터', '-'), td_left), Paragraph(f"{r.get('현재가', '')}원", td), signed(r.get('등락률')),
            signed(r.get('3개월수익률')), Paragraph(r.get('고점대비', '-'), td), Paragraph(r.get('차트꼬리', '') or '-', td),
            Paragraph(r.get('매수신호사유', ''), td_left)
        ] for r in signal_list]
        story.append(build_table(['코드', '종목명', '시장', '섹터', '현재가', '등락률', '3개월', '고점 대비', '차트 꼬리', '판정 사유'],
                                 body, [36, 82, 32, 80, 48, 40, 42, 40, 50, 95], '#b91c1c', '#fef2f2'))
    else:
        story.append(Paragraph('기준일에 매수신호 A 종목이 없습니다.', section_desc))
    story.append(Spacer(1, 8))

    # [표 2] 섹터 순위
    story.append(Paragraph('2. 섹터 순위', section_style))
    story.append(Paragraph('통과 = 종가가 60일선 위, 60일선 상승, 1년 최고 종가의 -15% 이내. 통과 종목이 많은 섹터가 위에 옵니다. 과거 데이터로 검증하지 않은 기준입니다.', section_desc))
    if ranking:
        body = [[
            Paragraph(str(idx), td), Paragraph(sec['섹터'], td_left), Paragraph(str(sec['통과']), td), Paragraph(str(sec['종목수']), td),
            Paragraph(f"{sec['통과비율'] * 100:.0f}%", td),
            signed(f"{sec['3개월중앙값']:+.1f}%" if sec['3개월중앙값'] is not None else '-'),
            Paragraph(f"★ {sec['신호']}" if sec['신호'] else '-', td)
        ] for idx, sec in enumerate(ranking, 1)]
        story.append(build_table(['순위', '섹터', '통과', '종목 수', '통과 비율', '통과 종목 3개월', '★ 오늘 신호'],
                                 body, [40, 165, 60, 60, 70, 85, 65], '#1e3a8a', '#f1f5f9'))
    else:
        story.append(Paragraph('이 날짜의 분석 파일에는 섹터 통계가 없습니다.', section_desc))
    story.append(Spacer(1, 8))

    # [표 3] 주도주
    story.append(Paragraph(f'3. 주도주 (섹터 상위 {LEADER_SECTORS}개, 섹터당 {LEADER_STOCKS}종목)', section_style))
    story.append(Paragraph('순위가 높은 섹터의 통과 종목을 3개월(60거래일) 상승률이 큰 순서로 보여 줍니다. ★ = 기준일 강한 마감.', section_desc))
    body = []
    for idx, sec in enumerate(leader_sectors, 1):
        for rank, r in enumerate(pick_leaders(rows, sec['섹터']), 1):
            body.append([
                Paragraph(f"{idx}위 {sec['섹터']}", td_left), Paragraph(str(rank), td), Paragraph(r.get('종목코드', ''), td),
                Paragraph(r.get('종목명', ''), td_left), Paragraph(r.get('시장', '-'), td), signed(r.get('3개월수익률')),
                Paragraph(r.get('고점대비', '-'), td), Paragraph('★' if r.get('강한마감') == 'O' else '-', td),
                Paragraph(f"{r.get('현재가', '')}원", td), signed(r.get('등락률')), Paragraph(r.get('매수신호', '-') or '-', td)
            ])
    if body:
        story.append(build_table(['섹터', '순위', '코드', '종목명', '시장', '3개월', '고점 대비', '신호', '현재가', '등락률', '매수신호'],
                                 body, [98, 26, 38, 84, 32, 46, 44, 26, 50, 42, 59], '#0369a1', '#f0f9ff'))
    else:
        story.append(Paragraph('통과 종목이 있는 섹터가 없습니다.', section_desc))

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=8))

    # [설명] 매매 규칙
    story.append(Paragraph('4. 매매 규칙 (검증 중인 후보)', section_style))
    rule_text = """
    • <b>매수</b>: 매수신호 A(강한 마감 + 추세 통과)인 날의 종가에 한 번 매수<br/>
    • <b>매도</b>: 종가가 보유 중 최고 종가의 -5% 이하이면 그날 종가에 전량<br/>
    • <b>검증</b>: 2022-10 ~ 2026-10 백테스트에서 승률 약 38%, 손익비 약 2.6, 매매당 평균 +2.2%. 강세장 구간만 검증했고 하락장은 검증하지 않았습니다<br/>
    • <b>섹터 순위·주도주</b>: 통과 종목 수와 3개월 상승률로 줄을 세운 것이며 이 줄 세우기는 과거 데이터로 검증하지 않았습니다<br/>
    • 과거 데이터 분석이며 매수·매도 추천이 아닙니다. 데이터: 네이버 증권, 장 마감 후 확정치
    """
    story.append(Paragraph(rule_text, normal_style))

    try:
        doc.build(story)
        print(f"💾 [성공] 추세추종 분석 PDF 리포트가 생성되었습니다: {pdf_path}")
        return True
    except Exception as e:
        print(f"❌ PDF 생성 실패: {e}")
        return False

def main():
    """
    [5단계] 추세추종 분석 리포트 생성기 메인 함수입니다.
    """
    parser = argparse.ArgumentParser(description="[5단계] ETF 주도주 추세추종 분석 리포트 생성기")
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
