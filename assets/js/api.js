const HR_API_BASE_URL = window.HR_API_BASE_URL || "https://smart-hr-api-8rxh.onrender.com/api";

async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("hr_token");
  const response = await fetch(`${HR_API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Token ${token}` } : {}),
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
