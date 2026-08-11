const HR_API_BASE_URL = window.HR_API_BASE_URL
  || (["127.0.0.1", "localhost"].includes(window.location.hostname)
    ? "http://127.0.0.1:8000/api"
    : "https://smart-hr-api-8rxh.onrender.com/api");

async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("hr_token");
  const isLoginRequest = path.startsWith("/auth/login/");
  const response = await fetch(`${HR_API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token && !isLoginRequest ? { Authorization: `Token ${token}` } : {}),
      ...(options.headers || {})
    }
  });

  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/auth/login/")) {
      localStorage.removeItem("hr_token");
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
  localStorage.removeItem("hr_user");
  const data = await apiRequest("/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
  localStorage.setItem("hr_token", data.token);
  localStorage.setItem("hr_user", JSON.stringify(data.user));
  return data.user;
}

async function getCurrentUser() {
  return apiRequest("/auth/me/");
}

function logout() {
  localStorage.removeItem("hr_token");
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
