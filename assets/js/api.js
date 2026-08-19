const HR_API_BASE_URL = window.HR_API_BASE_URL
  || (["127.0.0.1", "localhost"].includes(window.location.hostname)
    ? "http://127.0.0.1:8000/api"
    : "https://smart-hr-api-8rxh.onrender.com/api");

// Every functional page loads this file. Attach the three shared stylesheets
// here so older pages no longer depend on duplicated inline styles.
(function ensureSharedAssets() {
  const scriptUrl = document.currentScript?.src || new URL("assets/js/api.js", window.location.href).href;
  ["base.css", "components.css", "mobile.css"].forEach((file) => {
    if (document.querySelector(`link[data-shared-hr-style="${file}"]`)) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = new URL(`../css/${file}?v=20260817-review4`, scriptUrl).href;
    link.dataset.sharedHrStyle = file;
    document.head.appendChild(link);
  });
})();

window.hrEscapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
})[char]);

window.showHrToast = (message, type = "success") => {
  document.querySelector(".hr-toast")?.remove();
  const toast = document.createElement("div");
  toast.className = `hr-toast ${type}`;
  toast.setAttribute("role", "status");
  toast.textContent = message;
  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("visible"));
  setTimeout(() => {
    toast.classList.remove("visible");
    setTimeout(() => toast.remove(), 200);
  }, 3600);
};

const HR_ICON_PATHS = {
  home: '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5"/><path d="M9.5 20v-6h5v6"/>',
  leave: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18M12 13v6M9 16h6"/>',
  late: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  history: '<path d="M6 3h9l4 4v14H6z"/><path d="M15 3v5h5M9 13h6M9 17h6"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  logout: '<path d="M10 5V3H4v18h6v-2"/><path d="M14 8l4 4-4 4M8 12h10"/>',
  announcement: '<path d="M4 13V9l12-5v14L4 13Z"/><path d="m7 14 1 6h4l-2-5M19 8v6"/>',
  team: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18M8 14h2M14 14h2M8 18h2M14 18h2"/>',
  department: '<path d="M3 21h18M5 21V7l7-4 7 4v14M9 9h1M14 9h1M9 13h1M14 13h1M9 17h6"/>',
  account: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><circle cx="12" cy="9" r="2.5"/><path d="M8.5 16a4 4 0 0 1 7 0"/>',
  success: '<path d="m5 12 4 4L19 6"/>',
  warning: '<path d="M10.3 3.7 2.6 17a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 3.7a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>'
};

window.hrIcon = (name) => `<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${HR_ICON_PATHS[name] || HR_ICON_PATHS.grid}</svg>`;

function installEnterpriseIcons() {
  const iconForHref = (href = "") => href.includes("leave-assistant") || href.includes("leave-apply") ? "leave"
    : href.includes("leave-history") ? "history"
    : href.includes("late-notice") ? "late"
    : href.includes("notification") ? "bell"
    : href.includes("team") || href.includes("employee") ? "team"
    : href.includes("calendar") || href.includes("leave-settings") ? "calendar"
    : href.includes("department") ? "department"
    : href.includes("account") ? "account"
    : href.includes("profile") ? "user"
    : href.includes("announcement") ? "announcement"
    : href.endsWith("index.html") ? "home" : "grid";
  document.querySelectorAll("[data-hr-icon]").forEach((node) => { node.innerHTML = hrIcon(node.dataset.hrIcon); });
  document.querySelectorAll(".mobile-nav a").forEach((link) => {
    const icon = link.querySelector("span:first-child");
    if (icon) icon.innerHTML = hrIcon(iconForHref(link.getAttribute("href") || ""));
  });
  document.querySelectorAll(".function-card").forEach((card) => {
    const icon = card.querySelector(".function-icon");
    if (icon) icon.innerHTML = hrIcon(iconForHref(card.getAttribute("href") || ""));
  });
  document.querySelectorAll(".warning-icon").forEach((node) => { node.innerHTML = hrIcon("warning"); });
  document.querySelectorAll(".success-icon").forEach((node) => { node.innerHTML = hrIcon("success"); });
  document.querySelectorAll(".result-icon").forEach((node) => { node.innerHTML = hrIcon("close"); });
  document.querySelectorAll(".icon").forEach((node) => {
    if (node.querySelector("svg") || node.closest(".calendar")) return;
    const href = node.closest("a")?.getAttribute("href") || window.location.pathname;
    node.innerHTML = hrIcon(iconForHref(href));
  });
}

function installAdminSidebar() {
  if (!/\/admin\//.test(window.location.pathname) || document.querySelector(".admin-sidebar")) return;
  const links = [
    ["index.html", "工作台"], ["employees.html", "員工管理"],
    ["departments.html", "部門管理"], ["accounts.html", "帳號與權限"],
    ["leave-settings.html", "假別設定"], ["profile-requests.html", "資料修改申請"],
    ["system-log.html", "系統紀錄"]
  ];
  const current = window.location.pathname.split("/").pop() || "index.html";
  const group = current.startsWith("employee-") ? "employees.html"
    : current.startsWith("department-") ? "departments.html"
    : current.startsWith("account-") ? "accounts.html"
    : current.startsWith("leave-type-") ? "leave-settings.html"
    : current.startsWith("profile-request-") ? "profile-requests.html" : current;
  const aside = document.createElement("aside");
  aside.className = "admin-sidebar";
  aside.setAttribute("aria-label", "系統管理導覽");
  aside.innerHTML = `<a class="admin-sidebar-brand" href="index.html"><span>HR</span><strong>系統管理</strong></a><nav>${links.map(([href, label]) => `<a href="${href}" ${href === group ? 'aria-current="page"' : ""}>${label}</a>`).join("")}</nav><button type="button" class="admin-sidebar-logout" title="登出">${hrIcon("logout")}<span>登出</span></button>`;
  aside.querySelector("button").addEventListener("click", logout);
  document.body.prepend(aside);
  document.body.classList.add("has-admin-sidebar");
}

function promoteAdminDetailActions() {
  if (!/\/admin\/(employee|account|department|leave-type)-detail\.html$/.test(window.location.pathname)) return;
  const main = document.querySelector("main");
  const actions = main?.querySelector(":scope > .actions");
  const summary = main?.querySelector(":scope > .profile-card, :scope > .department-card, :scope > .hero");
  if (!actions || !summary) return;
  actions.classList.add("promoted-detail-actions");
  summary.insertAdjacentElement("afterend", actions);
}

function prioritizeDashboardTasks(section) {
  const grid = document.querySelector(".function-grid, .manager-actions");
  if (!grid || grid.dataset.organized === "true") return;
  const priorities = section === "employee"
    ? ["leave-assistant.html", "leave-history.html", "notifications.html"]
    : ["leave-requests.html", "late-notices.html", "team.html"];
  const cards = [...grid.children];
  const rank = (card) => {
    const href = card.matches("a") ? card.getAttribute("href") : card.querySelector("a")?.getAttribute("href");
    const index = priorities.findIndex((item) => href?.includes(item));
    return index < 0 ? 99 : index;
  };
  cards.sort((left, right) => {
    const leftHref = left.matches("a") ? left.getAttribute("href") : left.querySelector("a")?.getAttribute("href");
    const rightHref = right.matches("a") ? right.getAttribute("href") : right.querySelector("a")?.getAttribute("href");
    const hrefRank = (href) => { const index = priorities.findIndex((item) => href?.includes(item)); return index < 0 ? 99 : index; };
    return hrefRank(leftHref) - hrefRank(rightHref);
  }).forEach((card) => grid.appendChild(card));
  grid.dataset.organized = "true";

  if (section === "employee") {
    const secondary = cards.filter((card) => rank(card) === 99);
    if (secondary.length) {
      const details = document.createElement("details");
      details.className = "secondary-actions";
      details.innerHTML = '<summary>其他人事功能</summary><div class="secondary-action-grid"></div>';
      const secondaryGrid = details.querySelector(".secondary-action-grid");
      secondary.forEach((card) => secondaryGrid.appendChild(card));
      grid.insertAdjacentElement("afterend", details);
    }
    const heading = grid.previousElementSibling?.querySelector("h2");
    if (heading) heading.textContent = "常用任務";
  }
}

async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("hr_token");
  const tokenScheme = localStorage.getItem("hr_token_scheme") || "Token";
  const isLoginRequest = path.startsWith("/auth/login/") || path.startsWith("/mock-central/login/");
  const response = await fetch(`${HR_API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token && !isLoginRequest ? { Authorization: `${tokenScheme} ${token}` } : {}),
      ...(options.headers || {})
    }
  });

  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/auth/login/")) {
      localStorage.removeItem("hr_token");
      localStorage.removeItem("hr_token_scheme");
      localStorage.removeItem("hr_user");
      const roleSection = window.location.pathname.match(/\/(employee|manager|admin)\//)?.[1];
      if (roleSection) {
        const next = `${window.location.pathname}${window.location.search}`;
        window.location.href = `../index.html?next=${encodeURIComponent(next.replace(/^\//, ""))}`;
      }
      throw new Error("登入狀態已失效，請重新登入。");
    }
    let message = `API request failed: ${response.status}`;
    try {
      const payload = await response.json();
      message = payload.detail || Object.values(payload).flat().join(" ") || message;
    } catch {
      // Keep the HTTP status when the response is not JSON.
    }
    throw new Error(message);
  }

  return response.status === 204 ? null : response.json();
}

async function login(username, password) {
  // A stale token must never be sent with a new login request. DRF rejects the
  // request during authentication before it reaches the login view otherwise.
  localStorage.removeItem("hr_token");
  localStorage.removeItem("hr_token_scheme");
  localStorage.removeItem("hr_user");
  const data = await apiRequest("/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
  localStorage.setItem("hr_token", data.token);
  localStorage.setItem("hr_token_scheme", "Token");
  localStorage.setItem("hr_user", JSON.stringify(data.user));
  return data.user;
}

async function centralLogin(externalUserId) {
  localStorage.removeItem("hr_token");
  localStorage.removeItem("hr_token_scheme");
  localStorage.removeItem("hr_user");
  const data = await apiRequest("/mock-central/login/", {
    method: "POST",
    body: JSON.stringify({ external_user_id: externalUserId })
  });
  localStorage.setItem("hr_token", data.access_token);
  localStorage.setItem("hr_token_scheme", data.token_type || "Bearer");
  localStorage.setItem("hr_user", JSON.stringify(data.user));
  return data.user;
}

async function getCurrentUser() {
  return apiRequest("/auth/me/");
}

async function encodeAttachment(file, maxBytes = 2 * 1024 * 1024) {
  if (!file) return { attachment_name: "", attachment_data: "" };
  if (file.size > maxBytes) throw new Error("附件大小不可超過 2 MB。");
  const attachment_data = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("附件讀取失敗。"));
    reader.readAsDataURL(file);
  });
  return { attachment_name: file.name, attachment_data };
}

function downloadAttachment(name, data) {
  if (!data) return;
  const link = document.createElement("a");
  link.href = data;
  link.download = name || "attachment";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function logout() {
  localStorage.removeItem("hr_token");
  localStorage.removeItem("hr_token_scheme");
  localStorage.removeItem("hr_user");
  window.location.href = "../index.html";
}

document.addEventListener("DOMContentLoaded", async () => {
  const section = window.location.pathname.match(/\/(employee|manager|admin)\//)?.[1];
  installEnterpriseIcons();
  installAdminSidebar();
  promoteAdminDetailActions();
  prioritizeDashboardTasks(section);
  const notice = new URLSearchParams(window.location.search).get("notice");
  if (notice) {
    showHrToast(notice);
    const url = new URL(window.location.href);
    url.searchParams.delete("notice");
    history.replaceState({}, "", url);
  }
  if (!section || !localStorage.getItem("hr_token")) return;
  try {
    const user = await getCurrentUser();
    localStorage.setItem("hr_user", JSON.stringify(user));
    if (user.role !== section) window.location.replace(`../${user.role}/index.html`);
  } catch {
    // apiRequest handles expired credentials and redirects to login.
  }
});
