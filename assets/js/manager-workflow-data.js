(function () {
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));
  const id = () => new URLSearchParams(location.search).get("id");

  async function approvalDetail() {
    const requestId = id(); if (!requestId) return;
    const item = await apiRequest(`/leave-requests/${requestId}/`);
    document.querySelector(".approval-record-avatar").textContent = (item.employee_name || "員").slice(0,1);
    document.querySelector(".approval-record-head h1").textContent = `${item.employee_name || "未提供姓名"}－${item.leave_type}`;
    document.querySelector(".approval-record-head p").textContent = `申請編號：LEAVE-${String(item.id).padStart(6,"0")}`;
    document.querySelector(".approval-record-status").textContent = item.status_label;
    const values = document.querySelectorAll(".approval-record-info .approval-record-row strong");
    [item.employee_department || "—", item.leave_type, `${item.start_date} 至 ${item.end_date}`, `${item.days} 天`, item.reason || "—", item.attachment_name || "未上傳附件"].forEach((value,index) => { if(values[index]) values[index].textContent=value; });
    if (item.attachment_data && values[5]) { values[5].style.cursor="pointer"; values[5].title="點擊下載附件"; values[5].addEventListener("click",()=>downloadAttachment(item.attachment_name,item.attachment_data)); }
    const timeline = document.querySelectorAll(".approval-timeline-item p");
    if (timeline[0]) timeline[0].textContent = `${new Date(item.created_at).toLocaleString("zh-TW")}，由 ${item.employee_name || "員工"} 送出。`;
    if (timeline[1]) timeline[1].textContent = item.reviewed_at ? `${new Date(item.reviewed_at).toLocaleString("zh-TW")}，審核結果為${item.status_label}。` : "尚未完成審核。";
    document.querySelector(".approval-comment-box").textContent = item.reviewer_comment || "未填寫主管備註。";
    const employeeLink = document.querySelector('a[href="team-member-detail.html"]'); if(employeeLink) employeeLink.href=`team-member-detail.html?id=${item.employee}`;
  }

  async function approvalResult() {
    const requestId = id(); if (!requestId) return;
    const item = await apiRequest(`/leave-requests/${requestId}/`);
    const values = document.querySelectorAll(".approval-info-row strong, .rejection-info-row strong");
    const data = [item.employee_name || "—", `LEAVE-${String(item.id).padStart(6,"0")}`, item.leave_type, `${item.start_date}－${item.end_date}`, item.status_label];
    data.forEach((value,index) => { if(values[index]) values[index].textContent=value; });
  }

  async function announcementResult() {
    const announcementId = id(); if (!announcementId) return;
    const item = await apiRequest(`/announcements/${announcementId}/`);
    document.querySelectorAll(".info .row, .announcement-info .row").forEach((row) => {
      const label = row.querySelector("span")?.textContent || "";
      const value = row.querySelector("strong");
      if (!value) return;
      if (label.includes("標題")) value.textContent = item.title;
      else if (label.includes("編號")) value.textContent = `ANN-${item.id}`;
      else if (label.includes("類型")) value.textContent = item.category_label || "未分類";
      else if (label.includes("時間")) value.textContent = new Date(item.published_at || item.created_at).toLocaleString("zh-TW");
      else if (label.includes("範圍")) value.textContent = "所有使用者";
      else if (label.includes("狀態")) value.textContent = item.is_published ? "已發布" : "草稿";
    });
    document.querySelectorAll('a[href="announcement-detail.html"], a[href="announcement-edit.html"]').forEach((link) => { link.href = `${link.getAttribute("href")}?id=${item.id}`; });
  }

  async function announcementDeactivate() {
    const announcementId = id(); if (!announcementId) return;
    const item = await apiRequest(`/announcements/${announcementId}/`);
    const values = document.querySelectorAll(".info-box .row strong, .info .row strong");
    [item.title, `ANN-${item.id}`, item.category_label, item.is_published ? "已發布" : "草稿"].forEach((value,index) => { if(values[index]) values[index].textContent=value; });
    document.querySelectorAll('a[href="announcement-detail.html"]').forEach((link) => { link.href=`announcement-detail.html?id=${item.id}`; });
    document.querySelector(".button.danger")?.addEventListener("click", async (event) => { event.preventDefault(); await apiRequest(`/announcements/${item.id}/`, {method:"PATCH",body:JSON.stringify({is_published:false})}); location.href=`announcements.html?notice=${encodeURIComponent("公告已停用")}`; });
  }

  async function announcementEdit() {
    const announcementId = id(); if (!announcementId) return;
    const item = await apiRequest(`/announcements/${announcementId}/`);
    const card = document.querySelector(".announcement-detail-card, article.card, main article");
    if (!card) return;
    card.innerHTML = `<h1>編輯公告</h1><form id="announcementEditForm"><label>公告標題<input id="editAnnouncementTitle" value="${escapeHtml(item.title)}" required></label><label>公告內容<textarea id="editAnnouncementContent" required>${escapeHtml(item.content)}</textarea></label><label>目前附件<strong>${escapeHtml(item.attachment_name || "未上傳附件")}</strong><input id="editAnnouncementAttachment" type="file" accept=".pdf,.jpg,.jpeg,.png"></label><label>發布狀態<select id="editAnnouncementPublished"><option value="true" ${item.is_published ? "selected" : ""}>已發布</option><option value="false" ${!item.is_published ? "selected" : ""}>草稿</option></select></label><div class="actions"><button class="button primary" type="submit">儲存公告</button><a class="button secondary" href="announcement-detail.html?id=${item.id}">取消</a></div></form>`;
    card.querySelectorAll("input, textarea, select").forEach((field) => { field.style.cssText = "display:block;width:100%;margin:8px 0 18px;padding:12px;border:1px solid #d8e2ec;border-radius:10px;font:inherit"; });
    card.querySelector("form").addEventListener("submit", async (event) => { event.preventDefault(); const file=card.querySelector("#editAnnouncementAttachment").files[0]; const attachment=file ? await encodeAttachment(file) : {}; await apiRequest(`/announcements/${item.id}/`, {method:"PATCH",body:JSON.stringify({title:card.querySelector("#editAnnouncementTitle").value.trim(),content:card.querySelector("#editAnnouncementContent").value.trim(),is_published:card.querySelector("#editAnnouncementPublished").value === "true",...attachment})}); location.href=`announcement-detail.html?id=${item.id}&notice=${encodeURIComponent("公告已更新")}`; });
  }

  document.addEventListener("DOMContentLoaded", async () => {
    if (!localStorage.getItem("hr_token")) return;
    const path = location.pathname;
    try {
      if (path.endsWith("/approval-record-detail.html")) await approvalDetail();
      if (path.endsWith("/approval-success.html") || path.endsWith("/rejection-success.html")) await approvalResult();
      if (/announcement-(create|edit|draft|deactivate)-success\.html$/.test(path)) await announcementResult();
      if (path.endsWith("/announcement-deactivate.html")) await announcementDeactivate();
      if (path.endsWith("/announcement-edit.html")) await announcementEdit();
    } catch (error) {
      const main = document.querySelector("main");
      if (main) main.insertAdjacentHTML("beforeend", `<p>無法載入真實資料：${escapeHtml(error.message)}</p>`);
    }
  });
})();
