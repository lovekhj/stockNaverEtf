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
let currentDate = getTodayDateStr();

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
const DEFAULT_SIGNAL_FILTER = "ALL";
const DEFAULT_CANDLE_FILTER = CANDLE_TYPES.map(c => c.id);

let currentSignalFilter = DEFAULT_SIGNAL_FILTER;
let currentCandleFilter = [...DEFAULT_CANDLE_FILTER];
let currentSearchQuery = "";
let selectedSector = null; // 섹터별 종목조회 화면에서 고른 섹터
let lastListView = "sector"; // 종목 상세나 날짜 선택 뒤에 돌아갈 목록 화면 (sector, leaders, journal, dashboard, virtual)
let virtualTrades = [];      // 가상 주식거래 장부 (reports/virtual_trades.csv) 전체
let selectedVirtualCode = null; // 가상 주식거래 화면에서 일별 기록을 보려고 고른 종목

// Pagination State
let currentPage = 1;
const pageSize = 25;

// Table Sort State
let sortKey = "매수신호";
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

  loadDateExplorer();
  loadDashboardData(currentDate);
  loadVirtualTrades();
});

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
  renderVirtualView();
  renderJournalView();
  switchView(lastListView);
  loadDashboardData(dateStr);
  renderCalendarGrid();
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

  updateFilterCounts();
  renderSectorView();
  renderLeadersView();
  renderJournalView();

  const tbody = document.getElementById("tableBody");
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="12" style="text-align: center; padding: 3.5rem 1rem; color: var(--text-muted); font-size: 0.95rem;">
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
function loadDashboardData(dateStr) {
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
            currentDate = dateStr;
            if (!availableDates.includes(dateStr)) {
              availableDates.push(dateStr);
            }
            allStockData = cleanData.map(item => {
              // 차트 꼬리: CSV에 값이 있을 때만 쓰고, 없으면 null (임의로 만들어 넣지 않는다)
              const rawCandle = item.차트꼬리 || item.캔들모양 || item.차트패턴;
              const candleShape = (rawCandle && rawCandle.trim() !== "-") ? rawCandle.trim() : null;

              return {
                ...item,
                종목코드: item.종목코드 ? item.종목코드.trim() : "",
                종목명: item.종목명 ? item.종목명.trim() : "",
                섹터: item.섹터 ? item.섹터.trim() : "-",
                차트꼬리: candleShape,
                등락률: (item.등락률 || "0.00%").trim().replace(/^--/, "-"),
                현재가: item.현재가 ? item.현재가.trim() : "0",
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
            updateFilterCounts();
            applyFiltersAndRenderTable();
            renderSectorView();
            renderLeadersView();
            renderJournalView();
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
 * 4-1. 필터 콤보박스(매수신호 / 캔들) 옵션별 실시간 개수 갱신
 */
function updateFilterCounts() {
  const total = allStockData.length;
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

}

/**
 * 6. 섹터별 종목조회: 섹터 순위 표와 선택한 섹터의 종목 표
 *    통과 여부·3개월 상승률·강한 마감은 4단계(getEtfInvestorFlow.py)가 리포트 CSV에 넣은 값을 그대로 쓴다
 */
function parsePercent(text) {
  const num = parseFloat(String(text || "").replace("%", ""));
  return isNaN(num) ? null : num;
}

function formatSignedPercent(value) {
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function percentColor(value) {
  if (value === null || value === 0) return "var(--text-main)";
  return value > 0 ? "#ef4444" : "#3b82f6";
}

function buildSectorRanking() {
  const sectors = {};
  allStockData.forEach(d => {
    if (!sectors[d.섹터]) sectors[d.섹터] = { name: d.섹터, total: 0, passed: [], signals: 0 };
    const sec = sectors[d.섹터];
    sec.total++;
    if (d.추세통과 === "O") {
      sec.passed.push(parsePercent(d["3개월수익률"]) || 0);
      if (d.강한마감 === "O") sec.signals++;
    }
  });

  return Object.values(sectors).map(sec => {
    const sorted = [...sec.passed].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length === 0 ? null
      : (sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2);
    return { ...sec, passCount: sorted.length, passRatio: sorted.length / sec.total, median };
  }).sort((a, b) => (b.passCount - a.passCount) || (b.passRatio - a.passRatio) || a.name.localeCompare(b.name));
}

function renderSectorView() {
  const rankBody = document.getElementById("sectorRankBody");
  const stockBody = document.getElementById("sectorStockBody");
  if (!rankBody || !stockBody) return;

  // 추세통과 열이 없는 예전 리포트
  if (!allStockData.some(d => d.추세통과 === "O" || d.추세통과 === "X")) {
    rankBody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem; color: var(--text-dim);">이 날짜의 리포트에는 섹터 통계가 없습니다.</td></tr>`;
    stockBody.innerHTML = "";
    document.getElementById("sectorStockTitle").innerText = "섹터 종목";
    return;
  }

  const ranking = buildSectorRanking();
  if (!ranking.some(sec => sec.name === selectedSector)) selectedSector = ranking[0].name;

  rankBody.innerHTML = "";
  ranking.forEach((sec, idx) => {
    const tr = document.createElement("tr");
    if (sec.name === selectedSector) tr.className = "sector-row-selected";
    tr.onclick = () => { selectedSector = sec.name; renderSectorView(); };
    tr.innerHTML = `
      <td>${idx + 1}</td>
      <td><strong>${sec.name}</strong></td>
      <td><strong>${sec.passCount}</strong></td>
      <td>${sec.total}</td>
      <td>${(sec.passRatio * 100).toFixed(0)}%</td>
      <td>${sec.median === null ? "-" : `<strong style="color: ${percentColor(sec.median)};">${formatSignedPercent(sec.median)}</strong>`}</td>
      <td>${sec.signals > 0 ? `★ ${sec.signals}` : "-"}</td>
    `;
    rankBody.appendChild(tr);
  });

  renderSectorStocks();
}

function renderSectorStocks() {
  const stockBody = document.getElementById("sectorStockBody");
  const rows = allStockData.filter(d => d.섹터 === selectedSector).sort((a, b) => {
    const passDiff = (b.추세통과 === "O") - (a.추세통과 === "O");
    if (passDiff) return passDiff;
    return (parsePercent(b["3개월수익률"]) ?? -Infinity) - (parsePercent(a["3개월수익률"]) ?? -Infinity);
  });

  const passCount = rows.filter(d => d.추세통과 === "O").length;
  document.getElementById("sectorStockTitle").innerText = `${selectedSector} (통과 ${passCount}개 / 전체 ${rows.length}개)`;

  stockBody.innerHTML = "";
  rows.forEach((row, idx) => stockBody.appendChild(buildSectorStockRow(row, idx + 1, true)));
}

/**
 * 섹터 종목 표와 주도주 표가 함께 쓰는 한 줄. showPass 가 false 면 통과 칸을 뺀다 (주도주는 모두 통과 종목)
 */
function buildSectorStockRow(row, rank, showPass) {
    const ret3m = parsePercent(row["3개월수익률"]);
    const fromHigh = parsePercent(row.고점대비);
    const rateVal = row.등락률 || "0.00%";

    const buySignal = row.매수신호 || "-";
    let buySignalClass = "signal-none";
    if (buySignal.startsWith("A")) buySignalClass = "signal-buy";
    else if (buySignal.startsWith("B")) buySignalClass = "signal-review";
    else if (buySignal.startsWith("C")) buySignalClass = "signal-avoid";

    const tr = document.createElement("tr");
    if (row.추세통과 !== "O") tr.className = "sector-stock-failed";
    tr.innerHTML = `
      <td>${rank}</td>
      <td><code class="stock-code-clickable" onclick="openStockDetail('${row.종목코드}')">${row.종목코드}</code></td>
      <td><strong class="stock-name-clickable" onclick="openStockDetail('${row.종목코드}')">${row.종목명}</strong></td>
      <td>${row.시장 || "-"}</td>
      ${showPass ? `<td>${row.추세통과 === "O" ? "🟢 O" : (row.추세통과 === "X" ? "🔴 X" : "-")}</td>` : ""}
      <td><strong style="color: ${percentColor(ret3m)};">${row["3개월수익률"] || "-"}</strong></td>
      <td>${fromHigh === null ? "-" : formatSignedPercent(fromHigh)}</td>
      <td>${row.강한마감 === "O" ? '<strong class="sector-star">★</strong>' : "-"}</td>
      <td><strong>${row.현재가}원</strong></td>
      <td><strong style="color: ${percentColor(parsePercent(rateVal))};">${rateVal}</strong></td>
      <td title="${row.매수신호사유 || ""}"><span class="badge-signal ${buySignalClass}">${buySignal}</span></td>
      <td><a href="${row.상세페이지}" target="_blank" class="link-naver">네이버 <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:0.75rem;"></i></a></td>
    `;
    return tr;
}

/**
 * 6-1. 주도주: 순위가 높은 섹터부터, 통과 종목을 3개월 상승률이 큰 순서로 보여 준다
 */
function renderLeadersView() {
  const body = document.getElementById("leaderBody");
  if (!body) return;
  const countEl = document.getElementById("leaderCount");
  body.innerHTML = "";
  countEl.innerText = "0";

  // 추세통과 열이 없는 예전 리포트
  if (!allStockData.some(d => d.추세통과 === "O" || d.추세통과 === "X")) {
    body.innerHTML = `<tr><td colspan="11" style="text-align: center; padding: 2rem; color: var(--text-dim);">이 날짜의 리포트에는 섹터 통계가 없습니다.</td></tr>`;
    return;
  }

  const sectorLimit = document.getElementById("leaderSectorCount").value;
  const stockLimit = parseInt(document.getElementById("leaderStockCount").value, 10);
  const market = document.getElementById("leaderMarket").value;

  // 섹터 순위는 시장 선택과 관계없이 전체 종목으로 매긴다
  let ranking = buildSectorRanking().map((sec, idx) => ({ ...sec, rank: idx + 1 })).filter(sec => sec.passCount > 0);
  if (sectorLimit !== "ALL") ranking = ranking.slice(0, parseInt(sectorLimit, 10));

  let total = 0;
  ranking.forEach(sec => {
    const leaders = allStockData
      .filter(d => d.섹터 === sec.name && d.추세통과 === "O" && (market === "ALL" || d.시장 === market))
      .sort((a, b) => (parsePercent(b["3개월수익률"]) ?? -Infinity) - (parsePercent(a["3개월수익률"]) ?? -Infinity))
      .slice(0, stockLimit);

    const head = document.createElement("tr");
    head.className = "leader-sector-row";
    head.innerHTML = `<td colspan="11"><strong>${sec.rank}위 ${sec.name}</strong> <span>통과 ${sec.passCount}개 / 전체 ${sec.total}개</span></td>`;
    body.appendChild(head);

    if (leaders.length === 0) {
      const empty = document.createElement("tr");
      empty.innerHTML = `<td colspan="11" style="color: var(--text-dim);">${market} 통과 종목이 없습니다.</td>`;
      body.appendChild(empty);
    }
    leaders.forEach((row, idx) => body.appendChild(buildSectorStockRow(row, idx + 1, false)));
    total += leaders.length;
  });
  countEl.innerText = total.toLocaleString();
}

/**
 * 6-1b. 하루 일지: 기준일에 무엇이 어떻게 움직였는지를 리포트 CSV 의 숫자로 적는다 (이유는 적지 않는다)
 */
function renderJournalView() {
  const sectorBody = document.getElementById("journalSectorBody");
  if (!sectorBody) return;

  const dateLabel = `${currentDate.slice(0, 4)}-${currentDate.slice(4, 6)}-${currentDate.slice(6, 8)}`;
  document.getElementById("journalDateText").innerText = `(${dateLabel})`;
  const setText = (id, text, colorValue) => {
    const el = document.getElementById(id);
    el.innerText = text;
    el.style.color = colorValue === undefined ? "" : percentColor(colorValue);
  };
  const emptyRow = (cols, text) => `<tr><td colspan="${cols}" style="text-align: center; padding: 1.5rem; color: var(--text-dim);">${text}</td></tr>`;

  // 기준일에 거래가 있었던 종목만 센다 (추세통과 열이 "-" 인 종목은 그날 일봉이 없다)
  const rows = allStockData.filter(d => d.추세통과 === "O" || d.추세통과 === "X").map(d => ({ ...d, chg: parsePercent(d.등락률) || 0 }));
  if (rows.length === 0) {
    ["journalUpDown", "journalFlat", "journalAvgChange", "journalMedianChange", "journalPassCount", "journalPassDiff", "journalStrong"].forEach(id => setText(id, "-"));
    sectorBody.innerHTML = emptyRow(7, "이 날짜의 리포트에는 일지에 쓸 통계가 없습니다.");
    ["journalGainersBody", "journalLosersBody"].forEach(id => { document.getElementById(id).innerHTML = emptyRow(10, "-"); });
    document.getElementById("journalPassChangeBody").innerHTML = emptyRow(2, "-");
    renderJournalVirtual();
    return;
  }

  // 1. 시장 한 줄
  const up = rows.filter(d => d.chg > 0).length;
  const down = rows.filter(d => d.chg < 0).length;
  const sortedChg = rows.map(d => d.chg).sort((a, b) => a - b);
  const avg = sortedChg.reduce((sum, v) => sum + v, 0) / rows.length;
  const mid = Math.floor(rows.length / 2);
  const med = rows.length % 2 ? sortedChg[mid] : (sortedChg[mid - 1] + sortedChg[mid]) / 2;
  const passNow = rows.filter(d => d.추세통과 === "O");
  const hasPrev = rows.some(d => d.전일통과 === "O" || d.전일통과 === "X");
  const passPrevCount = rows.filter(d => d.전일통과 === "O").length;
  const signed = n => `${n > 0 ? "+" : ""}${n}`;

  setText("journalUpDown", `${up} / ${down}`);
  setText("journalFlat", `보합 ${rows.length - up - down}개 · 전체 ${rows.length}개`);
  setText("journalAvgChange", formatSignedPercent(avg), avg);
  setText("journalMedianChange", `중앙값 ${formatSignedPercent(med)}`);
  setText("journalPassCount", `${passNow.length}개`);
  setText("journalPassDiff", hasPrev ? `전일 ${passPrevCount}개 (${signed(passNow.length - passPrevCount)})` : "전일 값 없음");
  setText("journalStrong", `${rows.filter(d => d.강한마감 === "O").length}개 / ${rows.filter(d => (d.매수신호 || "").startsWith("A")).length}개`);

  // 2. 섹터 표
  const sectors = {};
  rows.forEach(d => { (sectors[d.섹터] = sectors[d.섹터] || []).push(d); });
  const nameWithChange = d => `${d.종목명} <strong style="color: ${percentColor(d.chg)};">${d.등락률}</strong>`;
  sectorBody.innerHTML = "";
  Object.entries(sectors)
    .map(([name, list]) => ({ name, list, avg: list.reduce((sum, d) => sum + d.chg, 0) / list.length }))
    .sort((a, b) => b.avg - a.avg)
    .forEach(sec => {
      const byChange = [...sec.list].sort((a, b) => b.chg - a.chg);
      const pass = sec.list.filter(d => d.추세통과 === "O").length;
      const passDiff = pass - sec.list.filter(d => d.전일통과 === "O").length;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${sec.name}</strong> <span style="color: var(--text-dim);">${sec.list.length}</span></td>
        <td><strong style="color: ${percentColor(sec.avg)};">${formatSignedPercent(sec.avg)}</strong></td>
        <td>${sec.list.filter(d => d.chg > 0).length} / ${sec.list.filter(d => d.chg < 0).length}</td>
        <td>${sec.list.filter(d => d.강한마감 === "O").length || "-"}</td>
        <td>${pass}${hasPrev ? ` <span style="color: ${percentColor(passDiff)};">(${signed(passDiff)})</span>` : ""}</td>
        <td>${nameWithChange(byChange[0])}</td>
        <td>${nameWithChange(byChange[byChange.length - 1])}</td>
      `;
      sectorBody.appendChild(tr);
    });

  // 3. 크게 움직인 종목
  const moverRow = d => {
    const buySignal = d.매수신호 || "-";
    const signalClass = { "A": "signal-buy", "B": "signal-review", "C": "signal-avoid" }[buySignal.charAt(0)] || "signal-none";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong class="stock-name-clickable" onclick="openStockDetail('${d.종목코드}')">${d.종목명}</strong></td>
      <td>${d.시장 || "-"}</td>
      <td><span class="stock-sector-tag">${d.섹터}</span></td>
      <td><strong style="color: ${percentColor(d.chg)};">${d.등락률}</strong></td>
      <td>${d.거래량배수 && d.거래량배수 !== "-" ? `${d.거래량배수}배` : "-"}</td>
      <td>${d.추세통과 === "O" ? "🟢 O" : "🔴 X"}</td>
      <td><strong style="color: ${percentColor(parsePercent(d["3개월수익률"]))};">${d["3개월수익률"] || "-"}</strong></td>
      <td>${d.고점대비 || "-"}</td>
      <td>${d.차트꼬리 || "-"}</td>
      <td><span class="badge-signal ${signalClass}">${buySignal}</span></td>
    `;
    return tr;
  };
  const byChangeAll = [...rows].sort((a, b) => b.chg - a.chg);
  const fill = (id, list) => { const body = document.getElementById(id); body.innerHTML = ""; list.forEach(d => body.appendChild(moverRow(d))); };
  fill("journalGainersBody", byChangeAll.slice(0, 10));
  fill("journalLosersBody", byChangeAll.slice(-10).reverse());

  // 4. 추세 통과 목록의 변화
  const changeBody = document.getElementById("journalPassChangeBody");
  if (!hasPrev) {
    changeBody.innerHTML = emptyRow(2, "이 날짜의 리포트에는 전일 통과 값이 없습니다.");
  } else {
    const listText = list => list.length
      ? list.sort((a, b) => b.chg - a.chg).map(d => `${d.종목명} <span style="color: var(--text-dim);">(${d.섹터}, </span><span style="color: ${percentColor(d.chg)};">${d.등락률}</span><span style="color: var(--text-dim);">)</span>`).join(", ")
      : "없음";
    const entered = rows.filter(d => d.추세통과 === "O" && d.전일통과 === "X");
    const left = rows.filter(d => d.추세통과 === "X" && d.전일통과 === "O");
    changeBody.innerHTML = `
      <tr><td><strong>새로 통과</strong> ${entered.length}개</td><td>${listText(entered)}</td></tr>
      <tr><td><strong>통과에서 빠짐</strong> ${left.length}개</td><td>${listText(left)}</td></tr>
    `;
  }

  renderJournalVirtual();
}

function renderJournalVirtual() {
  const body = document.getElementById("journalVirtualBody");
  const rows = virtualTrades.filter(row => row.날짜 === currentDate);
  if (rows.length === 0) {
    body.innerHTML = `<tr><td colspan="2" style="text-align: center; padding: 1.5rem; color: var(--text-dim);">이 날짜의 가상 거래 기록이 없습니다.</td></tr>`;
    return;
  }
  const num = text => Number(text) || 0;
  const names = status => {
    const list = rows.filter(row => row.상태 === status);
    return list.length ? list.map(row => status === "매수" ? row.종목명 : `${row.종목명} <span style="color: ${percentColor(parsePercent(row.수익률))};">${row.수익률}</span>`).join(", ") : "없음";
  };
  const holding = rows.filter(row => row.상태 !== "매도");
  const cost = holding.reduce((sum, row) => sum + num(row.매수가) * num(row.수량), 0);
  const value = holding.reduce((sum, row) => sum + num(row.평가금액), 0);
  const realized = virtualTrades.filter(row => row.상태 === "매도" && row.날짜 <= currentDate).reduce((sum, row) => sum + num(row.손익), 0);
  body.innerHTML = `
    <tr><td><strong>오늘 매수</strong> ${rows.filter(row => row.상태 === "매수").length}건</td><td>${names("매수")}</td></tr>
    <tr><td><strong>오늘 매도</strong> ${rows.filter(row => row.상태 === "매도").length}건</td><td>${names("매도")}</td></tr>
    <tr><td><strong>보유</strong> ${holding.length}종목</td><td>원금 ${formatWon(cost)} · 평가손익 <strong style="color: ${percentColor(value - cost)};">${formatSignedWon(value - cost)}</strong> · 누적 실현손익 <strong style="color: ${percentColor(realized)};">${formatSignedWon(realized)}</strong></td></tr>
  `;
}

/**
 * 6-2. 가상 주식거래 리포트: virtualTrade.py 가 쌓는 장부(reports/virtual_trades.csv)를 날짜별로 보여 준다
 */
function loadVirtualTrades() {
  fetchLocalFile("reports/virtual_trades.csv")
    .then(csvText => {
      Papa.parse(csvText, {
        header: true,
        skipEmptyLines: true,
        transformHeader: h => (h ? h.replace(/^\ufeff/, '').trim() : ''),
        complete: results => {
          virtualTrades = (results.data || []).filter(row => row.날짜 && row.종목코드);
          renderVirtualView();
          renderJournalView();
        }
      });
    })
    .catch(() => { virtualTrades = []; renderVirtualView(); });
}

function formatWon(value) {
  return `${Math.round(value).toLocaleString()}원`;
}

function formatSignedWon(value) {
  return `${value > 0 ? "+" : ""}${Math.round(value).toLocaleString()}원`;
}

function virtualStatusBadge(status) {
  const badgeClass = { "매수": "signal-buy", "보유": "signal-review", "매도": "signal-avoid" }[status] || "signal-none";
  return `<span class="badge-signal ${badgeClass}">${status}</span>`;
}

function renderVirtualView() {
  const body = document.getElementById("virtualBody");
  if (!body) return;

  const dateLabel = `${currentDate.slice(0, 4)}-${currentDate.slice(4, 6)}-${currentDate.slice(6, 8)}`;
  document.getElementById("virtualDateText").innerText = `(${dateLabel})`;

  const rows = virtualTrades.filter(row => row.날짜 === currentDate);
  const holding = rows.filter(row => row.상태 !== "매도");
  const soldUntilToday = virtualTrades.filter(row => row.상태 === "매도" && row.날짜 <= currentDate);
  const num = text => Number(text) || 0;

  const cost = holding.reduce((sum, row) => sum + num(row.매수가) * num(row.수량), 0);
  const value = holding.reduce((sum, row) => sum + num(row.평가금액), 0);
  const realized = soldUntilToday.reduce((sum, row) => sum + num(row.손익), 0);
  const countOf = status => rows.filter(row => row.상태 === status).length;

  const setText = (id, text, colorValue) => {
    const el = document.getElementById(id);
    el.innerText = text;
    el.style.color = colorValue === undefined ? "" : percentColor(colorValue);
  };
  setText("virtualHoldCount", rows.length ? `${holding.length}개` : "-");
  setText("virtualTodayTrades", `오늘 매수 ${countOf("매수")}건 · 매도 ${countOf("매도")}건`);
  setText("virtualCost", rows.length ? formatWon(cost) : "-");
  setText("virtualValue", `평가금액 ${formatWon(value)}`);
  setText("virtualOpenProfit", rows.length ? formatSignedWon(value - cost) : "-", value - cost);
  setText("virtualOpenRate", cost > 0 ? formatSignedPercent((value / cost - 1) * 100) : "-");
  setText("virtualRealized", formatSignedWon(realized), realized);
  setText("virtualSellCount", `매도 ${soldUntilToday.length}건 (기준일까지)`);

  if (rows.length === 0) {
    body.innerHTML = `<tr><td colspan="15" style="text-align: center; padding: 2rem; color: var(--text-dim);">이 날짜의 가상 거래 기록이 없습니다.</td></tr>`;
  } else {
    body.innerHTML = "";
    rows.forEach(row => {
      const profit = num(row.손익);
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${virtualStatusBadge(row.상태)}</td>
        <td><code>${row.종목코드}</code></td>
        <td><strong class="stock-name-clickable" title="이 종목의 일별 기록 보기">${row.종목명}</strong></td>
        <td>${row.시장 || "-"}</td>
        <td><span class="stock-sector-tag">${row.섹터 || "-"}</span></td>
        <td>${row.수량}주</td>
        <td>${row.매수일.slice(4, 6)}-${row.매수일.slice(6, 8)}</td>
        <td>${formatWon(num(row.매수가))}</td>
        <td><strong>${formatWon(num(row.종가))}</strong></td>
        <td>${formatWon(num(row.손절가))}</td>
        <td>${row.매도가 ? formatWon(num(row.매도가)) : "-"}</td>
        <td>${row.상태 === "매도" ? "-" : formatWon(num(row.평가금액))}</td>
        <td><strong style="color: ${percentColor(profit)};">${formatSignedWon(profit)}</strong></td>
        <td><strong style="color: ${percentColor(parsePercent(row.수익률))};">${row.수익률}</strong></td>
        <td><span style="font-size:0.82rem; color:var(--text-muted);">${row.비고 || "-"}</span></td>
      `;
      tr.querySelector(".stock-name-clickable").onclick = () => { selectedVirtualCode = row.종목코드; renderVirtualHistory(); };
      body.appendChild(tr);
    });
  }
  renderVirtualHistory();
}

function renderVirtualHistory() {
  const body = document.getElementById("virtualHistoryBody");
  const title = document.getElementById("virtualHistoryTitle");
  const rows = virtualTrades.filter(row => row.종목코드 === selectedVirtualCode);
  const num = text => Number(text) || 0;

  if (rows.length === 0) {
    title.innerText = "종목 일별 기록";
    body.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 2rem; color: var(--text-dim);">위 표에서 종목명을 누르세요.</td></tr>`;
    return;
  }

  title.innerText = `${rows[0].종목명} 일별 기록`;
  body.innerHTML = "";
  rows.forEach(row => {
    const profit = num(row.손익);
    const tr = document.createElement("tr");
    if (row.날짜 === currentDate) tr.className = "sector-row-selected";
    tr.innerHTML = `
      <td>${row.날짜.slice(0, 4)}-${row.날짜.slice(4, 6)}-${row.날짜.slice(6, 8)}</td>
      <td>${virtualStatusBadge(row.상태)}</td>
      <td>${formatWon(num(row.매수가))}</td>
      <td><strong>${formatWon(num(row.종가))}</strong></td>
      <td>${formatWon(num(row.최고종가))}</td>
      <td>${formatWon(num(row.손절가))}</td>
      <td>${row.매도가 ? formatWon(num(row.매도가)) : "-"}</td>
      <td><strong style="color: ${percentColor(profit)};">${formatSignedWon(profit)}</strong></td>
      <td><strong style="color: ${percentColor(parsePercent(row.수익률))};">${row.수익률}</strong></td>
      <td><span style="font-size:0.82rem; color:var(--text-muted);">${row.비고 || "-"}</span></td>
    `;
    body.appendChild(tr);
  });
}

/**
 * 8. 필터링 및 데이터 테이블 렌더링
 */
function applyFiltersAndRenderTable() {
  filteredStockData = allStockData.filter(item => {
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

    // 4. Search query
    if (currentSearchQuery) {
      const q = currentSearchQuery.toLowerCase();
      const matchName = item.종목명.toLowerCase().includes(q);
      const matchCode = item.종목코드.toLowerCase().includes(q);
      if (!matchName && !matchCode) return false;
    }

    return true;
  });

  // Table Sort
  filteredStockData.sort((a, b) => {
    let valA, valB;

    if (sortKey === "매수신호") {
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
    } else if (sortKey === "3개월수익률") {
      valA = parsePercent(a["3개월수익률"]) ?? -Infinity;
      valB = parsePercent(b["3개월수익률"]) ?? -Infinity;
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
    tbody.innerHTML = `<tr><td colspan="12" style="text-align: center; padding: 2rem; color: var(--text-dim);">검색 및 필터 조건에 부합하는 종목이 없습니다.</td></tr>`;
    return;
  }

  pageRows.forEach(row => {
    const tr = document.createElement("tr");
    
    // 매수신호 (이 열이 없는 예전 리포트는 "-" 로 표시)
    const buySignal = row.매수신호 || "-";
    const buyReason = row.매수신호사유 || "";
    let buySignalClass = "signal-none";
    if (buySignal.startsWith("A")) buySignalClass = "signal-buy";
    else if (buySignal.startsWith("B")) buySignalClass = "signal-review";
    else if (buySignal.startsWith("C")) buySignalClass = "signal-avoid";

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
      <td>${row.시장 || "-"}</td>
      <td><span class="stock-sector-tag">${row.섹터}</span></td>
      <td title="${buyReason}"><span class="badge-signal ${buySignalClass}">${buySignal}</span>${buyReason ? `<div class="signal-reason">${buyReason}</div>` : ""}</td>
      <td>${row.추세통과 === "O" ? "🟢 O" : (row.추세통과 === "X" ? "🔴 X" : "-")}</td>
      <td><strong style="color: ${percentColor(parsePercent(row["3개월수익률"]))};">${row["3개월수익률"] || "-"}</strong></td>
      <td>${candleBadge}</td>
      <td><span class="count-pill">${row["20일이격도"] || "100.0%"}</span></td>
      <td><strong>${row.현재가}원</strong></td>
      <td><strong style="color: ${rateColor};">${rateVal}</strong></td>
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
  currentSignalFilter = DEFAULT_SIGNAL_FILTER;
  currentCandleFilter = [...DEFAULT_CANDLE_FILTER];
  currentSearchQuery = "";
  currentPage = 1;

  const searchInput = document.getElementById("searchInput");
  if (searchInput) searchInput.value = "";

  switchView('sector');
  updateFilterCounts();
  applyFiltersAndRenderTable();
  window.scrollTo({ top: 0, behavior: 'smooth' });
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

window.addEventListener("popstate", (e) => {
  if (e.state && e.state.view === 'stockDetail' && e.state.code) {
    openStockDetail(e.state.code, false);
  } else {
    switchView(lastListView);
  }
});

/**
 * 12. 뷰 전환
 */
function switchView(viewName) {
  document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
  if (['dashboard', 'sector', 'leaders', 'journal', 'virtual'].includes(viewName)) lastListView = viewName;

  if (viewName === 'dashboard') {
    document.getElementById("viewDashboard").classList.add("active");
    document.getElementById("navBtnMain").classList.add("active");
  } else if (viewName === 'sector') {
    document.getElementById("viewSector").classList.add("active");
    document.getElementById("navBtnSector").classList.add("active");
  } else if (viewName === 'leaders') {
    document.getElementById("viewLeaders").classList.add("active");
    document.getElementById("navBtnLeaders").classList.add("active");
  } else if (viewName === 'journal') {
    document.getElementById("viewJournal").classList.add("active");
    document.getElementById("navBtnJournal").classList.add("active");
    renderJournalView();
  } else if (viewName === 'virtual') {
    document.getElementById("viewVirtual").classList.add("active");
    document.getElementById("navBtnVirtual").classList.add("active");
    renderVirtualView();
  } else if (viewName === 'rules') {
    document.getElementById("viewRules").classList.add("active");
    document.getElementById("navBtnRules").classList.add("active");
  } else if (viewName === 'stockDetail') {
    document.getElementById("viewStockDetail").classList.add("active");
  }
}

/**
 * 13. 개별 종목 상세 분석 페이지 오픈 & 차트 렌더링
 */
function openStockDetail(code, pushHistory = true) {
  const stock = allStockData.find(s => s.종목코드 === code);
  if (!stock) return;

  if (pushHistory && window.history && window.history.pushState) {
    try {
      window.history.pushState({ view: 'stockDetail', code: code }, '', `#stock-${code}`);
    } catch(e) {}
  }

  // 헤더 요약 정보
  document.getElementById("detailStockTitle").innerText = `${stock.종목명} 상세`;
  document.getElementById("detailStockCode").innerText = stock.종목코드;
  document.getElementById("detailStockName").innerText = stock.종목명;
  document.getElementById("detailStockMarket").innerText = stock.시장 || "-";
  document.getElementById("detailStockSector").innerText = stock.섹터;
  document.getElementById("detailStockPrice").innerText = `${stock.현재가}원`;
  document.getElementById("detailStockNaverLink").href = stock.상세페이지;

  // 지표 카드
  const passText = { "O": "🟢 통과", "X": "🔴 미통과" }[stock.추세통과] || "-";
  document.getElementById("detailBuySignal").innerText = stock.매수신호 || "-";
  document.getElementById("detailBuyReason").innerText = stock.매수신호사유 || "-";
  document.getElementById("detailTrendPass").innerText = passText;
  document.getElementById("detailReturn3m").innerText = stock["3개월수익률"] || "-";
  document.getElementById("detailFromHigh").innerText = stock.고점대비 || "-";
  document.getElementById("detailDisparity").innerText = stock["20일이격도"] || "-";
  document.getElementById("detailChange").innerText = stock.등락률 || "-";
  document.getElementById("detailCandle").innerText =
    `${stock.차트꼬리 || "-"}${stock.강한마감 === "O" ? " · ★ 강한 마감" : ""}`;

  // 이평선 가격 수치
  document.getElementById("detailMa5").innerText = `${stock.MA5 || "0"}원`;
  document.getElementById("detailMa20").innerText = `${stock.MA20 || "0"}원`;
  document.getElementById("detailMa60").innerText = `${stock.MA60 || "0"}원`;
  document.getElementById("detailMa120").innerText = `${stock.MA120 || "0"}원`;

  switchView("stockDetail");
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
