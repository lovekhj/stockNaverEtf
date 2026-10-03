#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
📌 [5단계] AI 추세추종 종합 분석 마크다운 리포트 생성 프로그램 (getEtfAiReport.py)
================================================================================
1. 프로그램 역할:
   4단계에서 산출된 분석 결과 CSV(`분석/분석_YYYYMMDD.csv`) 데이터를 바탕으로 
   누구나 한눈에 주도주 현황과 매매 전략을 파악할 수 있는 
   아주 예쁜 AI 종합 분석 마크다운 보고서(`분석/분석_YYYYMMDD.md`)를 자동 생성합니다.

2. 입력 데이터:
   - CSV 파일: `분석/분석_YYYYMMDD.csv` (4단계 실행 결과)

3. 출력 결과:
   - 마크다운 파일: `분석/분석_YYYYMMDD.md` (예: `분석/분석_20261003.md`)

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

def find_target_csv(target_date=None):
    """
    분석 대상이 되는 CSV 파일 경로(`분석/분석_YYYYMMDD.csv`)를 찾아내는 함수입니다.
    날짜를 직접 지정하지 않으면 가장 최신의 분석 CSV 파일을 자동으로 선택합니다.
    """
    anal_dir = "분석"
    if not os.path.exists(anal_dir):
        print(f"❌ '{anal_dir}' 폴더가 존재하지 않습니다.")
        return None

    # 특정 날짜(예: 20261003)가 지정된 경우
    if target_date:
        filename = f"분석_{target_date}.csv"
        path = os.path.join(anal_dir, filename)
        if os.path.exists(path):
            return path
        else:
            print(f"❌ 지정한 날짜의 분석 CSV 파일이 없습니다: {path}")
            return None

    # 지정된 날짜가 없으면 `분석/` 폴더에서 가장 최신 날짜 파일 검색
    files = glob.glob(os.path.join(anal_dir, "분석_*.csv"))
    if not files:
        print(f"❌ '{anal_dir}' 폴더 내에 분석_YYYYMMDD.csv 파일이 없습니다.")
        return None

    # 날짜순 역순 정렬 후 가장 최근 파일 선택
    files.sort(reverse=True)
    return files[0]

def generate_ai_report(csv_path):
    """
    4단계 분석 CSV 파일 데이터를 파싱하여 가독성 우수한 마크다운(.md) 보고서를 생성합니다.
    
    :param csv_path: 분석 CSV 파일 경로 (예: '분석/분석_20261003.csv')
    :return: True(성공), False(실패)
    """
    base_name = os.path.basename(csv_path)
    date_part = base_name.replace("분석_", "").replace(".csv", "")
    md_path = os.path.join(os.path.dirname(csv_path), f"분석_{date_part}.md")

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
        md.append(f"| 종목코드 | 종목명 | 현재가 | 외국인연속 | 기관연속 | 外보유율 | 변동이유 | 상세페이지 |")
        md.append(f"| :---: | :--- | :---: | :---: | :---: | :---: | :--- | :---: |")
        for r in a_plus_list:
            code = r['종목코드']
            name = r['종목명']
            price = r['현재가']
            f_seq = f"{r['외국인연속매수(일)']}일"
            i_seq = f"{r['기관연속매수(일)']}일"
            f_rate = r['외국인보유율']
            reason = r['변동이유']
            link = f"[네이버증권]({r['상세페이지']})"
            md.append(f"| `{code}` | **{name}** | {price}원 | {f_seq} | {i_seq} | {f_rate} | {reason} | {link} |")
        md.append(f"")
        
        md.append(f"### 💡 A+ 종목별 핵심 투자 팁")
        for r in a_plus_list:
            md.append(f"- **{r['종목명']} ({r['종목코드']})**:")
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
        md.append(f"| 종목코드 | 종목명 | 현재가 | 쌍끌이 | 20일선위 | 정배열 | 외인연속 | 기관연속 | 상세링크 |")
        md.append(f"| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        for r in top_a:
            code = r['종목코드']
            name = r['종목명']
            price = r['현재가']
            bi = r['쌍끌이여부']
            ma20 = r['20일선위']
            align = r['정배열여부']
            f_seq = f"{r['외국인연속매수(일)']}일"
            i_seq = f"{r['기관연속매수(일)']}일"
            link = f"[보기]({r['상세페이지']})"
            md.append(f"| `{code}` | {name} | {price}원 | {bi} | {ma20} | {align} | {f_seq} | {i_seq} | {link} |")
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
    md.append(f"> **리포트 활용법**: 본 마크다운 리포트는 매일 4단계 수급 분석 완료 후 5단계 AI 분석을 통해 자동으로 업데이트됩니다. 최신 `분석_YYYYMMDD.md` 파일을 통해 주도주의 등급 변동 추이를 체크하세요.")

    # 마크다운 파일로 저장
    report_content = "\n".join(md)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"💾 [성공] AI 추세추종 분석 마크다운 리포트가 생성되었습니다: {md_path}")
    return True

def main():
    """
    [5단계] AI 추세추종 분석 리포트 생성기 메인 함수입니다.
    """
    parser = argparse.ArgumentParser(description="[5단계] ETF 주도주 AI 추세추종 분석 마크다운 리포트 생성기")
    parser.add_argument("--date", type=str, help="분석 대상 날짜 (YYYYMMDD 형식, 예: 20261003)")
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
