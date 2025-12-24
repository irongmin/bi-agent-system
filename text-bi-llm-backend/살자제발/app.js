// ===== DOM =====
const splashRoot = document.getElementById("splashRoot");
const logoAssemble = document.getElementById("logoAssemble");

const part1 = document.getElementById("part1");
const part2 = document.getElementById("part2");
const part3 = document.getElementById("part3");
const part4 = document.getElementById("part4");

const loginPanel = document.getElementById("loginPanel");
const loginBtn = document.getElementById("loginBtn");
const empNo = document.getElementById("empNo");
const empPw = document.getElementById("empPw");
const loginMsg = document.getElementById("loginMsg");

const dashboardRoot = document.getElementById("dashboardRoot");

// ===== SPLASH LOGO ANIMATION SEQUENCE =====
function runSplash() {
  // 1) 파트 날아오기 순서: 4 -> 1 -> 3 -> 2
  setTimeout(() => part4.classList.add("fly-in"), 100);
  setTimeout(() => part1.classList.add("fly-in"), 260);
  setTimeout(() => part3.classList.add("fly-in"), 420);
  setTimeout(() => part2.classList.add("fly-in"), 560);

  // 2) 전체 줌
  setTimeout(() => {
    logoAssemble.classList.add("logo-zoom");
  }, 900);

  // 3) 살짝 페이드
  setTimeout(() => {
    logoAssemble.classList.add("logo-fade");
  }, 2400);

  // 4) 로그인 패널 등장 + ✅ 여기서만 배경 사진 ON
  setTimeout(() => {
    loginPanel.classList.add("show");
    loginPanel.setAttribute("aria-hidden", "false");

    // ✅ 로그인 화면 뜰 때만 배경 사진/베일 켜기
    splashRoot.classList.add("login-bg");
  }, 2600);
}

// ===== LOGIN (Mock) =====
function doLogin() {
  const id = (empNo.value || "").trim();
  const pw = (empPw.value || "").trim();

  if (!id || !pw) {
    loginMsg.textContent = "사번과 비밀번호를 입력해 주세요.";
    return;
  }

  // Mock: 1111 / 1111만 통과
  if (id === "1111" && pw === "1111") {
    loginMsg.textContent = "";

    // ✅ 화면 전환
    document.getElementById("splashRoot").classList.add("hidden");
    dashboardRoot.classList.remove("hidden");

    // ✅ 배경 클래스 제거(혹시 splash가 다시 보일 경우 대비)
    splashRoot.classList.remove("login-bg");

    startClock();
    bindDashboardNav();
  } else {
    loginMsg.textContent = "로그인 정보가 올바르지 않습니다.";
  }
}

// ===== DASHBOARD (기본 기능 최소) =====
function startClock() {
  const el = document.getElementById("datetime");
  if (!el) return;

  const tick = () => {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, "0");
    const dd = String(now.getDate()).padStart(2, "0");
    const hh = String(now.getHours()).padStart(2, "0");
    const mi = String(now.getMinutes()).padStart(2, "0");
    el.textContent = `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
  };
  tick();
  setInterval(tick, 1000 * 15);
}

function bindDashboardNav() {
  const navItems = document.querySelectorAll(".nav-item[data-page]");
  const pages = {
    dashboard: document.getElementById("dashboard-page"),
    history: document.getElementById("history-page"),
    report: document.getElementById("report-page"),
    data: document.getElementById("data-page"),
  };

  navItems.forEach((item) => {
    item.addEventListener("click", () => {
      navItems.forEach((x) => x.classList.remove("active"));
      item.classList.add("active");

      const pageKey = item.getAttribute("data-page");
      Object.values(pages).forEach((p) => p && p.classList.remove("active"));
      if (pages[pageKey]) pages[pageKey].classList.add("active");
    });
  });

  // Quick Query
  document.querySelectorAll(".quick-query").forEach((q) => {
    q.addEventListener("click", () => {
      const tpl = q.getAttribute("data-template") || "";
      const input = document.getElementById("queryInput");
      if (input) input.value = tpl;
    });
  });

  // Query Button (Mock)
  const queryButton = document.getElementById("queryButton");
  if (queryButton) {
    queryButton.addEventListener("click", () => {
      const input = document.getElementById("queryInput");
      const text = (input?.value || "").trim();
      if (!text) return;

      // 채팅에 사용자 메시지 추가
      const chatList = document.getElementById("chatList");
      if (chatList) {
        const wrap = document.createElement("div");
        wrap.className = "chat-message user";
        wrap.innerHTML = `
          <div>
            <div class="chat-bubble user">${escapeHtml(text)}</div>
            <div class="chat-meta">사용자</div>
          </div>
        `;
        chatList.appendChild(wrap);
        chatList.scrollTop = chatList.scrollHeight;
      }

      // Mock 결과
      const insight = document.getElementById("insightText");
      if (insight) insight.textContent = "현재는 Mock 화면입니다. 백엔드 연결 시 분석 결과가 표시됩니다.";

      const sql = document.getElementById("sqlCode");
      if (sql) sql.textContent = "SELECT * FROM ... (Mock SQL)";

      const k1 = document.getElementById("kpi1Value");
      const k2 = document.getElementById("kpi2Value");
      const k3 = document.getElementById("kpi3Value");
      if (k1) k1.textContent = "1,234";
      if (k2) k2.textContent = "567";
      if (k3) k3.textContent = "89";

      // Chart Mock
      renderMockChart();
    });
  }
}

let chartInstance = null;
function renderMockChart() {
  const canvas = document.getElementById("myChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  if (chartInstance) chartInstance.destroy();

  chartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["A", "B", "C", "D", "E"],
      datasets: [
        {
          label: "Mock",
          data: [12, 19, 3, 5, 2],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  });
}

function escapeHtml(str) {
  return str
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// ===== EVENTS =====
loginBtn?.addEventListener("click", doLogin);
empPw?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") doLogin();
});

// ===== START =====
runSplash();
