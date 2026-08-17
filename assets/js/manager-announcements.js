(function () {
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>\"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[char]));
  document.addEventListener("DOMContentLoaded", async () => {
    const list = document.querySelector(".announcement-list");
    if (!list || !localStorage.getItem("hr_token")) return;
    try {
      const payload = await apiRequest("/announcements/");
      const announcements = Array.isArray(payload) ? payload : (payload.results || []);
      const summary = document.querySelectorAll(".summary-grid .summary-card strong");
      if (summary[0]) summary[0].textContent = String(announcements.filter((item) => item.is_published).length);
      if (summary[1]) summary[1].textContent = String(announcements.filter((item) => !item.is_published).length);
      if (summary[2]) summary[2].textContent = "尚無資料";
      const search = document.querySelector('input[type="search"]');
      const selects = document.querySelectorAll(".toolbar select, .filter-bar select");
      const categories = [...new Set(announcements.map((item) => item.category_label).filter(Boolean))];
      if (selects[1]) selects[1].innerHTML = `<option value="">全部類型</option>${categories.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("")}`;
      const render = () => {
        const keyword = (search?.value || "").trim().toLowerCase();
        const statusText = selects[0]?.value || "全部狀態";
        const category = selects[1]?.value || "";
        const filtered = announcements.filter((item) => `${item.title} ${item.content}`.toLowerCase().includes(keyword) && (!category || item.category_label === category) && (statusText.includes("全部") || (statusText.includes("發布") && item.is_published) || (statusText.includes("草稿") && !item.is_published)));
        list.innerHTML = filtered.length ? filtered.map((item) => `<article class="announcement-card"><div class="announcement-head"><div class="title-group"><div class="icon">公</div><div><h2>${escapeHtml(item.title)}</h2><p>公告編號：ANN-${Number(item.id)}</p></div></div><span class="status ${item.is_published ? "published" : "draft"}">${item.is_published ? "已發布" : "草稿"}</span></div><p class="excerpt">${escapeHtml(item.content)}</p><div class="details"><div class="detail"><span>公告類型</span><strong>${escapeHtml(item.category_label)}</strong></div><div class="detail"><span>發布人</span><strong>${escapeHtml(item.author_name || "—")}</strong></div><div class="detail"><span>發布時間</span><strong>${item.published_at ? new Date(item.published_at).toLocaleString("zh-TW") : "尚未發布"}</strong></div></div><div class="actions"><a class="button primary" href="announcement-detail.html?id=${Number(item.id)}">查看詳情</a></div></article>`).join("") : "<p class=\"empty-state\">目前尚無符合條件的公告資料。</p>";
      };
      [search, ...selects].filter(Boolean).forEach((element) => element.addEventListener("input", render));
      render();
    } catch (error) {
      list.innerHTML = `<p class="empty-state">無法載入公告：${escapeHtml(error.message)}</p>`;
    }
  });
})();
