(function () {
  const empty = (text) => `<div class="card"><p>${escapeHtml(text)}</p></div>`;
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));
  document.addEventListener("DOMContentLoaded", () => {
    if (!localStorage.getItem("hr_token")) return;
    const path = window.location.pathname;
    if (path.endsWith("/announcements.html")) {
      void (async () => {
        try {
          const payload = await apiRequest("/announcements/");
          const announcements = Array.isArray(payload) ? payload : (payload.results || []);
          const now = new Date();
          const currentMonth = announcements.filter((item) => { const date = new Date(item.published_at || item.created_at); return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth(); });
          const summary = document.querySelectorAll(".announcement-summary .summary-card strong");
          if (summary[0]) summary[0].textContent = String(announcements.length);
          if (summary[1]) summary[1].textContent = String(currentMonth.length);
          if (summary[2]) summary[2].textContent = "尚無資料";
          const list = document.querySelector(".announcement-list");
          if (!list) return;
          const search = document.querySelector('input[type="search"]');
          const selects = document.querySelectorAll("select");
          const categories = [...new Set(announcements.map((item) => item.category_label).filter(Boolean))];
          if (selects[0]) selects[0].innerHTML = `<option value="">全部類型</option>${categories.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("")}`;
          const render = () => {
            const keyword = (search?.value || "").trim().toLowerCase();
            const category = selects[0]?.value || "";
            let filtered = announcements.filter((item) => `${item.title} ${item.content}`.toLowerCase().includes(keyword) && (!category || item.category_label === category));
            filtered = [...filtered].sort((a, b) => (selects[1]?.selectedIndex === 1 ? 1 : -1) * (new Date(b.published_at || b.created_at) - new Date(a.published_at || a.created_at)));
            list.innerHTML = filtered.length ? filtered.map((item) => `<a class="announcement-card" href="announcement-detail.html?id=${Number(item.id)}"><div class="announcement-head"><div class="announcement-title-group"><div class="announcement-icon">公</div><div><h2>${escapeHtml(item.title)}</h2><p>發布人：${escapeHtml(item.author_name || "—")}</p></div></div><time class="announcement-date">${new Date(item.published_at || item.created_at).toLocaleDateString("zh-TW")}</time></div><p class="announcement-excerpt">${escapeHtml(item.content)}</p><span class="announcement-tag tag-company">${escapeHtml(item.category_label || "公告")}</span><span class="announcement-view-link">查看公告內容 →</span></a>`).join("") : empty("目前尚無符合條件的公告資料。");
          };
          [search, ...selects].filter(Boolean).forEach((element) => element.addEventListener("input", render));
          render();
        } catch (error) {
          const list = document.querySelector(".announcement-list");
          if (list) list.innerHTML = empty(`無法載入公告：${escapeHtml(error.message)}`);
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
          list.innerHTML = notifications.length ? notifications.map((item) => `<a class="notification-card ${item.is_read ? "read" : "unread"}" href="notification-detail.html?id=${Number(item.id)}"><div class="notification-icon">知</div><div class="notification-content"><div class="notification-head"><h2>${escapeHtml(item.title)}</h2><time>${escapeHtml(new Date(item.created_at).toLocaleString("zh-TW"))}</time></div><p>${escapeHtml(item.content)}</p><span class="notification-status">${item.is_read ? "已讀" : "未讀"}</span></div></a>`).join("") : empty("目前尚無通知資料。");
          const markAll = [...document.querySelectorAll("button")].find((button) => button.textContent.includes("全部標示為已讀"));
          markAll?.addEventListener("click", async () => {
            markAll.disabled = true;
            await Promise.all(notifications.filter((item) => !item.is_read).map((item) => apiRequest(`/notifications/${item.id}/`, { method: "PATCH", body: JSON.stringify({ is_read: true }) })));
            window.location.reload();
          });
        } catch (error) {
          const list = document.querySelector(".notification-list");
          if (list) list.innerHTML = empty(`無法載入通知：${escapeHtml(error.message)}`);
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
