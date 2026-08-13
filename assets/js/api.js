const HR_API_BASE_URL = window.HR_API_BASE_URL
  || (["127.0.0.1", "localhost"].includes(window.location.hostname)
    ? "http://127.0.0.1:8000/api"
    : "https://smart-hr-api-8rxh.onrender.com/api");

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
  if (!section || !localStorage.getItem("hr_token")) return;
  try {
    const user = await getCurrentUser();
    localStorage.setItem("hr_user", JSON.stringify(user));
    if (user.role !== section) window.location.replace(`../${user.role}/index.html`);
  } catch {
    // apiRequest handles expired credentials and redirects to login.
  }
});
