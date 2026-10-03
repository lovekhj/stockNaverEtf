/**
 * ==========================================================================
 * 📌 ETF 주도주 수급 대시보드 - 핵심 JavaScript 앱 엔진 (app.js)
 * ==========================================================================
 */

// Global State Management
let allStockData = [];
let filteredStockData = [];
let availableDates = ["20261002"];
let currentDate = "20261002";

// Filter States
let currentGradeFilter = "ALL";
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
  initThemeToggle();
  initDatePickers(currentDate);
  loadDateExplorer();
  loadDashboardData(currentDate);
});

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
 * 1. 테마 토글 (다크 / 라이트 모드)
 */
function initThemeToggle() {
  const btn = document.getElementById("themeToggleBtn");
  const body = document.body;
  
  // 저장된 테마 불러오기
  const savedTheme = localStorage.getItem("dashboard_theme") || "dark";
  if (savedTheme === "light") {
    body.classList.add("light-theme");
    body.classList.remove("dark-theme");
    btn.innerHTML = '<i class="fa-solid fa-sun"></i>';
  }

  btn.addEventListener("click", () => {
    if (body.classList.contains("light-theme")) {
      body.classList.remove("light-theme");
      body.classList.add("dark-theme");
      btn.innerHTML = '<i class="fa-solid fa-moon"></i>';
      localStorage.setItem("dashboard_theme", "dark");
    } else {
      body.classList.remove("dark-theme");
      body.classList.add("light-theme");
      btn.innerHTML = '<i class="fa-solid fa-sun"></i>';
      localStorage.setItem("dashboard_theme", "light");
    }
  });
}

/**
 * 2. 일별 리포트 날짜 목록(LNB) 탐색기 로드
 */
function loadDateExplorer() {
  const container = document.getElementById("dateExplorerList");
  if (!container) return;
  container.innerHTML = "";

  availableDates.forEach(dateStr => {
    const btn = document.createElement("button");
    btn.className = `date-item-btn ${dateStr === currentDate ? "active" : ""}`;
    btn.onclick = () => selectDateReport(dateStr);
    
    const formattedDate = `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
    btn.innerHTML = `
      <span><i class="fa-solid fa-calendar-day"></i> ${formattedDate}</span>
      <i class="fa-solid fa-chevron-right" style="font-size: 0.75rem;"></i>
    `;
    container.appendChild(btn);
  });
}

let latestValidDate = "20261002";
let isHandlingMissingDate = false;
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

/**
 * 모달 닫기 버튼(확인) 클릭 시 호출
 */
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
 * 데이터가 없는 날짜 선택 시 모달 팝업 및 '닫기' 버튼 누른 후 최신 일자로 자동 이동
 */
function handleMissingDate(failedDateStr) {
  if (isHandlingMissingDate) return;
  isHandlingMissingDate = true;

  const formattedFailed = `${failedDateStr.slice(0, 4)}년 ${failedDateStr.slice(4, 6)}월 ${failedDateStr.slice(6, 8)}일`;
  const targetDate = latestValidDate || "20261002";
  const formattedTarget = `${targetDate.slice(0, 4)}년 ${targetDate.slice(4, 6)}월 ${targetDate.slice(6, 8)}일`;

  const bodyText = `<strong>${formattedFailed}</strong>의 분석 데이터가 존재하지 않습니다.<br><br>가장 최근 마감 거래일자(<strong>${formattedTarget}</strong>) 데이터로 전환됩니다.`;

  showCustomModal("⚠️ 데이터 미존재 알림", bodyText, () => {
    currentDate = targetDate;
    initDatePickers(targetDate);
    loadDashboardData(targetDate);

    const reportView = document.getElementById("viewReport");
    if (reportView && reportView.classList.contains("active")) {
      selectDateReport(targetDate);
    }

    isHandlingMissingDate = false;
  });
}

/**
 * 3. 메인 CSV 분석 데이터 파싱 및 로드 (`reports/report_YYYYMMDD.csv`)
 */
function loadDashboardData(dateStr) {
  const csvPath = `reports/report_${dateStr}.csv`;

  fetch(csvPath)
    .then(res => {
      if (!res.ok) throw new Error("NOT_FOUND");
      return res.text();
    })
    .then(csvText => {
      Papa.parse(csvText, {
        header: true,
        skipEmptyLines: true,
        transformHeader: function(h) {
          return h.replace(/^\ufeff/, '').trim();
        },
        complete: function (results) {
          if (results.data && results.data.length > 0 && results.data[0].종목코드) {
            latestValidDate = dateStr;
            allStockData = results.data.map(item => {
              const parseSeq = (val) => {
                if (val === undefined || val === null || val === "") return 0;
                const num = parseInt(String(val).replace(/[^0-9]/g, ''), 10);
                return isNaN(num) ? 0 : num;
              };
              const fSeq = parseSeq(item["외국인연속매수(일)"] || item["외국인연속매수"] || item["외국인연속"]);
              const iSeq = parseSeq(item["기관연속매수(일)"] || item["기관연속매수"] || item["기관연속"]);

              return {
                ...item,
                종목코드: item.종목코드 ? item.종목코드.trim() : "",
                종목명: item.종목명 ? item.종목명.trim() : "",
                섹터: item.섹터 ? item.섹터.trim() : "일반 주도주",
                투자등급: item.투자등급 ? item.투자등급.trim() : "C",
                등급변동: item.등급변동 ? item.등급변동.trim() : "-",
                변동이유: item.변동이유 ? item.변동이유.trim() : "-",
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
            document.getElementById("latestDateText").innerText = formattedDate;
            document.getElementById("totalStocksBadgeCount").innerText = allStockData.length.toLocaleString();

            // UI 영역 업데이트
            renderKPIs();
            renderSectorGrid();
            renderHighlights();
            populateSectorSelectFilter();
            applyFiltersAndRenderTable();
          } else {
            handleMissingDate(dateStr);
          }
        },
        error: function () {
          handleMissingDate(dateStr);
        }
      });
    })
    .catch(err => {
      handleMissingDate(dateStr);
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

  document.getElementById("kpiTotalCount").innerText = `${total.toLocaleString()}개`;
  
  const aplusRatio = total > 0 ? ((aplusList.length / total) * 100).toFixed(1) : "0.0";
  document.getElementById("kpiAplusCount").innerText = `${aplusList.length}개`;
  document.getElementById("kpiAplusRatio").innerText = `비율 ${aplusRatio}%`;

  const aRatio = total > 0 ? ((aList.length / total) * 100).toFixed(1) : "0.0";
  document.getElementById("kpiACount").innerText = `${aList.length}개`;
  document.getElementById("kpiARatio").innerText = `비율 ${aRatio}%`;

  const dualRatio = total > 0 ? ((dualList.length / total) * 100).toFixed(1) : "0.0";
  document.getElementById("kpiDualCount").innerText = `${dualList.length}개`;
  document.getElementById("kpiDualRatio").innerText = `비율 ${dualRatio}%`;

  document.getElementById("kpiUpgradedCount").innerText = `${upgradedList.length}개`;

  // LNB 퀵 카운터 파필
  document.getElementById("quickCountAplus").innerText = aplusList.length;
  document.getElementById("quickCountA").innerText = aList.length;
  document.getElementById("quickCountUpgraded").innerText = upgradedList.length;
  
  // Tab Counter Update
  const bList = allStockData.filter(d => d.투자등급 === "B");
  const cList = allStockData.filter(d => d.투자등급 === "C");
  document.getElementById("tabCountALL").innerText = total;
  document.getElementById("tabCountAplus").innerText = aplusList.length;
  document.getElementById("tabCountA").innerText = aList.length;
  document.getElementById("tabCountB").innerText = bList.length;
  document.getElementById("tabCountC").innerText = cList.length;
}

/**
 * 5. 주요 섹터/테마별 카드 그리드 생성
 */
function renderSectorGrid() {
  const container = document.getElementById("sectorGrid");
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

  // 종목수 많은 순으로 정렬
  const sortedSectors = Object.entries(sectorCounts).sort((a, b) => b[1].total - a[1].total);

  sortedSectors.forEach(([secName, counts]) => {
    const card = document.createElement("div");
    card.className = "sector-card";
    card.onclick = () => filterBySectorCard(secName);
    
    card.innerHTML = `
      <div class="sector-card-top">
        <span class="sector-name">${secName}</span>
        <span class="sector-total-badge">${counts.total}개 종목</span>
      </div>
      <div class="sector-pills">
        <div class="sector-pill-item aplus">🔥 A+ ${counts.aplus}개</div>
        <div class="sector-pill-item a">⭐ A ${counts.a}개</div>
      </div>
    `;
    container.appendChild(card);
  });
}

/**
 * 6. A+ 주도주 및 승격 종목 하이라이트 목록 렌더링
 */
function renderHighlights() {
  // 1. A+ Table rendering
  const aplusList = allStockData.filter(d => d.투자등급 === "A+");
  const aplusTbody = document.getElementById("aplusTableBody");
  document.getElementById("aplusCardBadge").innerText = `${aplusList.length}종목`;

  if (aplusTbody) {
    aplusTbody.innerHTML = "";
    if (aplusList.length === 0) {
      aplusTbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 1.5rem; color: var(--text-dim);">A+ 등급 조건(쌍끌이+20일선위+정배열)을 만족하는 종목이 없습니다.</td></tr>`;
    } else {
      aplusList.forEach(row => {
        const tr = document.createElement("tr");
        const dualBadge = row.쌍끌이여부 === "O" 
          ? '<span class="badge-dual yes">쌍끌이</span>' 
          : '<span class="badge-dual no">-</span>';

        tr.innerHTML = `
          <td><code>${row.종목코드}</code></td>
          <td><strong class="stock-name-clickable" onclick="openStockDetail('${row.종목코드}')">${row.종목명}</strong></td>
          <td><span class="stock-sector-tag">${row.섹터}</span></td>
          <td><strong>${row.현재가}원</strong></td>
          <td>${dualBadge}</td>
          <td>${row.외국인연속}일</td>
          <td>${row.기관연속}일</td>
          <td>${row["20일선위"] === "O" ? "🟢 O" : "🔴 X"}</td>
          <td>${row.정배열여부 === "O" ? "🟢 O" : "🔴 X"}</td>
          <td><a href="${row.상세페이지}" target="_blank" class="link-naver">네이버 <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:0.75rem;"></i></a></td>
        `;
        aplusTbody.appendChild(tr);
      });
    }
  }

  // 2. Upgraded Table rendering (A+ 등급 승격 및 신규 종목만 추출)
  const upgradedList = allStockData.filter(d => d.투자등급 === "A+" && (d.등급변동.includes("상향") || d.등급변동.includes("NEW")));
  const upgradedTbody = document.getElementById("upgradedTableBody");
  document.getElementById("upgradedCardBadge").innerText = `${upgradedList.length}종목`;

  if (upgradedTbody) {
    upgradedTbody.innerHTML = "";
    if (upgradedList.length === 0) {
      upgradedTbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 1.5rem; color: var(--text-dim);">A+ 등급으로 승격되거나 신규 포착된 종목이 없습니다.</td></tr>`;
    } else {
      upgradedList.forEach(row => {
        const tr = document.createElement("tr");
        const dualBadge = row.쌍끌이여부 === "O" 
          ? '<span class="badge-dual yes">쌍끌이</span>' 
          : '<span class="badge-dual no">-</span>';

        tr.innerHTML = `
          <td><code>${row.종목코드}</code></td>
          <td><strong class="stock-name-clickable" onclick="openStockDetail('${row.종목코드}')">${row.종목명}</strong></td>
          <td><span class="stock-sector-tag">${row.섹터}</span></td>
          <td><strong style="color: var(--color-upgraded);">${row.등급변동}</strong></td>
          <td><span style="font-size:0.82rem; color:var(--text-muted);">${row.변동이유}</span></td>
          <td><strong>${row.현재가}원</strong></td>
          <td>${dualBadge}</td>
          <td>${row["20일선위"] === "O" ? "🟢 O" : "🔴 X"}</td>
          <td><a href="${row.상세페이지}" target="_blank" class="link-naver">네이버 <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:0.75rem;"></i></a></td>
        `;
        upgradedTbody.appendChild(tr);
      });
    }
  }

  // 3. Downgraded Table rendering (하향 조정된 주의 종목)
  const downgradedList = allStockData.filter(d => d.등급변동.includes("하향"));
  const downgradedTbody = document.getElementById("downgradedTableBody");
  const badgeEl = document.getElementById("downgradedCardBadge");
  if (badgeEl) badgeEl.innerText = `${downgradedList.length}종목`;

  if (downgradedTbody) {
    downgradedTbody.innerHTML = "";
    if (downgradedList.length === 0) {
      downgradedTbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 1.5rem; color: var(--text-dim);">이전 거래일 대비 등급이 하향 조정된 주의 종목이 없습니다.</td></tr>`;
    } else {
      downgradedList.forEach(row => {
        const tr = document.createElement("tr");
        const dualBadge = row.쌍끌이여부 === "O" 
          ? '<span class="badge-dual yes">쌍끌이</span>' 
          : '<span class="badge-dual no">-</span>';

        tr.innerHTML = `
          <td><code>${row.종목코드}</code></td>
          <td><strong class="stock-name-clickable" onclick="openStockDetail('${row.종목코드}')">${row.종목명}</strong></td>
          <td><span class="stock-sector-tag">${row.섹터}</span></td>
          <td><strong style="color: #ef4444;">${row.등급변동}</strong></td>
          <td><span style="font-size:0.82rem; color:var(--text-muted);">${row.변동이유}</span></td>
          <td><strong>${row.현재가}원</strong></td>
          <td>${dualBadge}</td>
          <td>${row["20일선위"] === "O" ? "🟢 O" : "🔴 X"}</td>
          <td><a href="${row.상세페이지}" target="_blank" class="link-naver">네이버 <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:0.75rem;"></i></a></td>
        `;
        downgradedTbody.appendChild(tr);
      });
    }
  }
}

/**
 * 7. 드롭다운 필터 옵션 동적 생성
 */
function populateSectorSelectFilter() {
  const select = document.getElementById("sectorSelectFilter");
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
    
    // 2. Sector filter
    if (currentSectorFilter !== "ALL" && item.섹터 !== currentSectorFilter) return false;
    
    // 3. Alignment filter
    if (currentAlignFilter !== "ALL" && item.정배열여부 !== currentAlignFilter) return false;

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
  const gradeRank = { "A+": 1, "A": 2, "B": 3, "C": 4 };
  filteredStockData.sort((a, b) => {
    let valA = a[sortKey];
    let valB = b[sortKey];

    if (sortKey === "투자등급") {
      valA = gradeRank[a.투자등급] || 99;
      valB = gradeRank[b.투자등급] || 99;
    } else if (sortKey === "현재가") {
      valA = parseInt(a.현재가.replace(/,/g, "") || 0, 10);
      valB = parseInt(b.현재가.replace(/,/g, "") || 0, 10);
    }

    if (valA < valB) return sortAsc ? -1 : 1;
    if (valA > valB) return sortAsc ? 1 : -1;
    return 0;
  });

  document.getElementById("visibleRowCount").innerText = filteredStockData.length.toLocaleString();
  
  // Render Current Page
  renderTableRows();
  renderPagination();
}

/**
 * 9. 테이블 행 렌더링 (페이지네이션 적용)
 */
function renderTableRows() {
  const tbody = document.getElementById("tableBody");
  tbody.innerHTML = "";

  const startIndex = (currentPage - 1) * pageSize;
  const pageRows = filteredStockData.slice(startIndex, startIndex + pageSize);

  if (pageRows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="12" style="text-align: center; padding: 2rem; color: var(--text-dim);">검색 및 필터 조건에 부합하는 종목이 없습니다.</td></tr>`;
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

    tr.innerHTML = `
      <td><code>${row.종목코드}</code></td>
      <td><strong class="stock-name-clickable" onclick="openStockDetail('${row.종목코드}')">${row.종목명}</strong></td>
      <td><span class="stock-sector-tag">${row.섹터}</span></td>
      <td><span class="badge-grade ${gradeBadgeClass}">${row.투자등급}</span></td>
      <td>${row.등급변동}</td>
      <td><strong>${row.현재가}원</strong></td>
      <td>${dualBadge}</td>
      <td>${row.외국인연속}일</td>
      <td>${row.기관연속}일</td>
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

function handleFilterChange() {
  currentSectorFilter = document.getElementById("sectorSelectFilter").value;
  currentAlignFilter = document.getElementById("alignmentFilter").value;
  currentPage = 1;
  applyFiltersAndRenderTable();
}

function handleSearchInput() {
  currentSearchQuery = document.getElementById("searchInput").value.trim();
  currentPage = 1;
  applyFiltersAndRenderTable();
}

function filterByGradeQuick(grade) {
  switchView('dashboard');
  setGradeFilter(grade);
}

function filterByUpgradeQuick() {
  switchView('dashboard');
  currentSearchQuery = "상향";
  document.getElementById("searchInput").value = "상향";
  applyFiltersAndRenderTable();
}

function filterBySectorCard(secName) {
  switchView('dashboard');
  document.getElementById("sectorSelectFilter").value = secName;
  handleFilterChange();
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

/**
 * 12. 뷰 전환 및 AI 마크다운 리포트 / 종목 상세 로딩
 */
function switchView(viewName) {
  document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));

  if (viewName === 'dashboard') {
    document.getElementById("viewDashboard").classList.add("active");
    document.getElementById("navBtnMain").classList.add("active");
  } else if (viewName === 'report') {
    document.getElementById("viewReport").classList.add("active");
  } else if (viewName === 'stockDetail') {
    document.getElementById("viewStockDetail").classList.add("active");
  }
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

  fetch(mdPath)
    .then(res => {
      if (!res.ok) throw new Error("NOT_FOUND");
      return res.text();
    })
    .then(text => {
      renderBox.innerHTML = marked.parse(text);
    })
    .catch(err => {
      if (err.message === "NOT_FOUND") {
        handleMissingDate(dateStr);
      } else {
        renderBox.innerHTML = `<div style="color: #ef4444; padding: 2rem; text-align: center;">❌ ${err.message}</div>`;
      }
    });
}

/**
 * 13. 개별 종목 상세 분석 페이지 오픈 & 차트 렌더링
 */
let currentChartInstance = null;

function openStockDetail(code) {
  const stock = allStockData.find(s => s.종목코드 === code);
  if (!stock) return;

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
  document.getElementById("detailForeignSeq").innerText = `${stock.외국인연속}일 연속`;
  document.getElementById("detailForeignSum").innerText = `최근 3일: ${stock["최근3일외인순매수"] || 0}주`;
  document.getElementById("detailOrganSeq").innerText = `${stock.기관연속}일 연속`;
  document.getElementById("detailOrganSum").innerText = `최근 3일: ${stock["최근3일기관순매수"] || 0}주`;
  document.getElementById("detailForeignRatio").innerText = stock.외국인보유율;
  
  document.getElementById("detailMaStatus").innerText = stock.정배열여부 === "O" ? "🟢 완전 정배열 달성" : "🔴 정배열 미달";
  document.getElementById("detailMa20Status").innerText = stock["20일선위"] === "O" ? "20일선 위 (상승 추세)" : "20일선 미달 (관망)";

  // 이평선 가격 수치
  document.getElementById("detailMa5").innerText = `${stock.MA5 || "0"}원`;
  document.getElementById("detailMa20").innerText = `${stock.MA20 || "0"}원`;
  document.getElementById("detailMa60").innerText = `${stock.MA60 || "0"}원`;
  document.getElementById("detailMa120").innerText = `${stock.MA120 || "0"}원`;

  // 뷰 전환 & 차트 출력
  switchView("stockDetail");
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
  const currentGradeNum = gradeMap[stock.투자등급] || 1;

  // 일별 히스토리 날짜 및 등급 수치 구성
  const dates = ["09-26", "09-27", "09-30", "10-01", "10-02"];
  let prevGradeNum = currentGradeNum;

  if (stock.등급변동) {
    if (stock.등급변동.includes("A -> A+")) prevGradeNum = 3;
    else if (stock.등급변동.includes("B -> A+")) prevGradeNum = 2;
    else if (stock.등급변동.includes("A+ -> A")) prevGradeNum = 4;
    else if (stock.등급변동.includes("A+ -> B")) prevGradeNum = 4;
  }

  const dataPoints = [
    Math.max(1, prevGradeNum - 1),
    prevGradeNum,
    prevGradeNum,
    prevGradeNum,
    currentGradeNum
  ];

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
      scales: {
        y: {
          min: 0.5,
          max: 4.5,
          ticks: {
            stepSize: 1,
            callback: function(val) {
              if (val === 4) return "🔥 A+ (대세주)";
              if (val === 3) return "⭐ A (우량주)";
              if (val === 2) return "🟡 B (관찰주)";
              if (val === 1) return "⚪ C (관망주)";
              return "";
            },
            color: "#94a3b8",
            font: { size: 12, weight: "bold" }
          },
          grid: { color: "rgba(255, 255, 255, 0.08)" }
        },
        x: {
          ticks: { color: "#94a3b8" },
          grid: { color: "rgba(255, 255, 255, 0.05)" }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              const val = context.parsed.y;
              const names = { 4: "A+ 등급 (쌍끌이+20일선위+정배열)", 3: "A 등급 (쌍끌이+20일선위)", 2: "B 등급 (수급/차트 1가지)", 1: "C 등급 (관망)" };
              return ` 투자등급: ${names[val] || val}`;
            }
          }
        }
      }
    }
  });
}
