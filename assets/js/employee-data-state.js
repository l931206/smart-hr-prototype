(function () {
  const empty = (text) => `<div class="card"><p>${text}</p></div>`;
  document.addEventListener("DOMContentLoaded", () => {
    if (!localStorage.getItem("hr_token")) return;
    const path = window.location.pathname;
    if (path.endsWith("/announcements.html")) {
      document.querySelectorAll(".announcement-summary .summary-card strong").forEach((node) => { node.textContent = "0"; });
      const list = document.querySelector(".announcement-list");
      if (list) list.innerHTML = empty("目前尚無公告資料。");
    }
    if (path.endsWith("/notifications.html")) {
      document.querySelectorAll(".notification-summary .summary-card strong").forEach((node) => { node.textContent = "0"; });
      const list = document.querySelector(".notification-list");
      if (list) list.innerHTML = empty("目前尚無通知資料。");
    }
    if (path.endsWith("/index.html") && path.includes("/employee/")) {
      const panel = document.querySelector(".lower-grid .panel");
      if (panel) {
        panel.querySelectorAll(".announcement-link").forEach((node) => node.remove());
        const message = document.createElement("p");
        message.textContent = "目前尚無公告資料。";
        panel.appendChild(message);
      }
    }
    if (path.endsWith("/late-notice.html")) {
      const form = document.querySelector(".late-form");
      if (form) {
        form.addEventListener("submit", (event) => {
          event.preventDefault();
          alert("晚到通知 API 尚未啟用，目前不會送出資料。");
        });
      }
    }
  });
})();
