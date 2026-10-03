# 네이버 주식 ETF 주도주 수급 & 이동평균선(추세추종) 분석 시스템

본 프로젝트는 네이버 증권 API를 활용하여 국내 주식형 ETF의 상위 주도주를 수집하고, **외국인·기관 동시 순매수(쌍끌이)** 및 **5일·20일·60일·120일 이동평균선 정배열 추세**를 종합 분석하여 **안전한 투자등급(A+, A, B, C)**을 자동 산출하는 데이터 파이프라인 시스템입니다.

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
초기 구축이 완료된 이후에는 매일 장 마감 후 `main.py`만 실행하고 **엔터**를 누르면 자동으로 최신 수급 분석 및 AI 리포트가 완성됩니다.
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
│   ├── etf_dtl_list.csv                  # ETF 상위 1~5위 구성종목 목록 (2,181개)
│   └── etf_top_stocks.csv                # ETF 상위 6자리 주식 종목코드 매핑 (320개)
│
├── 분석/                                 # 일별 수급 및 이동평균선 분석 결과 저장 폴더
│   ├── 분석_20261003.csv                  # 수급 & 이평선 분석 결과 CSV 데이터
│   ├── 분석_20261003.md                   # AI 추세추종 종합 분석 마크다운 리포트
│   └── 분석_YYYYMMDD.csv / .md            # 매일 생성되는 날짜별 분석 파일들
│
├── docs/                                 # 프로젝트 세부 매뉴얼 문서
│   ├── etf_분석.md                        # ETF 데이터 수집 파이프라인 명세서
│   └── 추세추종.md                        # 주체추종 + 피라미드 분할매수 매매 가이드
│
├── getEtfList.py                         # 1단계: ETF 기본 목록 수집 스크립트
├── getEtfDtlList.py                      # 2단계: ETF 상위 구성종목 수집 스크립트
├── getEtfTopStockList.py                 # 3단계: 주도주 6자리 종목코드 추출 스크립트
├── getEtfInvestorFlow.py                 # 4단계: 수급 & 이동평균선 통합 분석 스크립트
├── getEtfAiReport.py                     # 5단계: AI 추세추종 분석 마크다운 리포트 생성 스크립트
└── main.py                               # 파이프라인 통합 대화형 실행기
```

---

## 🚀 파이프라인 실행 가이드 (`main.py`)

통합 실행 스크립트인 **`main.py`**를 사용하면 1~5단계 전체 파이프라인을 한 번에 실행하거나, 원하는 개별 단계만 옵션으로 선택하여 실행할 수 있습니다.

### 1) 매일 수급 분석 및 AI 리포트 자동 실행 (기본 엔터)
```bash
python3 main.py
# 실행 시 엔터를 치거나 4 지정 -> 4단계(수급분석) + 5단계(AI 마크다운 리포트 생성) 자동 실행
```

### 2) 전체 파이프라인 순차 실행 (1단계 → 5단계 전체 수집 및 분석)
```bash
python3 main.py --all
```

### 3) 특정 단계만 지정하여 실행 (`--step` 옵션)
```bash
# 5단계 (AI 리포트 생성)만 실행
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

# 5단계: AI 추세추종 분석 마크다운 리포트 생성 (getEtfAiReport.py)
python3 main.py --ai-report
```

---

## 🛠️ 개별 스크립트 직접 실행 방법

### 1단계: 국내 주식형 ETF 전체 목록 수집
```bash
python3 getEtfList.py
```
* **결과 저장**: `data/etf_list.csv` (국내 시장지수 `1`, 업종/테마 `2` 카테고리 439개 ETF 수집)

### 2단계: ETF 상위 1~5위 주요 구성종목 수집
```bash
python3 getEtfDtlList.py
```
* **결과 저장**: `data/etf_dtl_list.csv` (ETF 포트폴리오 상위 1~5위 2,181개 종목 수집)

### 3단계: 주도주 6자리 종목코드 및 상세페이지 매핑
```bash
python3 getEtfTopStockList.py
```
* **결과 저장**: `data/etf_top_stocks.csv` (순수 국내 주식 종목 320개 정제 및 종목코드 매핑)

### 4단계: 외국인/기관 수급 & 5/20/60/120일 이동평균선 통합 분석
```bash
python3 getEtfInvestorFlow.py
```
* **결과 저장**: `분석/분석_YYYYMMDD.csv`
* **핵심 기능**:
  - 이전 날짜 분석 파일과 자동 비교하여 **`등급변동` (예: `A -> A+ (상향)`)** 및 **`변동이유`** 자동 기록
  - 외국인/기관 5일 연속 매수 일수 및 3일 누적 순매수 수량 합산
  - 5일, 20일, 60일, 120일 이동평균선(MA) 계산
  - `20일선위(O/X)` 및 `정배열여부(O/X)` 자동 판별
  - `투자등급(A+, A, B, C)` 자동 부여 및 정렬

### 5단계: AI 추세추종 분석 마크다운 리포트 자동 생성
```bash
python3 getEtfAiReport.py
```
* **결과 저장**: `분석/분석_YYYYMMDD.md`
* **핵심 기능**:
  - `분석_YYYYMMDD.csv` 데이터를 바탕으로 AI 분석 리포트 자동 작성
  - 등급 분포, A+ / A 등급 주도주 심층 요약, 등급 상향/하향 종목 하이라이트
  - 추세추종 피라미딩 매매 가이드 및 risk 관리 원칙 자동 제시

---

## 📊 투자등급 (`투자등급`) 기준표

| 투자등급 | 조건 조합 | 의미 및 매매 전략 |
| :--- | :--- | :--- |
| **`A+`** | **`쌍끌이(O)` + `20일선위(O)` + `정배열(O)`** | **최상위 대세상승주** (5 >= 20 >= 60 >= 120일 정배열)<br>수급과 차트 추세 최상. 시세 폭발 가능성 최상 |
| **`A`** | **`쌍끌이(O)` + `20일선위(O)`** | **우량 수급 상승주** (20일선 위 상승 모멘텀 유지)<br>20일선 눌림목 반등 시 1차 씨앗 매수(40%) 진입 적합 |
| **`B`** | **`쌍끌이(O)` OR `20일선위(O)`** | **관찰 대상 종목** (수급이나 차트 추세 일부 충족)<br>A등급 이상 승격 시 추적 |
| **`C`** | **조건 미충족** | **매수 관망 (매수 금지)**<br>20일선 아래 하락 추세 포함. 리스크가 높으므로 매수 제외 |

---

## 📖 상세 매뉴얼 및 가이드 문서

- 📄 **[docs/etf_분석.md](file:///Users/hyunjongkim/Documents/02_dev/stock_naver/docs/etf_%EB%B6%84%EC%84%9D.md)**: 전체 데이터 파이프라인 구조 및 네이버 API 명세서
- 📄 **[docs/추세추종.md](file:///Users/hyunjongkim/Documents/02_dev/stock_naver/docs/%EC%B6%94%EC%84%B8%EC%B6%94%EC%A2%85.md)**: 주체추종 원칙, 4단계 피라미드 분할매수 (40% → 30% → 20% → 10%), -3% 손절 철칙 상세 매뉴얼
