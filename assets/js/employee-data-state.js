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
      void (async () => {
        try {
          const payload = await apiRequest("/notifications/");
          const notifications = Array.isArray(payload) ? payload : (payload.results || []);
          const unread = notifications.filter((item) => !item.is_read).length;
          const summary = document.querySelectorAll(".notification-summary .summary-card strong");
          if (summary[0]) summary[0].textContent = String(unread);
          if (summary[1]) summary[1].textContent = String(notifications.length);
          const list = document.querySelector(".notification-list");
          if (!list) return;
          list.innerHTML = notifications.length ? notifications.map((item) => `<a class="notification-card ${item.is_read ? "read" : "unread"}" href="notification-detail.html?id=${item.id}"><div class="notification-icon">🔔</div><div class="notification-content"><div class="notification-head"><h2>${item.title}</h2><time>${new Date(item.created_at).toLocaleString("zh-TW")}</time></div><p>${item.content}</p><span class="notification-status">${item.is_read ? "已讀" : "未讀"}</span></div></a>`).join("") : empty("目前尚無通知資料。");
        } catch (error) {
          const list = document.querySelector(".notification-list");
          if (list) list.innerHTML = empty(`無法載入通知：${error.message}`);
        }
      })();
    }
    if (path.endsWith("/index.html") && path.includes("/employee/")) {
      const jobTitle = document.querySelector("#jobTitle");
      const supervisor = document.querySelector(".employee-meta span:last-child");
      if (jobTitle) jobTitle.textContent = "尚無資料";
      if (supervisor) supervisor.textContent = "直屬主管：尚無資料";
      const panel = document.querySelector(".lower-grid .panel");
      if (panel) {
        void (async () => {
          try {
            const payload = await apiRequest("/announcements/");
            const announcements = Array.isArray(payload) ? payload : (payload.results || []);
            panel.querySelectorAll(".announcement-link").forEach((node) => node.remove());
            if (!announcements.length) {
              const message = document.createElement("p");
              message.textContent = "目前尚無公告資料。";
              panel.appendChild(message);
              return;
            }
            announcements.slice(0, 3).reverse().forEach((item) => {
              const link = document.createElement("a");
              link.className = "announcement announcement-link";
              link.href = `announcement-detail.html?id=${item.id}`;
              link.innerHTML = `<div><strong></strong><p></p></div><time></time>`;
              link.querySelector("strong").textContent = item.title;
              link.querySelector("p").textContent = item.content;
              link.querySelector("time").textContent = new Date(item.published_at || item.created_at).toLocaleDateString("zh-TW");
              panel.appendChild(link);
            });
          } catch (error) {
            const message = document.createElement("p");
            message.textContent = `無法載入公告：${error.message}`;
            panel.appendChild(message);
          }
        })();
      }
    }
  });
})();
