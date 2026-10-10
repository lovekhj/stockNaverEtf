/**
 * ==========================================================================
 * 📌 ETF 주도주 수급 대시보드 - 핵심 JavaScript 앱 엔진 (app.js)
 * ==========================================================================
 */

// Global State Management
function getTodayDateStr() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}${mm}${dd}`;
}

let allStockData = [];
let filteredStockData = [];
// 리포트 날짜 목록: main.py 실행 시 자동 생성되는 reports/available_dates.js (window.AVAILABLE_DATES)
let availableDates = Array.isArray(window.AVAILABLE_DATES) ? [...window.AVAILABLE_DATES] : [];
let sortedAvailableDates = [...availableDates].sort((a, b) => b.localeCompare(a));
let currentDate = getTodayDateStr();
let stockHistoryCache = {}; // { dateStr: { code: gradeStr } }

// 차트 꼬리 분류 (getEtfInvestorFlow.py 의 classify_candle 이 만드는 값과 같아야 한다)
const CANDLE_TYPES = [
  { id: "장대양봉", label: "장대양봉" },
  { id: "보통 양봉", label: "보통 양봉" },
  { id: "긴 아래꼬리", label: "긴 아래꼬리" },
  { id: "십자형", label: "십자형" },
  { id: "긴 윗꼬리", label: "긴 윗꼬리" },
  { id: "보통 음봉", label: "보통 음봉" },
  { id: "장대음봉", label: "장대음봉" }
];

// Filter States - Defaults: 모든 필터 "전체"
const DEFAULT_GRADE_FILTER = "ALL";
const DEFAULT_SIGNAL_FILTER = "ALL";
const DEFAULT_CANDLE_FILTER = CANDLE_TYPES.map(c => c.id);
const DEFAULT_OVERHEAT_FILTER = "ALL";

let currentGradeFilter = DEFAULT_GRADE_FILTER;
let currentSignalFilter = DEFAULT_SIGNAL_FILTER;
let currentCandleFilter = [...DEFAULT_CANDLE_FILTER];
let currentOverheatFilter = DEFAULT_OVERHEAT_FILTER;
let currentSectorFilter = "ALL";
let currentAlignFilter = "ALL";
let currentSearchQuery = "";

// Pagination State
let currentPage = 1;
const pageSize = 25;

// Table Sort State
let sortKey = "투자등급";
let sortAsc = true;

// Initialize Dashboard App
document.addEventListener("DOMContentLoaded", () => {
  const todayStr = getTodayDateStr();
  const sortedDates = [...availableDates].sort((a, b) => b.localeCompare(a));
  const latestVerified = sortedDates[0] || todayStr;

  // 오늘 날짜 데이터가 알려진 목록에 있으면 사용, 그렇지 않으면 최신 유효 일자 선택
  if (availableDates.includes(todayStr)) {
    currentDate = todayStr;
  } else {
    currentDate = latestVerified;
  }
  latestValidDate = currentDate;

  initDatePickers(currentDate);
  loadDateExplorer();
  loadDashboardData(currentDate, true);
  buildStockHistoryCache();
});

function buildStockHistoryCache() {
  availableDates.forEach(dateStr => {
    fetch(`reports/report_${dateStr}.csv`)
      .then(res => res.text())
      .then(csvText => {
        Papa.parse(csvText, {
          header: true,
          skipEmptyLines: true,
          transformHeader: h => h.replace(/^\ufeff/, '').trim(),
          complete: function(results) {
            if (results.data) {
              stockHistoryCache[dateStr] = {};
              results.data.forEach(item => {
                if (item.종목코드) {
                  stockHistoryCache[dateStr][item.종목코드] = item.투자등급;
                }
              });
            }
          }
        });
      })
      .catch(() => {});
  });
}

/**
 * 0. 달력(Date Picker) 초기화 및 날짜 변경 핸들러
 */
function initDatePickers(dateStr) {
  if (!dateStr || dateStr.length !== 8) return;
  const yyyy = dateStr.slice(0, 4);
  const mm = dateStr.slice(4, 6);
  const dd = dateStr.slice(6, 8);
  const val = `${yyyy}-${mm}-${dd}`;

  const lnbPicker = document.getElementById("datePickerInput");
  const hdrPicker = document.getElementById("reportHeaderDatePicker");
  if (lnbPicker) lnbPicker.value = val;
  if (hdrPicker) hdrPicker.value = val;
}

function handleDatePickerChange(dateVal) {
  if (!dateVal) return;
  const dateStr = dateVal.replace(/-/g, '');
  currentDate = dateStr;

  initDatePickers(dateStr);
  loadDashboardData(dateStr);

  const reportView = document.getElementById("viewReport");
  if (reportView && reportView.classList.contains("active")) {
    selectDateReport(dateStr);
  }
}

/**
 * 2. 인터랙티브 년/월 그리드 달력 위젯 (Calendar Widget)
 */
let calCurrentYear = 2026;
let calCurrentMonth = 10;

function loadDateExplorer() {
  initCalendarWidget(currentDate);
}

function initCalendarWidget(dateStr) {
  if (dateStr && dateStr.length === 8) {
    calCurrentYear = parseInt(dateStr.slice(0, 4), 10);
    calCurrentMonth = parseInt(dateStr.slice(4, 6), 10);
  } else {
    const d = new Date();
    calCurrentYear = d.getFullYear();
    calCurrentMonth = d.getMonth() + 1;
  }
  populateCalDropdowns();
  renderCalendarGrid();
}

function populateCalDropdowns() {
  const yearSelect = document.getElementById("calYearSelect");
  const monthSelect = document.getElementById("calMonthSelect");
  if (!yearSelect || !monthSelect) return;

  const startY = 2024;
  const endY = 2028;

  let yHtml = "";
  for (let y = startY; y <= endY; y++) {
    yHtml += `<option value="${y}">${y}년</option>`;
  }
  yearSelect.innerHTML = yHtml;

  let mHtml = "";
  for (let m = 1; m <= 12; m++) {
    mHtml += `<option value="${m}">${m}월</option>`;
  }
  monthSelect.innerHTML = mHtml;
}

function handleCalSelectChange() {
  const yearSelect = document.getElementById("calYearSelect");
  const monthSelect = document.getElementById("calMonthSelect");
  if (!yearSelect || !monthSelect) return;

  calCurrentYear = parseInt(yearSelect.value, 10);
  calCurrentMonth = parseInt(monthSelect.value, 10);
  renderCalendarGrid();
}

function changeCalMonth(delta) {
  calCurrentMonth += delta;
  if (calCurrentMonth > 12) {
    calCurrentMonth = 1;
    calCurrentYear++;
  } else if (calCurrentMonth < 1) {
    calCurrentMonth = 12;
    calCurrentYear--;
  }
  renderCalendarGrid();
}

function renderCalendarGrid() {
  const grid = document.getElementById("calendarDaysGrid");
  const yearSelect = document.getElementById("calYearSelect");
  const monthSelect = document.getElementById("calMonthSelect");

  if (yearSelect) yearSelect.value = calCurrentYear;
  if (monthSelect) monthSelect.value = calCurrentMonth;

  if (!grid) return;
  grid.innerHTML = "";

  // 1일의 요일 (0: 일요일, 6: 토요일)
  const firstDayObj = new Date(calCurrentYear, calCurrentMonth - 1, 1);
  const startDay = firstDayObj.getDay();

  // 해당 월의 총 일수
  const totalDays = new Date(calCurrentYear, calCurrentMonth, 0).getDate();

  // 이전 달 빈 칸
  for (let i = 0; i < startDay; i++) {
    const emptyCell = document.createElement("div");
    emptyCell.className = "cal-day-cell empty";
    grid.appendChild(emptyCell);
  }

  // 날짜 셀 생성
  for (let day = 1; day <= totalDays; day++) {
    const mmStr = String(calCurrentMonth).padStart(2, '0');
    const ddStr = String(day).padStart(2, '0');
    const dateStr = `${calCurrentYear}${mmStr}${ddStr}`;

    const dayObj = new Date(calCurrentYear, calCurrentMonth - 1, day);
    const dayOfWeek = dayObj.getDay();

    const cell = document.createElement("div");
    let cellClass = "cal-day-cell";
    if (dayOfWeek === 0) cellClass += " sun";
    if (dayOfWeek === 6) cellClass += " sat";

    if (availableDates.includes(dateStr)) {
      cellClass += " has-data";
    }

    if (dateStr === currentDate) {
      cellClass += " selected";
    }

    cell.className = cellClass;
    cell.setAttribute("data-date", dateStr);
    cell.title = availableDates.includes(dateStr) 
      ? `${calCurrentYear}-${mmStr}-${ddStr} (수급 리포트 존재)` 
      : `${calCurrentYear}-${mmStr}-${ddStr}`;
    cell.innerHTML = `<span class="day-num">${day}</span>`;
    cell.onclick = () => onCalendarDayClick(dateStr);

    grid.appendChild(cell);
  }
}

function onCalendarDayClick(dateStr) {
  currentDate = dateStr;
  initDatePickers(dateStr);
  switchView('dashboard');
  loadDashboardData(dateStr);
  renderCalendarGrid();
}

let latestValidDate = "20261007";
let modalCloseCallback = null;

/**
 * 커스텀 모달 알림창 띄우기
 */
function showCustomModal(title, text, onClose) {
  const overlay = document.getElementById("customModalOverlay");
  const titleEl = document.getElementById("modalTitle");
  const bodyEl = document.getElementById("modalBodyText");
  const closeBtn = document.getElementById("btnModalClose");

  if (titleEl) titleEl.innerText = title;
  if (bodyEl) bodyEl.innerHTML = text;

  modalCloseCallback = onClose;

  if (overlay) overlay.classList.add("active");
  if (closeBtn) closeBtn.focus();
}

function closeCustomModal() {
  const overlay = document.getElementById("customModalOverlay");
  if (overlay) overlay.classList.remove("active");

  if (typeof modalCloseCallback === "function") {
    const cb = modalCloseCallback;
    modalCloseCallback = null;
    cb();
  }
}

/**
 * 로컬 file:// 및 http:// 프로토콜 통합 파일 읽기 도우미 (fetch + XMLHttpRequest fallback)
 */
function fetchLocalFile(path) {
  const tryPaths = [
    path,
    `./${path.replace(/^\.\//, '')}`,
    `../${path.replace(/^\.\//, '')}`,
    `/${path.replace(/^\//, '')}`
  ];

  return new Promise((resolve, reject) => {
    let attempt = 0;

    function tryFetchNext() {
      if (attempt >= tryPaths.length) {
        tryXHRNext(0);
        return;
      }
      const targetPath = tryPaths[attempt++];
      fetch(targetPath)
        .then(res => {
          if (res.ok || res.status === 0) return res.text();
          throw new Error("NOT_FOUND");
        })
        .then(text => {
          if (text && text.trim() && !text.toLowerCase().includes("<!doctype html>")) {
            resolve(text);
          } else {
            tryFetchNext();
          }
        })
        .catch(() => {
          tryFetchNext();
        });
    }

    function tryXHRNext(idx) {
      if (idx >= tryPaths.length) {
        reject(new Error("NOT_FOUND"));
        return;
      }
      const targetPath = tryPaths[idx];
      try {
        const xhr = new XMLHttpRequest();
        xhr.open("GET", targetPath, true);
        xhr.onload = function () {
          if ((xhr.status === 200 || xhr.status === 0) && xhr.responseText && xhr.responseText.trim() && !xhr.responseText.toLowerCase().includes("<!doctype html>")) {
            resolve(xhr.responseText);
          } else {
            tryXHRNext(idx + 1);
          }
        };
        xhr.onerror = function () {
          tryXHRNext(idx + 1);
        };
        xhr.send();
      } catch (e) {
        tryXHRNext(idx + 1);
      }
    }

    tryFetchNext();
  });
}

/**
 * 데이터가 존재하지 않는 날짜 선택 시 오른쪽 영역을 깔끔한 데이터 없음 상태로 표시
 */
function renderEmptyDashboard(dateStr) {
  allStockData = [];
  filteredStockData = [];
  
  const formattedDate = `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
  
  const latestDateText = document.getElementById("latestDateText");
  if (latestDateText) latestDateText.innerText = formattedDate;

  const totalStocksBadge = document.getElementById("totalStocksBadgeCount");
  if (totalStocksBadge) totalStocksBadge.innerText = "0";

  renderKPIs();
  renderSectorGrid();
  populateSectorSelectFilter();

  const tbody = document.getElementById("tableBody");
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="19" style="text-align: center; padding: 3.5rem 1rem; color: var(--text-muted); font-size: 0.95rem;">
          <i class="fa-solid fa-calendar-xmark" style="font-size: 2.5rem; margin-bottom: 0.8rem; display: block; color: var(--text-dim);"></i>
          <strong style="color: var(--text-main); font-size: 1.05rem; display: block; margin-bottom: 0.3rem;">
            ${formattedDate} 데이터가 존재하지 않습니다.
          </strong>
          <span style="font-size: 0.82rem; color: var(--text-dim);">
            달력에서 데이터 지표(🟢)가 표시된 거래일을 선택하시면 상세 수급 리포트가 로드됩니다.
          </span>
        </td>
      </tr>
    `;
  }
  
  const visibleRowCount = document.getElementById("visibleRowCount");
  if (visibleRowCount) visibleRowCount.innerText = "0";

  renderCalendarGrid();
}

/**
 * 3. 메인 CSV 분석 데이터 파싱 및 로드 (`reports/report_YYYYMMDD.csv`)
 */
function loadDashboardData(dateStr, isInitialLoad = false) {
  const csvPath = `reports/report_${dateStr}.csv`;

  fetchLocalFile(csvPath)
    .then(csvText => {
      Papa.parse(csvText, {
        header: true,
        skipEmptyLines: true,
        transformHeader: function(h) {
          return h ? h.replace(/^\ufeff/, '').trim() : '';
        },
        complete: function (results) {
          const cleanData = (results.data || []).map(row => {
            const cleanRow = {};
            Object.keys(row).forEach(k => {
              const cleanKey = k ? k.replace(/^\ufeff/, '').trim() : '';
              if (cleanKey) cleanRow[cleanKey] = row[k];
            });
            return cleanRow;
          }).filter(row => row.종목코드 || row.종목명);

          if (cleanData.length > 0) {
            latestValidDate = dateStr;
            currentDate = dateStr;
            if (!availableDates.includes(dateStr)) {
              availableDates.push(dateStr);
              sortedAvailableDates = [...availableDates].sort((a, b) => b.localeCompare(a));
            }
            allStockData = cleanData.map(item => {
              const parseSeq = (val) => {
                if (val === undefined || val === null || val === "") return 0;
                const num = parseInt(String(val).replace(/[^0-9]/g, ''), 10);
                return isNaN(num) ? 0 : num;
              };
              const fSeq = parseSeq(item["외국인연속매수(일)"] || item["외국인연속매수"] || item["외국인연속"]);
              const iSeq = parseSeq(item["기관연속매수(일)"] || item["기관연속매수"] || item["기관연속"]);

              // 차트 꼬리: CSV에 값이 있을 때만 쓰고, 없으면 null (임의로 만들어 넣지 않는다)
              const rawCandle = item.차트꼬리 || item.캔들모양 || item.차트패턴;
              const candleShape = (rawCandle && rawCandle.trim() !== "-") ? rawCandle.trim() : null;

              return {
                ...item,
                종목코드: item.종목코드 ? item.종목코드.trim() : "",
                종목명: item.종목명 ? item.종목명.trim() : "",
                섹터: item.섹터 ? item.섹터.trim() : "일반 주도주",
                투자등급: item.투자등급 ? item.투자등급.trim() : "C",
                등급변동: item.등급변동 ? item.등급변동.trim() : "-",
                변동이유: item.변동이유 ? item.변동이유.trim() : "-",
                차트꼬리: candleShape,
                등락률: (item.등락률 || "0.00%").trim().replace(/^--/, "-"),
                현재가: item.현재가 ? item.현재가.trim() : "0",
                쌍끌이여부: item.쌍끌이여부 ? item.쌍끌이여부.trim() : "X",
                정배열여부: item.정배열여부 ? item.정배열여부.trim() : "X",
                "20일선위": item["20일선위"] ? item["20일선위"].trim() : "X",
                외국인연속: fSeq,
                기관연속: iSeq,
                외국인연속매수: fSeq,
                기관연속매수: iSeq,
                외국인보유율: item.외국인보유율 ? item.외국인보유율.trim() : "0.0%",
                상세페이지: item.상세페이지 ? item.상세페이지.trim() : "#"
              };
            });
            
            // 날짜 뱃지 업데이트
            const formattedDate = `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
            const elDateText = document.getElementById("latestDateText");
            if (elDateText) elDateText.innerText = formattedDate;

            const elTotalBadge = document.getElementById("totalStocksBadgeCount");
            if (elTotalBadge) elTotalBadge.innerText = allStockData.length.toLocaleString();

            // UI 영역 업데이트
            renderKPIs();
            renderSectorGrid();
            populateSectorSelectFilter();
            applyFiltersAndRenderTable();
            renderCalendarGrid();
          } else {
            renderEmptyDashboard(dateStr);
          }
        },
        error: function () {
          renderEmptyDashboard(dateStr);
        }
      });
    })
    .catch(err => {
      renderEmptyDashboard(dateStr);
    });
}

/**
 * 4. 핵심 KPI 카드 요약 통계 계산 및 화면 표시
 */
function renderKPIs() {
  const total = allStockData.length;
  const aplusList = allStockData.filter(d => d.투자등급 === "A+");
  const aList = allStockData.filter(d => d.투자등급 === "A");
  const dualList = allStockData.filter(d => d.쌍끌이여부 === "O");
  const upgradedList = allStockData.filter(d => d.등급변동.includes("상향"));

  const elTotal = document.getElementById("kpiTotalCount");
  if (elTotal) elTotal.innerText = `${total.toLocaleString()}개`;
  
  const aplusRatio = total > 0 ? ((aplusList.length / total) * 100).toFixed(1) : "0.0";
  const elAplusCount = document.getElementById("kpiAplusCount");
  if (elAplusCount) elAplusCount.innerText = `${aplusList.length}개`;
  const elAplusRatio = document.getElementById("kpiAplusRatio");
  if (elAplusRatio) elAplusRatio.innerText = `비율 ${aplusRatio}%`;

  const aRatio = total > 0 ? ((aList.length / total) * 100).toFixed(1) : "0.0";
  const elACount = document.getElementById("kpiACount");
  if (elACount) elACount.innerText = `${aList.length}개`;
  const elARatio = document.getElementById("kpiARatio");
  if (elARatio) elARatio.innerText = `비율 ${aRatio}%`;

  const dualRatio = total > 0 ? ((dualList.length / total) * 100).toFixed(1) : "0.0";
  const elDualCount = document.getElementById("kpiDualCount");
  if (elDualCount) elDualCount.innerText = `${dualList.length}개`;
  const elDualRatio = document.getElementById("kpiDualRatio");
  if (elDualRatio) elDualRatio.innerText = `비율 ${dualRatio}%`;

  const elUpgradedCount = document.getElementById("kpiUpgradedCount");
  if (elUpgradedCount) elUpgradedCount.innerText = `${upgradedList.length}개`;

  // LNB 퀵 카운터 파필
  const elQAp = document.getElementById("quickCountAplus");
  if (elQAp) elQAp.innerText = aplusList.length;
  const elQA = document.getElementById("quickCountA");
  if (elQA) elQA.innerText = aList.length;
  const elQUp = document.getElementById("quickCountUpgraded");
  if (elQUp) elQUp.innerText = upgradedList.length;

  updateFilterCounts();
}

/**
 * 4-1. 필터 콤보박스(등급 / 캔들 / 과열) 옵션별 실시간 개수 갱신
 */
function updateFilterCounts() {
  const total = allStockData.length;
  const aplusList = allStockData.filter(d => d.투자등급 === "A+");
  const aList = allStockData.filter(d => d.투자등급 === "A");

  // Update Grade Select Combobox Options with Live Counts
  const bList = allStockData.filter(d => d.투자등급 === "B");
  const cList = allStockData.filter(d => d.투자등급 === "C");

  const gradeSelect = document.getElementById("gradeSelectFilter");
  if (gradeSelect) {
    const curVal = currentGradeFilter;
    gradeSelect.innerHTML = `
      <option value="ALL">전체 보기 (${total.toLocaleString()}개)</option>
      <option value="A+">🔥 A+ 최상위주 (${aplusList.length.toLocaleString()}개)</option>
      <option value="A">⭐ A 우량 수급주 (${aList.length.toLocaleString()}개)</option>
      <option value="B">🟡 B 일반 수급주 (${bList.length.toLocaleString()}개)</option>
      <option value="C">⚪ C 미달/관망주 (${cList.length.toLocaleString()}개)</option>
    `;
    gradeSelect.value = curVal;
  }

  // Update Buy Signal Select Combobox Options with Live Counts
  const signalSelect = document.getElementById("signalSelectFilter");
  if (signalSelect) {
    const signalCount = (letter) => allStockData.filter(d => (d.매수신호 || "").startsWith(letter)).length;
    signalSelect.innerHTML = `
      <option value="ALL">전체 매수신호 (${total.toLocaleString()}개)</option>
      <option value="A">A(매수) (${signalCount("A").toLocaleString()}개)</option>
      <option value="B">B(재검토) (${signalCount("B").toLocaleString()}개)</option>
      <option value="C">C(매수금지) (${signalCount("C").toLocaleString()}개)</option>
    `;
    signalSelect.value = currentSignalFilter;
  }

  // Update Candle Multi-Select Combobox Options with Live Counts
  const candleOptionList = document.getElementById("candleOptionList");
  const candleLabel = document.getElementById("candleMultiSelectLabel");
  const chkAll = document.getElementById("chkCandleAll");

  if (candleOptionList) {
    const counts = {};
    CANDLE_TYPES.forEach(t => {
      counts[t.id] = allStockData.filter(d => (d.차트꼬리 || "").includes(t.id)).length;
    });

    let selectedArr = [];
    if (currentCandleFilter === "ALL") {
      selectedArr = CANDLE_TYPES.map(t => t.id);
    } else if (Array.isArray(currentCandleFilter)) {
      selectedArr = currentCandleFilter;
    }
    
    if (chkAll) {
      chkAll.checked = selectedArr.length === CANDLE_TYPES.length;
    }

    candleOptionList.innerHTML = CANDLE_TYPES.map(t => {
      const isChecked = selectedArr.includes(t.id);
      const c = counts[t.id] || 0;
      return `
        <label class="multiselect-chk-label">
          <input type="checkbox" value="${t.id}" ${isChecked ? "checked" : ""} onchange="handleCandleCheckboxChange()">
          <span>${t.label} (${c.toLocaleString()}개)</span>
        </label>
      `;
    }).join("");

    if (candleLabel) {
      if (selectedArr.length === 0) {
        candleLabel.innerText = "캔들 선택 없음 (0개)";
      } else if (selectedArr.length === CANDLE_TYPES.length) {
        candleLabel.innerText = `전체 캔들 형태 (${total.toLocaleString()}개)`;
      } else if (selectedArr.length === 1) {
        const count = counts[selectedArr[0]] || 0;
        candleLabel.innerText = `${selectedArr[0]} (${count.toLocaleString()}개)`;
      } else {
        candleLabel.innerText = `${selectedArr.join(", ")} (${selectedArr.length}개 선택)`;
      }
    }
  }

  // Update Overheat Select Combobox Options with Live Counts
  const overheatSelect = document.getElementById("overheatSelectFilter");
  if (overheatSelect) {
    const normalCount = allStockData.filter(d => (d.과열여부 || "").includes("적정") || (!(d.과열여부 || "").includes("과열") && !(d.과열여부 || "").includes("이격"))).length;
    const riseCount = allStockData.filter(d => (d.과열여부 || "").includes("상승과열")).length;
    const shortOverheatCount = allStockData.filter(d => (d.과열여부 || "").includes("단기과열")).length;
    const gapOverheatCount = allStockData.filter(d => (d.과열여부 || "").includes("이격과도")).length;

    const curOverheatVal = currentOverheatFilter;
    overheatSelect.innerHTML = `
      <option value="ALL">전체 과열 판정 (${total.toLocaleString()}개)</option>
      <option value="적정">🟢 적정 (안전) (${normalCount.toLocaleString()}개)</option>
      <option value="상승과열">🟡 상승과열 (${riseCount.toLocaleString()}개)</option>
      <option value="단기과열">🔴 단기과열 (${shortOverheatCount.toLocaleString()}개)</option>
      <option value="이격과도">🔵 이격과도 (${gapOverheatCount.toLocaleString()}개)</option>
    `;
    overheatSelect.value = curOverheatVal;
  }
}

/**
 * 5. 주요 섹터/테마별 카드 그리드 생성
 */
function renderSectorGrid() {
  const container = document.getElementById("sectorGrid");
  if (!container) return;
  container.innerHTML = "";

  const sectorCounts = {};
  allStockData.forEach(d => {
    const sec = d.섹터 || "일반 주도주";
    if (!sectorCounts[sec]) {
      sectorCounts[sec] = { total: 0, aplus: 0, a: 0 };
    }
    sectorCounts[sec].total++;
    if (d.투자등급 === "A+") sectorCounts[sec].aplus++;
    if (d.투자등급 === "A") sectorCounts[sec].a++;
  });

  // 섹터 모멘텀 점수(A+ * 3.0 + A * 1.0) 순으로 정렬하여 주도 섹터 하이라이트
  const sortedSectors = Object.entries(sectorCounts).sort((a, b) => {
    const scoreA = (a[1].aplus * 3.0) + (a[1].a * 1.0) + (a[1].total * 0.01);
    const scoreB = (b[1].aplus * 3.0) + (b[1].a * 1.0) + (b[1].total * 0.01);
    return scoreB - scoreA;
  });

  sortedSectors.forEach(([secName, counts], idx) => {
    const card = document.createElement("div");
    card.className = "sector-card";
    if (idx < 3) {
      card.style.borderColor = "var(--color-gold, #f59e0b)";
      card.style.boxShadow = "0 0 12px rgba(245, 158, 11, 0.15)";
    }
    card.onclick = () => filterBySectorCard(secName);
    
    const rankBadge = idx === 0 ? "🥇 1위 주도섹터" : (idx === 1 ? "🥈 2위 주도섹터" : (idx === 2 ? "🥉 3위 주도섹터" : ""));
    const rankHtml = rankBadge ? `<span style="font-size:0.75rem; font-weight:700; color:#f59e0b; margin-bottom:4px; display:block;">${rankBadge}</span>` : "";

    card.innerHTML = `
      ${rankHtml}
      <div class="sector-card-top">
        <span class="sector-name" style="font-weight:700;">${secName}</span>
        <span class="sector-total-badge">${counts.total}개 종목</span>
      </div>
      <div class="sector-pills" style="margin-top:6px;">
        <div class="sector-pill-item aplus" style="font-weight:600;">🔥 A+ ${counts.aplus}개</div>
        <div class="sector-pill-item a" style="font-weight:600;">⭐ A ${counts.a}개</div>
      </div>
    `;
    container.appendChild(card);
  });
}

/**
 * 7. 드롭다운 필터 옵션 동적 생성
 */
function populateSectorSelectFilter() {
  const select = document.getElementById("sectorSelectFilter");
  if (!select) return;
  select.innerHTML = '<option value="ALL">전체 섹터 보기</option>';

  const sectors = [...new Set(allStockData.map(d => d.섹터))].filter(Boolean).sort();
  sectors.forEach(sec => {
    const opt = document.createElement("option");
    opt.value = sec;
    opt.innerText = sec;
    select.appendChild(opt);
  });
}

/**
 * 8. 필터링 및 데이터 테이블 렌더링
 */
function applyFiltersAndRenderTable() {
  filteredStockData = allStockData.filter(item => {
    // 1. Grade filter
    if (currentGradeFilter !== "ALL" && item.투자등급 !== currentGradeFilter) return false;

    // 1-2. Buy signal filter (매수신호 열이 없는 예전 리포트는 A/B/C 어느 것에도 해당하지 않는다)
    if (currentSignalFilter !== "ALL" && !(item.매수신호 || "").startsWith(currentSignalFilter)) return false;

    // 2. Candle tail filter (Multi-select array support)
    if (currentCandleFilter !== "ALL") {
      const selectedArr = Array.isArray(currentCandleFilter) ? currentCandleFilter : [currentCandleFilter];
      if (selectedArr.length === 0) {
        return false;
      } else if (selectedArr.length < CANDLE_TYPES.length) {
        // 차트 꼬리 값이 없는 종목은 걸러낼 근거가 없으므로 통과시킨다
        const cStr = item.차트꼬리 || "";
        const matches = selectedArr.some(target => cStr.includes(target));
        if (cStr && !matches) return false;
      }
    }

    // 3. Overheat status filter
    if (currentOverheatFilter !== "ALL") {
      const oStr = item.과열여부 || "적정";
      if (currentOverheatFilter === "적정") {
        if (oStr.includes("단기과열") || oStr.includes("상승과열") || oStr.includes("이격과도")) return false;
      } else {
        if (!oStr.includes(currentOverheatFilter)) return false;
      }
    }
    
    // 4. Search query
    if (currentSearchQuery) {
      const q = currentSearchQuery.toLowerCase();
      const matchName = item.종목명.toLowerCase().includes(q);
      const matchCode = item.종목코드.toLowerCase().includes(q);
      if (!matchName && !matchCode) return false;
    }

    return true;
  });

  // Table Sort (1순위: 투자등급 A+->A->B->C, 2순위: 과열여부 적정/안전 우선)
  const gradeRank = { "A+": 1, "A": 2, "B": 3, "C": 4 };
  const overheatRank = (ohStr) => {
    if (!ohStr || ohStr.includes("적정")) return 1;
    if (ohStr.includes("이격과도")) return 2;
    if (ohStr.includes("상승과열")) return 3;
    if (ohStr.includes("단기과열")) return 4;
    return 5;
  };

  filteredStockData.sort((a, b) => {
    let valA, valB;

    if (sortKey === "투자등급") {
      valA = gradeRank[a.투자등급] || 99;
      valB = gradeRank[b.투자등급] || 99;
      
      // 1차: 투자등급 비교
      if (valA !== valB) {
        return sortAsc ? valA - valB : valB - valA;
      }

      // 2차: 과열여부 비교 (적정/안전 종목 우선 배치)
      const oA = overheatRank(a.과열여부);
      const oB = overheatRank(b.과열여부);
      if (oA !== oB) {
        return oA - oB;
      }

      // 3차: 20일이격도 비교
      const iA = parseFloat((a["20일이격도"] || "0").replace(/%/g, "") || 0);
      const iB = parseFloat((b["20일이격도"] || "0").replace(/%/g, "") || 0);
      return iA - iB;

    } else if (sortKey === "과열여부") {
      valA = overheatRank(a.과열여부);
      valB = overheatRank(b.과열여부);
      
      if (valA !== valB) {
        return sortAsc ? valA - valB : valB - valA;
      }

      // 2차: 투자등급 비교
      const gA = gradeRank[a.투자등급] || 99;
      const gB = gradeRank[b.투자등급] || 99;
      return gA - gB;

    } else if (sortKey === "매수신호") {
      // A(매수) -> B(재검토) -> C(매수금지) -> 신호 없음(-) 순
      const signalRank = (sig) => ({ "A": 1, "B": 2, "C": 3 }[(sig || "").charAt(0)] || 4);
      valA = signalRank(a.매수신호);
      valB = signalRank(b.매수신호);
    } else if (sortKey === "현재가") {
      valA = parseInt((a.현재가 || "0").replace(/,/g, "") || 0, 10);
      valB = parseInt((b.현재가 || "0").replace(/,/g, "") || 0, 10);
    } else if (sortKey === "등락률") {
      valA = parseFloat((a.등락률 || "0").replace(/[+%,]/g, "") || 0);
      valB = parseFloat((b.등락률 || "0").replace(/[+%,]/g, "") || 0);
    } else if (sortKey === "20일이격도") {
      valA = parseFloat((a["20일이격도"] || "0").replace(/%/g, "") || 0);
      valB = parseFloat((b["20일이격도"] || "0").replace(/%/g, "") || 0);
    } else if (sortKey === "차트꼬리") {
      valA = a.차트꼬리 || "";
      valB = b.차트꼬리 || "";
    } else {
      valA = a[sortKey] || "";
      valB = b[sortKey] || "";
    }

    if (valA < valB) return sortAsc ? -1 : 1;
    if (valA > valB) return sortAsc ? 1 : -1;
    return 0;
  });

  const visibleRowCount = document.getElementById("visibleRowCount");
  if (visibleRowCount) visibleRowCount.innerText = filteredStockData.length.toLocaleString();
  
  // Render Current Page
  renderTableRows();
  renderPagination();
}

/**
 * 9. 테이블 행 렌더링 (페이지네이션 적용)
 */
function renderTableRows() {
  const tbody = document.getElementById("tableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  const startIndex = (currentPage - 1) * pageSize;
  const pageRows = filteredStockData.slice(startIndex, startIndex + pageSize);

  if (pageRows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="19" style="text-align: center; padding: 2rem; color: var(--text-dim);">검색 및 필터 조건에 부합하는 종목이 없습니다.</td></tr>`;
    return;
  }

  pageRows.forEach(row => {
    const tr = document.createElement("tr");
    
    let gradeBadgeClass = "grade-c";
    if (row.투자등급 === "A+") gradeBadgeClass = "grade-aplus";
    else if (row.투자등급 === "A") gradeBadgeClass = "grade-a";
    else if (row.투자등급 === "B") gradeBadgeClass = "grade-b";

    const dualBadge = row.쌍끌이여부 === "O" 
      ? '<span class="badge-dual yes">쌍끌이</span>' 
      : '<span class="badge-dual no">-</span>';

    // 매수신호 (이 열이 없는 예전 리포트는 "-" 로 표시)
    const buySignal = row.매수신호 || "-";
    const buyReason = row.매수신호사유 || "";
    let buySignalClass = "signal-none";
    if (buySignal.startsWith("A")) buySignalClass = "signal-buy";
    else if (buySignal.startsWith("B")) buySignalClass = "signal-review";
    else if (buySignal.startsWith("C")) buySignalClass = "signal-avoid";

    const overheatText = row.과열여부 || "적정(안전)";
    let overheatBadge = '<span style="color:#10b981; font-weight:600;"><i class="fa-solid fa-shield-check"></i> 적정(안전)</span>';
    if (overheatText.includes("단기과열")) {
      overheatBadge = '<span style="color:#ef4444; font-weight:600;"><i class="fa-solid fa-triangle-exclamation"></i> 단기과열</span>';
    } else if (overheatText.includes("상승과열")) {
      overheatBadge = '<span style="color:#f59e0b; font-weight:600;"><i class="fa-solid fa-fire"></i> 상승과열</span>';
    } else if (overheatText.includes("이격과도")) {
      overheatBadge = '<span style="color:#6366f1; font-weight:600;"><i class="fa-solid fa-arrow-trend-down"></i> 이격과도</span>';
    }

    // 차트 꼬리: 4단계가 일봉으로 계산한 값. 예전 리포트처럼 값이 없으면 "-"
    const candleShape = row.차트꼬리 || "";
    const candleColors = {
      "장대양봉": "#ef4444", "보통 양봉": "#f87171", "긴 아래꼬리": "#10b981",
      "십자형": "#f59e0b", "긴 윗꼬리": "#6366f1", "보통 음봉": "#60a5fa", "장대음봉": "#3b82f6"
    };
    const candleBadge = candleShape
      ? `<span style="color:${candleColors[candleShape] || "var(--text-muted)"}; font-weight:600; font-size:0.82rem;">${candleShape}</span>`
      : `<span style="font-size:0.82rem; color:var(--text-dim);">-</span>`;

    const rateVal = row.등락률 || "0.00%";
    const rateColor = rateVal.includes('+') ? '#ef4444' : (rateVal.includes('-') ? '#3b82f6' : 'var(--text-main)');

    tr.innerHTML = `
      <td><code class="stock-code-clickable" onclick="openStockDetail('${row.종목코드}')" title="클릭 시 ${row.종목명} 상세 분석 페이지로 이동">${row.종목코드}</code></td>
      <td><strong class="stock-name-clickable" onclick="openStockDetail('${row.종목코드}')">${row.종목명}</strong></td>
      <td><span class="stock-sector-tag">${row.섹터}</span></td>
      <td><span class="badge-grade ${gradeBadgeClass}">${row.투자등급}</span></td>
      <td title="${buyReason}"><span class="badge-signal ${buySignalClass}">${buySignal}</span>${buyReason ? `<div class="signal-reason">${buyReason}</div>` : ""}</td>
      <td>${row.등급변동}</td>
      <td><span style="font-size:0.82rem; color:var(--text-muted);">${row.변동이유 || "-"}</span></td>
      <td>${candleBadge}</td>
      <td><span class="count-pill">${row["20일이격도"] || "100.0%"}</span></td>
      <td>${overheatBadge}</td>
      <td><span class="stock-sector-tag" style="background: rgba(255,255,255,0.06); color: var(--text-main); font-weight: 600;">${row.추세단계 || "관망(C)"}</span></td>
      <td><strong>${row.현재가}원</strong></td>
      <td><strong style="color: ${rateColor};">${rateVal}</strong></td>
      <td>${dualBadge}</td>
      <td>${row.외국인연속 || row["외국인연속매수(일)"] || 0}일</td>
      <td>${row.기관연속 || row["기관연속매수(일)"] || 0}일</td>
      <td>${row["20일선위"] === "O" ? "🟢 O" : "🔴 X"}</td>
      <td>${row.정배열여부 === "O" ? "🟢 O" : "🔴 X"}</td>
      <td><a href="${row.상세페이지}" target="_blank" class="link-naver">네이버 <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:0.75rem;"></i></a></td>
    `;
    tbody.appendChild(tr);
  });
}

/**
 * 10. 페이지네이션 버튼 렌더링
 */
function renderPagination() {
  const container = document.getElementById("paginationControls");
  container.innerHTML = "";

  const totalPages = Math.ceil(filteredStockData.length / pageSize);
  if (totalPages <= 1) return;

  for (let i = 1; i <= totalPages; i++) {
    const btn = document.createElement("button");
    btn.className = `page-btn ${i === currentPage ? "active" : ""}`;
    btn.innerText = i;
    btn.onclick = () => {
      currentPage = i;
      renderTableRows();
      renderPagination();
    };
    container.appendChild(btn);
  }
}

/**
 * 11. 이벤트 핸들러 함수들
 */
function setGradeFilter(grade) {
  currentGradeFilter = grade;
  currentPage = 1;

  document.querySelectorAll("#gradeFilterTabs .filter-tab").forEach(tab => {
    tab.classList.toggle("active", tab.dataset.grade === grade);
  });

  applyFiltersAndRenderTable();
}

function setGradeFilter(grade) {
  currentGradeFilter = grade;
  currentPage = 1;

  const select = document.getElementById("gradeSelectFilter");
  if (select) select.value = grade;

  applyFiltersAndRenderTable();
}

function handleGradeSelectChange() {
  const select = document.getElementById("gradeSelectFilter");
  if (!select) return;
  currentGradeFilter = select.value;
  currentPage = 1;
  applyFiltersAndRenderTable();
}

function handleSignalSelectChange() {
  const select = document.getElementById("signalSelectFilter");
  if (!select) return;
  currentSignalFilter = select.value;
  currentPage = 1;
  applyFiltersAndRenderTable();
}

function toggleCandleDropdown(e) {
  if (e) e.stopPropagation();
  const container = document.getElementById("candleMultiSelectContainer");
  if (container) container.classList.toggle("open");
}

document.addEventListener("click", (e) => {
  const container = document.getElementById("candleMultiSelectContainer");
  if (container && !container.contains(e.target)) {
    container.classList.remove("open");
  }
});

function handleCandleAllToggle(isChecked) {
  if (isChecked) {
    currentCandleFilter = CANDLE_TYPES.map(c => c.id);
  } else {
    currentCandleFilter = [];
  }
  currentPage = 1;
  updateFilterCounts();
  applyFiltersAndRenderTable();
}

function handleCandleCheckboxChange() {
  const container = document.getElementById("candleOptionList");
  if (!container) return;
  const checkboxes = container.querySelectorAll("input[type='checkbox']");
  const selected = [];
  checkboxes.forEach(chk => {
    if (chk.checked) selected.push(chk.value);
  });
  currentCandleFilter = selected;
  currentPage = 1;
  updateFilterCounts();
  applyFiltersAndRenderTable();
}

function handleOverheatSelectChange() {
  const select = document.getElementById("overheatSelectFilter");
  if (!select) return;
  currentOverheatFilter = select.value;
  currentPage = 1;
  applyFiltersAndRenderTable();
}

function handleFilterChange() {
  currentPage = 1;
  applyFiltersAndRenderTable();
}

function handleSearchInput() {
  const searchInput = document.getElementById("searchInput");
  if (searchInput) currentSearchQuery = searchInput.value.trim();
  currentPage = 1;
  applyFiltersAndRenderTable();
}

function executeSearchQuery() {
  const searchInput = document.getElementById("searchInput");
  if (searchInput) currentSearchQuery = searchInput.value.trim();
  currentPage = 1;
  applyFiltersAndRenderTable();
}

function goHome() {
  currentGradeFilter = DEFAULT_GRADE_FILTER;
  currentSignalFilter = DEFAULT_SIGNAL_FILTER;
  currentCandleFilter = [...DEFAULT_CANDLE_FILTER];
  currentOverheatFilter = DEFAULT_OVERHEAT_FILTER;
  currentSearchQuery = "";
  currentPage = 1;

  const searchInput = document.getElementById("searchInput");
  if (searchInput) searchInput.value = "";

  switchView('dashboard');
  updateFilterCounts();
  applyFiltersAndRenderTable();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function filterByGradeQuick(grade) {
  switchView('dashboard');
  setGradeFilter(grade);
}

function filterByUpgradeQuick() {
  switchView('dashboard');
  currentSearchQuery = "상향";
  const searchInput = document.getElementById("searchInput");
  if (searchInput) searchInput.value = "상향";
  applyFiltersAndRenderTable();
}

function filterBySectorCard(secName) {
  switchView('dashboard');
  currentSearchQuery = secName;
  const searchInput = document.getElementById("searchInput");
  if (searchInput) searchInput.value = secName;
  applyFiltersAndRenderTable();
}

function sortTable(key) {
  if (sortKey === key) {
    sortAsc = !sortAsc;
  } else {
    sortKey = key;
    sortAsc = true;
  }
  applyFiltersAndRenderTable();
}

function goBackToDashboard() {
  switchView('dashboard');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

window.addEventListener("popstate", (e) => {
  if (e.state && e.state.view === 'stockDetail' && e.state.code) {
    openStockDetail(e.state.code, false);
  } else {
    switchView('dashboard');
  }
});

/**
 * 12. 뷰 전환 및 AI 마크다운 리포트 / 종목 상세 로딩
 */
function switchView(viewName) {
  document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));

  if (viewName === 'dashboard') {
    document.getElementById("viewDashboard").classList.add("active");
    document.getElementById("navBtnMain").classList.add("active");
  } else if (viewName === 'strategy') {
    document.getElementById("viewStrategy").classList.add("active");
    const navBtn = document.getElementById("navBtnStrategy");
    if (navBtn) navBtn.classList.add("active");
    loadStrategyContent();
  } else if (viewName === 'report') {
    document.getElementById("viewReport").classList.add("active");
  } else if (viewName === 'stockDetail') {
    document.getElementById("viewStockDetail").classList.add("active");
  } else if (viewName === 'priorityStrategy') {
    const pView = document.getElementById("viewPriorityStrategy");
    if (pView) pView.classList.add("active");
    const navBtn = document.getElementById("navBtnPriority");
    if (navBtn) navBtn.classList.add("active");
    loadPriorityStrategyContent();
  }
}

function loadStrategyContent() {
  const renderBox = document.getElementById("strategyMarkdownRenderBox");
  if (!renderBox) return;

  renderBox.innerHTML = `<div class="report-loading"><i class="fa-solid fa-spinner fa-spin"></i> 추세추종 매매 전략 HTML을 불러오는 중입니다...</div>`;

  fetch('docs/stockDesc1.html')
    .then(res => {
      if (!res.ok) throw new Error("STRATEGY_HTML_NOT_FOUND");
      return res.text();
    })
    .then(htmlText => {
      // HTML 내용에서 body 내부 컨테이너만 추출하거나 전체 바인딩
      const parser = new DOMParser();
      const doc = parser.parseFromString(htmlText, 'text/html');
      const container = doc.querySelector('.strategy-container');
      const styleTags = Array.from(doc.querySelectorAll('style')).map(s => s.outerHTML).join('\n');
      
      if (container) {
        renderBox.innerHTML = styleTags + container.outerHTML;
      } else {
        renderBox.innerHTML = htmlText;
      }

      if (window.mermaid) {
        try {
          mermaid.run({ nodes: renderBox.querySelectorAll('.language-mermaid, .mermaid') });
        } catch (e) {
          console.warn("Mermaid render warning:", e);
        }
      }
    })
    .catch(err => {
      renderBox.innerHTML = `<div style="color: #ef4444; padding: 2rem; text-align: center;">❌ 추세추종 매매 전략 HTML을 불러오지 못했습니다. (${err.message})</div>`;
    });
}

function loadPriorityStrategyContent() {
  const renderBox = document.getElementById("priorityStrategyRenderBox");
  if (!renderBox) return;

  renderBox.innerHTML = `<div class="report-loading"><i class="fa-solid fa-spinner fa-spin"></i> 매수 우선순위 가이드 HTML을 불러오는 중입니다...</div>`;

  fetch('docs/stockDesc2.html')
    .then(res => {
      if (!res.ok) throw new Error("PRIORITY_HTML_NOT_FOUND");
      return res.text();
    })
    .then(htmlText => {
      const parser = new DOMParser();
      const doc = parser.parseFromString(htmlText, 'text/html');
      const container = doc.querySelector('.strategy-container');
      const styleTags = Array.from(doc.querySelectorAll('style')).map(s => s.outerHTML).join('\n');
      
      if (container) {
        renderBox.innerHTML = styleTags + container.outerHTML;
      } else {
        renderBox.innerHTML = htmlText;
      }
    })
    .catch(err => {
      renderBox.innerHTML = `<div style="color: #ef4444; padding: 2rem; text-align: center;">❌ 매수 우선순위 전략 HTML을 불러오지 못했습니다. (${err.message})</div>`;
    });
}

function selectDateReport(dateStr) {
  currentDate = dateStr;
  initDatePickers(dateStr);
  switchView('report');

  const formattedDate = `${dateStr.slice(0, 4)}년 ${dateStr.slice(4, 6)}월 ${dateStr.slice(6, 8)}일`;
  document.getElementById("reportPageDateTag").innerText = formattedDate;

  const mdPath = `reports/report_${dateStr}.md`;
  const renderBox = document.getElementById("markdownRenderBox");
  renderBox.innerHTML = `<div class="report-loading"><i class="fa-solid fa-spinner fa-spin"></i> 마크다운 리포트를 불러오는 중입니다...</div>`;

  fetchLocalFile(mdPath)
    .then(text => {
      renderBox.innerHTML = marked.parse(text);
    })
    .catch(err => {
      renderBox.innerHTML = `<div style="text-align:center; padding: 3rem; color: var(--text-muted);"><i class="fa-solid fa-file-excel" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>해당 일자의 마크다운 리포트가 존재하지 않습니다.</div>`;
    });
}

/**
 * 13. 개별 종목 상세 분석 페이지 오픈 & 차트 렌더링
 */
let currentChartInstance = null;

function openStockDetail(code, pushHistory = true) {
  const stock = allStockData.find(s => s.종목코드 === code);
  if (!stock) return;

  if (pushHistory && window.history && window.history.pushState) {
    try {
      window.history.pushState({ view: 'stockDetail', code: code }, '', `#stock-${code}`);
    } catch(e) {}
  }

  // 헤더 요약 정보 업데이트
  document.getElementById("detailStockCode").innerText = stock.종목코드;
  document.getElementById("detailStockName").innerText = stock.종목명;
  document.getElementById("detailStockSector").innerText = stock.섹터;
  document.getElementById("detailStockPrice").innerText = `${stock.현재가}원`;
  document.getElementById("detailStockNaverLink").href = stock.상세페이지;
  
  const gradeBadge = document.getElementById("detailStockGradeBadge");
  gradeBadge.innerText = stock.투자등급;
  let gradeClass = "grade-c";
  if (stock.투자등급 === "A+") gradeClass = "grade-aplus";
  else if (stock.투자등급 === "A") gradeClass = "grade-a";
  else if (stock.투자등급 === "B") gradeClass = "grade-b";
  gradeBadge.className = `badge-grade ${gradeClass}`;

  const dualBadge = document.getElementById("detailStockDualBadge");
  if (stock.쌍끌이여부 === "O") {
    dualBadge.className = "badge-dual yes";
    dualBadge.innerText = "🤝 외인/기관 쌍끌이 유입";
  } else {
    dualBadge.className = "badge-dual no";
    dualBadge.innerText = "쌍끌이 미달";
  }

  // 지표 카드 세부 수치 업데이트
  document.getElementById("detailForeignSeq").innerText = `${stock.외국인연속 || stock["외국인연속매수(일)"] || 0}일 연속`;
  document.getElementById("detailForeignSum").innerText = `최근 3일: ${stock["최근3일외인순매수"] || 0}주`;
  document.getElementById("detailOrganSeq").innerText = `${stock.기관연속 || stock["기관연속매수(일)"] || 0}일 연속`;
  document.getElementById("detailOrganSum").innerText = `최근 3일: ${stock["최근3일기관순매수"] || 0}주`;
  document.getElementById("detailForeignRatio").innerText = stock.외국인보유율;
  
  document.getElementById("detailMaStatus").innerText = stock.정배열여부 === "O" ? "🟢 완전 정배열 달성" : "🔴 정배열 미달";
  document.getElementById("detailMa20Status").innerText = stock["20일선위"] === "O" ? "20일선 위 (상승 추세)" : "20일선 미달 (관망)";

  const disparityVal = stock["20일이격도"] || "100.0%";
  const overheatVal = stock.과열여부 || "적정(안전)";
  const phaseVal = stock.추세단계 || "관망(C)";

  let overheatGuideText = "🟢 적정 (20일선 안심 눌림목 1차 진입 적기)";
  if (overheatVal.includes("단기과열")) {
    overheatGuideText = "🚨 단기과열 (추격 매수 및 추가 불타기 절대 금지!)";
  } else if (overheatVal.includes("상승과열")) {
    overheatGuideText = "🟡 상승과열 (신규 추격 자제 / 본전 스탑로스 설정)";
  } else if (overheatVal.includes("이격과도")) {
    overheatGuideText = "🔵 이격과도 (20일선 재돌파 전까지 관망)";
  }

  document.getElementById("detailDisparity").innerText = disparityVal;
  document.getElementById("detailOverheat").innerText = overheatGuideText;
  document.getElementById("detailPhase").innerText = phaseVal;
  document.getElementById("detailBuySignal").innerText = `매수신호: ${stock.매수신호 || "-"}`;

  // 이평선 가격 수치
  document.getElementById("detailMa5").innerText = `${stock.MA5 || "0"}원`;
  document.getElementById("detailMa20").innerText = `${stock.MA20 || "0"}원`;
  document.getElementById("detailMa60").innerText = `${stock.MA60 || "0"}원`;
  document.getElementById("detailMa120").innerText = `${stock.MA120 || "0"}원`;

  // 뷰 전환 & 차트 출력
  switchView("stockDetail");
  window.scrollTo({ top: 0, behavior: 'smooth' });
  renderGradeHistoryChart(stock);
}

/**
 * Chart.js 이용 일별 등급 변화 추이 선 그래프 생성
 */
function renderGradeHistoryChart(stock) {
  const canvas = document.getElementById("gradeHistoryChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  if (currentChartInstance) {
    currentChartInstance.destroy();
  }

  const gradeMap = { "A+": 4, "A": 3, "B": 2, "C": 1 };
  
  // 11개 거래일 라벨 (MM-DD) 및 해당 날짜별 실제 등급 데이터
  const dates = availableDates.map(d => `${d.slice(4,6)}-${d.slice(6,8)}`);
  const dataPoints = availableDates.map(d => {
    if (stockHistoryCache[d] && stockHistoryCache[d][stock.종목코드]) {
      return gradeMap[stockHistoryCache[d][stock.종목코드]] || 1;
    }
    return gradeMap[stock.투자등급] || 1;
  });

  const gradient = ctx.createLinearGradient(0, 0, 0, 300);
  gradient.addColorStop(0, "rgba(16, 185, 129, 0.4)");
  gradient.addColorStop(1, "rgba(16, 185, 129, 0.0)");

  currentChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [{
        label: `${stock.종목명} 투자등급 추이`,
        data: dataPoints,
        borderColor: "#10b981",
        borderWidth: 3.5,
        pointBackgroundColor: "#10b981",
        pointBorderColor: "#ffffff",
        pointBorderWidth: 2,
        pointRadius: 6,
        pointHoverRadius: 9,
        tension: 0.3,
        fill: true,
        backgroundColor: gradient
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: {
        padding: { left: 10, right: 15, top: 15, bottom: 10 }
      },
      scales: {
        y: {
          min: 0,
          max: 5,
          ticks: {
            stepSize: 1,
            callback: function(val) {
              const numVal = Math.round(val);
              if (numVal === 4) return "🔥 A+ (대세주)";
              if (numVal === 3) return "⭐ A (우량주)";
              if (numVal === 2) return "🟡 B (관찰주)";
              if (numVal === 1) return "⚪ C (관망주)";
              return "";
            },
            color: "#cbd5e1",
            font: { size: 13, weight: "bold", family: "Inter, sans-serif" }
          },
          grid: {
            color: function(ctx) {
              if (ctx.tick && [1, 2, 3, 4].includes(Math.round(ctx.tick.value))) {
                return "rgba(255, 255, 255, 0.12)";
              }
              return "transparent";
            }
          }
        },
        x: {
          ticks: {
            color: "#94a3b8",
            font: { size: 11, weight: "600" }
          },
          grid: { color: "rgba(255, 255, 255, 0.05)" }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              const val = Math.round(context.parsed.y);
              const names = { 4: "A+ 등급 (쌍끌이 + 20일선위 + 정배열)", 3: "A 등급 (쌍끌이 + 20일선위)", 2: "B 등급 (수급/차트 1가지)", 1: "C 등급 (관망)" };
              return ` 투자등급: ${names[val] || val}`;
            }
          }
        }
      }
    }
  });
}
