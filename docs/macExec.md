# 🖥️ macOS 오후 4시 자동 실행 & 일별 작업 로그 가이드 (`macExec.md`)

> **[개요]**
> 본 문서는 **ETF 주도주 수급 분석 파이프라인**을 macOS 환경에서 매일 주식 장 마감 후(**오후 4:00**) 자동으로 실행되도록 설정하는 백그라운드 자동 실행 및 **일별 로그 자동 저장(`reports/log_YYYYMMDD.txt`) 설정 가이드**입니다.

---

## 📁 1. 일별 작업 로그 파일 생성 안내 (`reports/log_YYYYMMDD.txt`)

프로그램이 실행(수동/자동 상관없이)되면 **`reports/` 폴더 내에 당일 날짜의 로그 파일(`log_YYYYMMDD.txt`)이 자동으로 생성 및 축적**됩니다.

### 📝 로그 파일 저장 내용
- **파이프라인 시작 시각**: 예) `📌 [파이프라인 실행 시작 시각: 2026-10-04 16:00:00]`
- **단계별 실행 및 소요 시간**: 4단계 수급 분석 및 5단계 AI 리포트 생성 내역
- **오류 및 성공 여부**: 예) `🎉 [파이프라인 종료 시각: 2026-10-04 16:01:25] (전체 소요시간: 85.2초)`

---

## ⭐️ 2. `crontab` 16:00시 자동 실행 & 일별 로그 연동 (2단계 설정)

### 1단계: 매일 오후 15:58분 맥 자동 깨우기 (`pmset`)
맥 터미널(Terminal)에서 아래 명령어를 실행합니다:
```bash
sudo pmset repeat wakeorpoweron MTWRF 15:58:00
```

### 2단계: 매일 오후 16:00시 파이프라인 자동 실행 (`crontab`)
1. 터미널에서 크론탭 편집기를 엽니다:
   ```bash
   crontab -e
   ```
2. 아래 구문을 등록하고 저장(`:wq`)합니다:
   ```bash
   0 16 * * 1-5 cd /Users/hyunjongkim/Documents/100_prd/stockNaverEtf && /usr/bin/python3 main.py --step 4,5 >> reports/log_$(date +\%Y\%m\%d).txt 2>&1
   ```
3. 등록 확인:
   ```bash
   crontab -l
   ```

---

## 🔍 3. 당일 로그 확인 방법

```bash
# 오늘 날짜 로그 내용 확인
cat reports/log_$(date +%Y%m%d).txt

# 특정 날짜 로그 확인 (예: 2026년 10월 4일)
cat reports/log_20261004.txt

# 실시간 진행 로그 감시
tail -f reports/log_$(date +%Y%m%d).txt
```

---

*최종 작성일: 2026-10-04*
