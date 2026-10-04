# 🖥️ macOS 오후 4시 자동 실행, 깃 푸시 & 텔레그램 알림 가이드 (`macExec.md`)

> **[개요]**
> 본 문서는 **ETF 주도주 수급 분석 파이프라인**을 macOS 환경에서 매일 주식 장 마감 후(**오후 4:00**) 자동으로 실행되도록 설정하는 가이드입니다.
> 기본 실행 시에는 안전을 위해 깃 푸시/텔레그램이 작동하지 않으며, **옵션 지정 시(`--push-git`, `--telegram`)에만 GitHub 원격 저장소 자동 커밋&푸시 및 A+ 등급 종목 텔레그램 알림이 작동**합니다.

---

## ⭐️ 1. 옵션별 실행 명령어 구문

### 1.1 기본 실행 (수동 테스트 - 전송 안 함)
```bash
python3 main.py --step 4,5
```

### 1.2 통합 실행 (수급분석 + 깃 푸시 + 텔레그램 알림)
```bash
python3 main.py --step 4,5 --push-git --telegram
```

### 1.3 텔레그램 알림 단독 실행 (분석 과정 생략, 기존 리포트 전송)
```bash
python3 main.py --telegram-only
```

### 1.4 Git 푸시 단독 실행 (분석 과정 생략, 기존 파일 커밋 및 푸시)
```bash
python3 main.py --push-git-only
```

- **`--push-git`**: 분석 완료 후 `git add`, `git commit -m "주식분석_자동화_YYYYMMDD"`, `git push` 자동 수행.
- **`--push-git-only`**: 1~5단계 데이터 수집을 생략하고 Git 커밋(`주식분석_자동화_YYYYMMDD`) 및 푸시만 단독 실행.
- **`--telegram`**: 분석 완료 후 **`A+ 등급` 주도주 종목명 및 주요 섹터(`종목명 - 섹터`)만 요약**하여 텔레그램 메시지 발송.
- **`--telegram-only`**: 1~5단계 데이터 수집을 생략하고 기존 최신 리포트로 텔레그램 알림만 단독 발송.

---

## 📲 2. 텔레그램 연동 및 `.env` 설정 방법

텔레그램 봇 연동을 위해 프로젝트 루트 경로에 `.env` 파일을 생성하거나 CLI 인자로 전달할 수 있습니다.

### 2.1 `.env` 파일 설정 방법 (추천)
프로젝트 루트 폴더(`/Users/hyunjongkim/Documents/100_prd/stockNaverEtf/.env`)에 아래 두 줄을 작성합니다:
```env
TELEGRAM_BOT_TOKEN="발급받으신_텔레그램_봇_토큰"
TELEGRAM_CHAT_ID="발급받으신_대화방_또는_채널_ID"
```

### 2.2 CLI 직접 전달 방법
```bash
python3 main.py --step 4,5 --telegram --bot-token "YOUR_TOKEN" --chat-id "YOUR_CHAT_ID"
```

---

## ⏰ 3. `crontab` 오후 4시 자동 실행 & 옵션 연동 (최종 2단계 설정)

### 1단계: 매일 오후 15:58분 맥 자동 깨우기 (`pmset`)
맥 터미널(Terminal)에서 아래 명령어를 실행합니다:
```bash
sudo pmset repeat wakeorpoweron MTWRF 15:58:00
```

### 2단계: 매일 오후 16:00시 파이프라인 + 깃 푸시 + 텔레그램 알림 (`crontab`)
1. 터미널에서 크론탭 편집기를 엽니다:
   ```bash
   crontab -e
   ```
2. 아래 구문을 등록하고 저장(`:wq`)합니다:
   ```bash
   0 16 * * 1-5 cd /Users/hyunjongkim/Documents/100_prd/stockNaverEtf && /usr/bin/python3 main.py --step 4,5 --push-git --telegram >> reports/log_$(date +\%Y\%m\%d).txt 2>&1
   ```
3. 등록 확인:
   ```bash
   crontab -l
   ```

---

## 📁 4. 일별 작업 로그 파일 및 확인 방법 (`reports/log_YYYYMMDD.txt`)

프로그램 실행 시 **`reports/log_YYYYMMDD.txt`**에 실행 시작/종료 시각, 소요 시간, 깃 푸시 및 텔레그램 전송 성공 여부가 기록됩니다.

```bash
# 오늘 날짜 로그 확인
cat reports/log_$(date +%Y%m%d).txt

# 실시간 진행 로그 감시
tail -f reports/log_$(date +%Y%m%d).txt
```

---

*최종 작성일: 2026-10-04*
