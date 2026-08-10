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
      list.innerHTML = announcements.length ? announcements.map((item) => `<article class="announcement-card"><div class="announcement-head"><div class="title-group"><div class="icon">📢</div><div><h2>${escapeHtml(item.title)}</h2><p>公告編號：ANN-${item.id}</p></div></div><span class="status ${item.is_published ? "published" : "draft"}">${item.is_published ? "已發布" : "草稿"}</span></div><p class="excerpt">${escapeHtml(item.content)}</p><div class="details"><div class="detail"><span>公告類型</span><strong>${escapeHtml(item.category_label)}</strong></div><div class="detail"><span>發布人</span><strong>${escapeHtml(item.author_name || "—")}</strong></div><div class="detail"><span>發布時間</span><strong>${item.published_at ? new Date(item.published_at).toLocaleString("zh-TW") : "尚未發布"}</strong></div></div><div class="actions"><a class="button primary" href="announcement-detail.html?id=${item.id}">查看詳情</a></div></article>`).join("") : "<p class=\"empty-state\">目前尚無公告資料。</p>";
    } catch (error) {
      list.innerHTML = `<p class="empty-state">無法載入公告：${escapeHtml(error.message)}</p>`;
    }
  });
})();
