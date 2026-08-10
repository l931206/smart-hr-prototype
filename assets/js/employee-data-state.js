(function () {
  const empty = (text) => `<div class="card"><p>${text}</p></div>`;
  document.addEventListener("DOMContentLoaded", () => {
    if (!localStorage.getItem("hr_token")) return;
    const path = window.location.pathname;
    if (path.endsWith("/announcements.html")) {
      void (async () => {
        try {
          const payload = await apiRequest("/announcements/");
          const announcements = Array.isArray(payload) ? payload : (payload.results || []);
          document.querySelectorAll(".announcement-summary .summary-card strong").forEach((node, index) => {
            node.textContent = String(index === 0 ? announcements.length : index === 1 ? announcements.length : 0);
          });
          const list = document.querySelector(".announcement-list");
          if (!list) return;
          list.innerHTML = announcements.length ? announcements.map((item) => `<a class="announcement-card" href="announcement-detail.html?id=${item.id}"><div class="announcement-head"><div class="announcement-title-group"><div class="announcement-icon">📢</div><div><h2>${item.title}</h2><p>發布人：${item.author_name || "—"}</p></div></div><time class="announcement-date">${new Date(item.published_at || item.created_at).toLocaleDateString("zh-TW")}</time></div><p class="announcement-excerpt">${item.content}</p><span class="announcement-tag tag-company">${item.category_label || "公告"}</span><span class="announcement-view-link">查看公告內容 →</span></a>`).join("") : empty("目前尚無公告資料。");
        } catch (error) {
          const list = document.querySelector(".announcement-list");
          if (list) list.innerHTML = empty(`無法載入公告：${error.message}`);
        }
      })();
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
