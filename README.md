# 네이버 주식 ETF 주도주 수급 & 이동평균선(추세추종) 분석 시스템

본 프로젝트는 네이버 증권 API로 국내 주식형 ETF의 상위 구성종목(약 500개)을 매일 수집하고, 장 마감 후 일봉(수정주가)으로 **섹터 순위**, **주도주**, **매수신호(강한 마감 + 추세 통과)**를 계산해 리포트·대시보드·텔레그램으로 전달하는 데이터 파이프라인입니다.

> 매수신호와 섹터 순위는 검증 중인 기준이며 매수·매도 추천이 아닙니다. 외국인·기관 수급 수집과 투자등급(A+/A/B/C)은 과거 검증에서 등급 순서가 이후 수익률과 맞지 않아 2026-10-10에 없앴습니다.

---

## 💻 다른 PC 환경 설정 및 실행 가이드 (Environment Setup)

다른 PC(Windows / macOS / Linux)에서 이 프로그램을 그대로 가져가서 실행할 때 필요한 환경 설정 안내입니다.

### 1️⃣ 필수 사전 요구사항 (Requirements)
* **Python 버전**: Python 3.8 이상 (Python 3.x 기본 제공 버전)
* **운영체제**: Windows 10/11, macOS, Linux (모든 OS 완벽 지원)
* **네트워크**: 인터넷 연결 필요 (네이버 증권 API 실시간 조회용)

### 2️⃣ 의존성 및 Import 패키지 안내 (No `pip install` required!)
본 프로그램은 **파이썬 표준 라이브러리(Standard Library)만 사용**하여 작성되었습니다. 
따라서 별도로 `pip install pandas`, `pip install requests` 등 외부 라이브러리를 설치할 필요가 **전혀 없습니다.** 파이썬만 설치되어 있으면 즉시 실행 가능합니다.

* **사용된 파이썬 기본 표준 모듈 목록 (`import`)**:
  - `urllib.request`, `urllib.parse` : 네이버 웹 API 데이터 통신
  - `json`, `csv`, `re` : JSON 데이터 해석, CSV 엑셀 파일 저장 및 글자 정제
  - `argparse`, `sys`, `os`, `glob`, `datetime`, `collections`, `subprocess`, `time` : 시스템 제어, 명령어 옵션 처리 및 파이프라인 연동

---

### 3️⃣ 다른 PC에서 최초 셋팅 및 실행 절차 (4-Step Quick Start)

#### **1단계: 소스코드 다운로드**
Git이 설치된 경우 저장소를 복제하거나 ZIP 파일로 다운로드하여 원하는 폴더에 압축을 풉니다.
```bash
git clone <저장소 주소>
cd stock_naver
```

#### **2단계: 파이썬 설치 확인**
터미널(CMD 창)에서 파이썬이 정상 설치되어 있는지 확인합니다.
```bash
# macOS / Linux
python3 --version

# Windows CMD / PowerShell
python --version
```
> 💡 만약 파이썬이 설치되어 있지 않다면 [python.org](https://www.python.org/downloads/)에서 Python 3.x 버전을 설치하세요. (Windows 설치 시 **"Add Python to PATH"** 옵션에 체크 필수!)

#### **3단계: 최초 전체 데이터 구축 (1~5단계 순차 실행)**
처음 셋팅한 PC에서는 기본 종목 데이터(`data/`)를 구축하기 위해 전체 파이프라인을 1회 실행합니다.
```bash
# macOS / Linux
python3 main.py --all

# Windows CMD / PowerShell
python main.py --all
```

#### **4단계: 매일 장 마감 후 데일리 수급 분석 실행**
초기 구축이 완료된 이후에는 매일 장 마감 후 `main.py`만 실행하고 **엔터**를 누르면 자동으로 최신 분석 CSV와 리포트가 완성됩니다.
```bash
# macOS / Linux
python3 main.py

# Windows
python main.py
```

---

## 📁 디렉토리 및 파일 구조

```text
stock_naver/
├── data/                                 # 기본 및 중간 분석 데이터 폴더
│   ├── etf_list.csv                      # 국내 주식형 ETF 전체 목록 (439개)
│   ├── etf_dtl_list.csv                  # ETF 상위 1~10위 구성종목 목록
│   ├── etf_top_stocks.csv                # ETF 상위 6자리 주식 종목코드 매핑 (약 500여개)
│   └── stock_sectors.csv                 # 종목별 시장(코스피/코스닥)·섹터 (네이버 업종을 15개 섹터로 묶음)
│
├── reports/                                # 일별 수급 및 이동평균선 분석 결과 저장 폴더
│   ├── report_20261002.csv                  # 수급 & 이평선 분석 결과 CSV 데이터
│   ├── report_20261002.md                   # 추세추종 분석 마크다운 리포트 (매수신호 A, 섹터 순위, 주도주)
│   └── report_YYYYMMDD.csv / .md            # 매일 생성되는 날짜별 분석 파일들
│
├── docs/                                 # 프로젝트 세부 매뉴얼 문서
│   ├── etf_분석.md                        # ETF 데이터 수집 파이프라인 명세서
│   └── 종목선정_검증.md                   # 현재 후보 규칙의 검증 기록
│
├── getEtfList.py                         # 1단계: ETF 기본 목록 수집 스크립트
├── getEtfDtlList.py                      # 2단계: ETF 상위 구성종목 수집 스크립트
├── getEtfTopStockList.py                 # 3단계: 주도주 6자리 종목코드 추출 스크립트
├── getEtfInvestorFlow.py                 # 4단계: 일봉 분석 스크립트 (이동평균선, 매수신호, 추세 통과)
├── getEtfAiReport.py                     # 5단계: 추세추종 분석 리포트(마크다운·PDF) 생성 스크립트
├── buySignal.py                          # 매수신호·추세 통과 규칙 정의 (4단계와 백테스트가 함께 사용)
├── virtualTrade.py                       # 가상 주식거래 장부 갱신 (main.py가 4·5단계 뒤에 자동 실행)
├── index.html / app.js / style.css       # 웹 대시보드 (정적 페이지)
└── main.py                               # 파이프라인 통합 대화형 실행기
```

---

## 🚀 파이프라인 실행 가이드 (`main.py`)

통합 실행 스크립트인 **`main.py`**를 사용하면 1~5단계 전체 파이프라인을 한 번에 실행하거나, 원하는 개별 단계만 옵션으로 선택하여 실행할 수 있습니다.

### 1) 매일 분석 및 리포트 자동 실행 (기본 엔터)
```bash
python3 main.py
# 실행 시 엔터를 치거나 4 지정 -> 4단계(수급분석) + 5단계(리포트 생성) 자동 실행
```

### 2) 전체 파이프라인 순차 실행 (1단계 → 5단계 전체 수집 및 분석)
```bash
python3 main.py --all
```

### 3) 특정 단계만 지정하여 실행 (`--step` 옵션)
```bash
# 5단계 (리포트 생성)만 실행
python3 main.py --step 5

# 4단계 + 5단계 연속 실행
python3 main.py --step 4,5

# 1단계부터 5단계까지 전체 실행
python3 main.py --step 1-5
```

### 4) 단계별 직관적인 옵션으로 실행
```bash
# 1단계: ETF 기본 목록 수집 (getEtfList.py)
python3 main.py --etf-list

# 2단계: ETF 상위 구성종목 수집 (getEtfDtlList.py)
python3 main.py --etf-dtl

# 3단계: 주도주 6자리 종목코드 추출 (getEtfTopStockList.py)
python3 main.py --top-stocks

# 4단계: 외국인/기관 수급 & 이동평균선 통합 분석 (getEtfInvestorFlow.py)
python3 main.py --investor-flow

# 5단계: 추세추종 분석 리포트 생성 (getEtfAiReport.py)
python3 main.py --ai-report
```

---

## 🛠️ 개별 스크립트 직접 실행 방법

### 1단계: 국내 주식형 ETF 전체 목록 수집
```bash
python3 getEtfList.py
```
* **결과 저장**: `data/etf_list.csv` (국내 시장지수 `1`, 업종/테마 `2` 카테고리 439개 ETF 수집)

### 2단계: ETF 상위 1~10위 주요 구성종목 수집
```bash
python3 getEtfDtlList.py
```
* **결과 저장**: `data/etf_dtl_list.csv` (ETF 포트폴리오 상위 1~10위 구성종목 수집)

### 3단계: 주도주 6자리 종목코드 및 상세페이지 매핑
```bash
python3 getEtfTopStockList.py
```
* **결과 저장**: `data/etf_top_stocks.csv` (순수 국내 주식 종목 320개 정제 및 종목코드 매핑)

### 4단계: 일봉 분석 (이동평균선, 매수신호, 추세 통과)
```bash
python3 getEtfInvestorFlow.py
```
* **결과 저장**: `reports/report_YYYYMMDD.csv`
* **핵심 기능**:
  - 종목별 **`시장`**·**`섹터`**를 `data/stock_sectors.csv`에서 읽음 (파일이 없으면 3단계의 섹터를 그대로 사용)
  - 5일, 20일, 60일, 120일 이동평균선(MA), 등락률, 20일 이격도, 차트 꼬리 계산 (수정주가 일봉 기준)
  - **`매수신호`**(A/B/C)와 사유: 강한 마감(+3% 이상, 거래량 1.5배 이상) + 추세 통과(종가 > 60일선, 60일선 상승, 1년 최고 종가의 -15% 이내)
  - **`추세통과`**(O/X), **`3개월수익률`**, **`고점대비`**, **`강한마감`**: 섹터 순위와 주도주 화면에 쓰는 열

### 5단계: 추세추종 분석 리포트(마크다운·PDF) 자동 생성
```bash
python3 getEtfAiReport.py
```
* **결과 저장**: `reports/report_YYYYMMDD.md`, `pdf/report_YYYYMMDD.pdf`
* **리포트 구성**:
  - 1. 매수신호 A 종목
  - 2. 섹터 순위 (통과 종목 수가 많은 순서)
  - 3. 주도주 (섹터 상위 4개, 섹터당 5종목, 3개월 상승률 순)
  - 4. 매매 규칙 안내 (검증 중인 후보 규칙과 한계)

---

## 🖥️ 웹 대시보드 메뉴

| 메뉴 | 내용 |
| :--- | :--- |
| 섹터별 종목조회 (첫 화면) | 위에는 섹터 순위 표, 섹터를 누르면 아래에 그 섹터의 종목 표 |
| 주도주 | 순위가 높은 섹터의 통과 종목을 3개월 상승률 순으로 표시. 섹터 수, 섹터당 종목 수, 시장을 고를 수 있음 |
| 전체 종목 검색 | 종목명·코드 검색, 매수신호·캔들 형태 필터 |
| 가상 주식거래 리포트 | 날짜별 가상 매수·보유·매도 내역과 손익, 종목별 일별 기록 |
| 매매 규칙 | 매수·매도 후보 규칙, 섹터 순위와 주도주 기준, 검증 결과와 한계 |

- **통과** = 종가가 60일선 위, 60일선 상승, 종가가 1년(250거래일) 최고 종가의 -15% 이내
- **가상 주식거래 리포트**: `virtualTrade.py`가 매일 `reports/virtual_trades.csv`에 쌓는 모의 거래 기록입니다. 매수신호 A(추세 통과 + 강한 마감)인 종목을 그날 종가에 100만 원어치 샀다고 치고, 종가가 손절가(보유 중 최고 종가 -5%) 이하인 날 종가에 팔았다고 칩니다. 실제 보유 종목이 아니며 수수료·세금은 넣지 않았습니다.
- 섹터 순위와 주도주 기준은 2026-10-10에 정했고 과거 데이터로 검증하지 않았습니다.

---

## 📖 상세 매뉴얼 및 가이드 문서

- 📄 **[docs/etf_분석.md](file:///Users/hyunjongkim/Documents/100_prd/stockNaverEtf/docs/etf_%EB%B6%84%EC%84%9D.md)**: 전체 데이터 파이프라인 구조 및 네이버 API 명세서
- 📄 **[docs/실시간감지.md](file:///Users/hyunjongkim/Documents/100_prd/stockNaverEtf/docs/%EC%8B%A4%EC%8B%9C%EA%B0%84%EA%B0%90%EC%A7%80.md)**: 내 포트폴리오 실시간 시세 감시 및 -3% 손절 알림 시스템 설계 명세서
