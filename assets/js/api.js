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
    link.href = new URL(`../css/${file}?v=20260817-review2`, scriptUrl).href;
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
  aside.innerHTML = `<a class="admin-sidebar-brand" href="index.html"><span>HR</span><strong>系統管理</strong></a><nav>${links.map(([href, label]) => `<a href="${href}" ${href === group ? 'aria-current="page"' : ""}>${label}</a>`).join("")}</nav><button type="button" class="admin-sidebar-logout">登出</button>`;
  aside.querySelector("button").addEventListener("click", logout);
  document.body.prepend(aside);
  document.body.classList.add("has-admin-sidebar");
}

function prioritizeDashboardTasks(section) {
  const grid = document.querySelector(".function-grid, .manager-actions");
  if (!grid || grid.dataset.organized === "true") return;
  const priorities = section === "employee"
    ? ["leave-apply.html", "leave-history.html", "notifications.html"]
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
      const next = `${window.location.pathname}${window.location.search}`;
      window.location.href = `../login.html?next=${encodeURIComponent(next.replace(/^\//, ""))}`;
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
  window.location.href = "../login.html";
}

document.addEventListener("DOMContentLoaded", async () => {
  const section = window.location.pathname.match(/\/(employee|manager|admin)\//)?.[1];
  installAdminSidebar();
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
