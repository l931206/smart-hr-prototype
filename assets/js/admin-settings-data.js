(function () {
  const asList = (payload) => Array.isArray(payload) ? payload : (payload?.results || []);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));

  async function loadLeaveSettings() {
    const list = document.querySelector(".leave-list");
    if (!list) return;
    const types = asList(await apiRequest("/leave-types/"));
    const summary = document.querySelectorAll(".summary-grid .summary-card strong");
    if (summary[0]) summary[0].textContent = String(types.length);
    if (summary[1]) summary[1].textContent = String(types.filter((item) => item.is_active).length);
    if (summary[2]) summary[2].textContent = String(types.filter((item) => item.attachment_required).length);
    if (summary[3]) summary[3].textContent = String(types.filter((item) => item.deduct_quota).length);
    list.innerHTML = types.length ? types.map((item) => `<article class="leave-card"><div class="leave-head"><div class="leave-main"><div class="icon">📅</div><div><h2>${escapeHtml(item.name)}</h2><p>假別代碼：${escapeHtml(item.code)}</p></div></div><span class="status ${item.is_active ? "active" : "inactive"}">${item.is_active ? "啟用中" : "已停用"}</span></div><div class="details"><div class="detail"><span>年度額度</span><strong>${item.default_days} 天</strong></div><div class="detail"><span>薪資類型</span><strong>${item.is_paid ? "給薪" : "不給薪"}</strong></div><div class="detail"><span>建立日期</span><strong>${new Date(item.created_at).toLocaleDateString("zh-TW")}</strong></div></div><div class="rule-box">${escapeHtml(item.description || "尚未設定說明")}</div><div class="actions"><a class="button primary" href="leave-type-detail.html?id=${item.id}">查看詳情</a><a class="button secondary" href="leave-type-edit.html?id=${item.id}">編輯規則</a>${item.is_active ? `<a class="button danger" href="leave-type-deactivate.html?id=${item.id}">停用假別</a>` : ""}</div></article>`).join("") : "<p>目前尚無假別資料。</p>";
  }

  function bindLeaveTypeCreate() {
    const form = document.querySelector("form.form-card");
    if (!form) return;
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector("button[type=submit]");
      button.disabled = true;
      try {
        const payText = document.querySelector("#payType").selectedOptions[0]?.textContent || "";
        const item = await apiRequest("/leave-types/", {method:"POST", body:JSON.stringify({code:document.querySelector("#leaveCode").value.trim().toUpperCase(), name:document.querySelector("#leaveName").value.trim(), default_days:Number(document.querySelector("#annualQuota").value || 0), quota_type:document.querySelector("#quotaType").value, minimum_unit:document.querySelector("#minimumUnit").value, is_paid:Boolean(payText) && !payText.includes("無薪"), deduct_quota:document.querySelector("#deductQuota").checked, requires_manager_approval:document.querySelector("#managerApproval").checked, attachment_required:document.querySelector("#attachmentRequired").checked, allow_hourly:document.querySelector("#allowHourly").checked, allow_carry_over:document.querySelector("#allowCarryOver").checked, attachment_rule:document.querySelector("#attachmentRule").value.trim(), is_active:document.querySelector("#active").checked, description:document.querySelector("#description").value.trim()})});
        window.location.href = `leave-type-create-success.html?id=${item.id}`;
      } catch (error) { alert(error.message || "建立假別失敗。"); button.disabled = false; }
    });
  }

  async function loadLeaveTypeDetail() {
    const id = new URLSearchParams(location.search).get("id");
    if (!id) return;
    const [item, leavePayload] = await Promise.all([apiRequest(`/leave-types/${id}/`), apiRequest("/leave-requests/")]);
    const leaves = asList(leavePayload).filter((leave) => leave.leave_type === item.name);
    const hero = document.querySelector(".hero");
    if (hero) {
      hero.querySelector("h1").textContent = item.name;
      const heroParagraphs = hero.querySelectorAll("p");
      if (heroParagraphs[0]) heroParagraphs[0].textContent = `假別代碼：${item.code}`;
      if (heroParagraphs[1]) heroParagraphs[1].textContent = item.description || "尚未設定假別說明。";
      hero.querySelector(".status").textContent = item.is_active ? "啟用中" : "已停用";
    }
    const summary = document.querySelectorAll(".summary-grid .summary-card strong");
    const summaryLabels = document.querySelectorAll(".summary-grid .summary-card span");
    ["年度額度", "計薪方式", "本年度申請", "待審核申請"].forEach((label, index) => { if (summaryLabels[index]) summaryLabels[index].textContent = label; });
    if (summary[0]) summary[0].textContent = `${item.default_days} 天`;
    if (summary[1]) summary[1].textContent = item.is_paid ? "給薪" : "不給薪";
    if (summary[2]) summary[2].textContent = String(leaves.length);
    if (summary[3]) summary[3].textContent = String(leaves.filter((leave) => leave.status === "pending").length);
    const contentGrid = document.querySelector(".content-grid");
    if (contentGrid) contentGrid.innerHTML = `<article class="card"><h2>基本規則</h2>
      <div class="row"><span>假別名稱</span><strong>${escapeHtml(item.name)}</strong></div>
      <div class="row"><span>假別代碼</span><strong>${escapeHtml(item.code)}</strong></div>
      <div class="row"><span>年度額度</span><strong>${item.default_days} 天</strong></div>
      <div class="row"><span>額度類型</span><strong>${escapeHtml(item.quota_type)}</strong></div>
      <div class="row"><span>最小請假單位</span><strong>${escapeHtml(item.minimum_unit)}</strong></div>
      <div class="row"><span>計薪方式</span><strong>${item.is_paid ? "給薪" : "不給薪"}</strong></div>
      <div class="row"><span>扣除額度</span><strong>${item.deduct_quota ? "是" : "否"}</strong></div>
      <div class="row"><span>主管審核</span><strong>${item.requires_manager_approval ? "需要" : "不需要"}</strong></div>
      <div class="row"><span>要求附件</span><strong>${item.attachment_required ? "需要" : "不需要"}</strong></div>
      <div class="row"><span>允許小時申請</span><strong>${item.allow_hourly ? "是" : "否"}</strong></div>
      <div class="row"><span>允許跨年度</span><strong>${item.allow_carry_over ? "是" : "否"}</strong></div>
      <div class="row"><span>目前狀態</span><strong>${item.is_active ? "啟用中" : "已停用"}</strong></div>
      <div class="row"><span>建立日期</span><strong>${new Date(item.created_at).toLocaleDateString("zh-TW")}</strong></div></article>
      <article class="card"><h2>申請統計</h2>
      <div class="row"><span>全部申請</span><strong>${leaves.length} 件</strong></div>
      <div class="row"><span>等待審核</span><strong>${leaves.filter((leave) => leave.status === "pending").length} 件</strong></div>
      <div class="row"><span>已核准</span><strong>${leaves.filter((leave) => leave.status === "approved").length} 件</strong></div>
      <div class="row"><span>已退回</span><strong>${leaves.filter((leave) => leave.status === "rejected").length} 件</strong></div></article>`;
    const usage = document.querySelector('section.card[style] .rule-box');
    if (usage) usage.textContent = item.attachment_rule || item.description || "尚未設定使用說明。";
    document.querySelectorAll('a[href="leave-type-edit.html"]').forEach((link) => { link.href = `leave-type-edit.html?id=${id}`; });
    document.querySelectorAll('a[href="leave-type-deactivate.html"]').forEach((link) => { link.href = `leave-type-deactivate.html?id=${id}`; });
  }

  async function bindLeaveTypeEdit() {
    const id = new URLSearchParams(location.search).get("id");
    if (!id) return;
    const item = await apiRequest(`/leave-types/${id}/`);
    document.querySelector("#leaveName").value = item.name;
    document.querySelector("#leaveCode").value = item.code;
    document.querySelector("#description").value = item.description || "";
    document.querySelector("#annualQuota").value = item.default_days;
    document.querySelector("#quotaType").value = item.quota_type;
    document.querySelector("#minimumUnit").value = item.minimum_unit;
    document.querySelector("#payType").value = [...document.querySelector("#payType").options].find((option) => option.textContent.includes(item.is_paid ? "給薪" : "不給薪"))?.value || document.querySelector("#payType").value;
    document.querySelector("#active").checked = item.is_active;
    document.querySelector("#deductQuota").checked = item.deduct_quota;
    document.querySelector("#managerApproval").checked = item.requires_manager_approval;
    document.querySelector("#attachmentRequired").checked = item.attachment_required;
    document.querySelector("#allowHourly").checked = item.allow_hourly;
    document.querySelector("#allowCarryOver").checked = item.allow_carry_over;
    document.querySelector("#ruleDescription").value = item.attachment_rule || "";
    document.querySelectorAll('a[href="leave-type-detail.html"]').forEach((link) => { link.href = `leave-type-detail.html?id=${id}`; });
    document.querySelector("form.form-card").addEventListener("submit", async (event) => {
      event.preventDefault();
      const payText = document.querySelector("#payType").selectedOptions[0]?.textContent || "";
      await apiRequest(`/leave-types/${id}/`, {method:"PATCH", body:JSON.stringify({name:document.querySelector("#leaveName").value.trim(), description:document.querySelector("#description").value.trim(), default_days:Number(document.querySelector("#annualQuota").value || 0), quota_type:document.querySelector("#quotaType").value, minimum_unit:document.querySelector("#minimumUnit").value, is_paid:Boolean(payText) && !payText.includes("無薪"), deduct_quota:document.querySelector("#deductQuota").checked, requires_manager_approval:document.querySelector("#managerApproval").checked, attachment_required:document.querySelector("#attachmentRequired").checked, allow_hourly:document.querySelector("#allowHourly").checked, allow_carry_over:document.querySelector("#allowCarryOver").checked, attachment_rule:document.querySelector("#ruleDescription").value.trim(), is_active:document.querySelector("#active").checked})});
      location.href = `leave-type-edit-success.html?id=${id}`;
    });
  }

  async function bindLeaveTypeDeactivate() {
    const id = new URLSearchParams(location.search).get("id");
    if (!id) return;
    const [item, leavePayload] = await Promise.all([apiRequest(`/leave-types/${id}/`), apiRequest("/leave-requests/")]);
    const leaveCount = asList(leavePayload).filter((leave) => leave.leave_type === item.name).length;
    const values = document.querySelectorAll(".info-box .row strong, .info .row strong");
    if (values[0]) values[0].textContent = item.name;
    if (values[1]) values[1].textContent = item.code;
    if (values[2]) values[2].textContent = item.is_paid ? "給薪" : "不給薪";
    if (values[3]) values[3].textContent = `${leaveCount} 件`;
    if (values[4]) values[4].textContent = item.is_active ? "啟用中" : "已停用";
    document.querySelectorAll('a[href="leave-type-detail.html"]').forEach((link) => { link.href = `leave-type-detail.html?id=${id}`; });
    const button = document.querySelector(".button.danger");
    button?.addEventListener("click", async (event) => { event.preventDefault(); await apiRequest(`/leave-types/${id}/`, {method:"PATCH", body:JSON.stringify({is_active:false})}); location.href = `leave-type-deactivate-success.html?id=${id}`; });
  }

  async function loadLeaveTypeResult() {
    const id = new URLSearchParams(location.search).get("id");
    if (!id) return;
    const item = await apiRequest(`/leave-types/${id}/`);
    const values = document.querySelectorAll(".info .row strong, .leave-info .info-row strong");
    if (values[0]) values[0].textContent = item.name;
    if (values[1]) values[1].textContent = item.code;
    if (values[2]) values[2].textContent = item.is_paid ? "給薪" : "不給薪";
    if (values[3]) values[3].textContent = item.is_active ? "啟用中" : "已停用";
    document.querySelectorAll('a[href="leave-type-detail.html"]').forEach((link) => { link.href = `leave-type-detail.html?id=${id}`; });
  }

  async function loadProfileRequests() {
    const list = document.querySelector("#profileRequestList");
    if (!list) return;
    const requests = asList(await apiRequest("/profile-change-requests/"));
    const summary = document.querySelectorAll("#profileRequestSummary .card strong");
    if (summary[0]) summary[0].textContent = String(requests.filter((item) => item.status === "pending").length);
    if (summary[1]) summary[1].textContent = String(requests.filter((item) => item.status === "approved").length);
    if (summary[2]) summary[2].textContent = String(requests.filter((item) => item.status === "rejected").length);
    list.innerHTML = requests.length ? requests.map((item) => `<a class="request" href="profile-request-detail.html?id=${item.id}"><div class="head"><div><h2>${escapeHtml(item.employee_name || "未提供姓名")}</h2><p>員工編號：${escapeHtml(item.employee_no || "—")}</p></div><span class="status">${escapeHtml(item.status_label)}</span></div><div class="detail"><div class="item"><span>部門</span><strong>${escapeHtml(item.employee_department || "—")}</strong></div><div class="item"><span>申請時間</span><strong>${new Date(item.created_at).toLocaleString("zh-TW")}</strong></div></div><span class="link">查看申請內容 →</span></a>`).join("") : "<div class=\"card\"><p>目前沒有資料修改申請。</p></div>";
  }

  async function loadProfileRequestDetail() {
    const id = new URLSearchParams(location.search).get("id");
    if (!id) return;
    const requestItem = await apiRequest(`/profile-change-requests/${id}/`);
    const employee = await apiRequest(`/employees/${requestItem.employee}/`);
    const name = requestItem.employee_name || employee.display_name || employee.username;
    document.querySelector(".avatar").textContent = name.slice(0, 1);
    document.querySelector(".head h1").textContent = `${name}的資料修改申請`;
    document.querySelector(".head p").textContent = `申請編號：PROFILE-${requestItem.id}`;
    document.querySelector(".head .status").textContent = requestItem.status_label;
    const infoValues = document.querySelectorAll(".info-box .row strong");
    if (infoValues[0]) infoValues[0].textContent = requestItem.employee_no || "—";
    if (infoValues[1]) infoValues[1].textContent = requestItem.employee_department || "—";
    if (infoValues[2]) infoValues[2].textContent = employee.job_title || employee.role_label || "未設定職稱";
    if (infoValues[3]) infoValues[3].textContent = new Date(requestItem.created_at).toLocaleString("zh-TW");
    const oldValues = document.querySelectorAll(".change-card.old .row strong");
    const newValues = document.querySelectorAll(".change-card.new .row strong");
    if (oldValues[0]) oldValues[0].textContent = employee.email || "—";
    if (oldValues[1]) oldValues[1].textContent = employee.phone || "—";
    if (newValues[0]) newValues[0].textContent = requestItem.requested_data.email || employee.email || "—";
    if (newValues[1]) newValues[1].textContent = requestItem.requested_data.phone || employee.phone || "—";
    document.querySelector(".reason-box").textContent = requestItem.requested_data.reason || "員工申請更新個人資料。";
    const update = async (status, button) => {
      const comment = document.querySelector("#comment").value.trim();
      if (status === "rejected" && !comment) { alert("退回申請時請填寫管理者備註。"); return; }
      button.disabled = true;
      try {
        await apiRequest(`/profile-change-requests/${id}/`, {method:"PATCH", body:JSON.stringify({status, reviewer_comment:comment})});
        location.href = `${status === "approved" ? "profile-request-approved" : "profile-request-rejected"}.html?id=${id}`;
      } catch (error) { button.disabled = false; alert(error.message || "更新申請狀態失敗。"); }
    };
    document.querySelector("#profileDecisionForm").addEventListener("submit", (event) => { event.preventDefault(); void update("approved", document.querySelector(".button.approve")); });
    document.querySelector(".button.reject").addEventListener("click", (event) => { void update("rejected", event.currentTarget); });
  }

  async function loadProfileRequestResult() {
    const id = new URLSearchParams(location.search).get("id");
    if (!id) return;
    const requestItem = await apiRequest(`/profile-change-requests/${id}/`);
    const resultDescription = document.querySelector(".success-card > p, .result-card > p");
    if (resultDescription) resultDescription.textContent = requestItem.status === "approved"
      ? `系統已更新${requestItem.employee_name || "該員工"}的個人資料，並將審核結果傳送至員工通知中心。`
      : `${requestItem.employee_name || "該員工"}的資料修改申請已退回。`;
    const values = document.querySelectorAll(".info .row strong");
    if (values[0]) values[0].textContent = requestItem.employee_name || "—";
    if (values[1]) values[1].textContent = `PROFILE-${requestItem.id}`;
    if (values[2]) values[2].textContent = Object.keys(requestItem.requested_data || {}).filter((field) => ["display_name", "email", "phone", "avatar_data"].includes(field)).map((field) => ({display_name:"姓名",email:"電子郵件",phone:"聯絡電話",avatar_data:"頭貼"}[field])).join("、") || "—";
    if (values[3]) values[3].textContent = requestItem.status_label;
    const employeeLink = document.querySelector('a[href="employee-detail.html"]');
    if (employeeLink) employeeLink.href = `employee-detail.html?id=${requestItem.employee}`;
    const reason = document.querySelector(".reason");
    if (reason) reason.innerHTML = `<strong>退回原因：</strong><br>${escapeHtml(requestItem.reviewer_comment || "未填寫退回原因")}`;
  }

  document.addEventListener("DOMContentLoaded", async () => {
    if (!localStorage.getItem("hr_token")) return;
    const path = location.pathname;
    try {
      if (path.endsWith("/leave-settings.html")) await loadLeaveSettings();
      if (path.endsWith("/leave-type-create.html")) bindLeaveTypeCreate();
      if (path.endsWith("/leave-type-detail.html")) await loadLeaveTypeDetail();
      if (path.endsWith("/leave-type-edit.html")) await bindLeaveTypeEdit();
      if (path.endsWith("/leave-type-deactivate.html")) await bindLeaveTypeDeactivate();
      if (path.endsWith("/leave-type-create-success.html") || path.endsWith("/leave-type-edit-success.html") || path.endsWith("/leave-type-deactivate-success.html")) await loadLeaveTypeResult();
      if (path.endsWith("/profile-requests.html")) await loadProfileRequests();
      if (path.endsWith("/profile-request-detail.html")) await loadProfileRequestDetail();
      if (path.endsWith("/profile-request-approved.html") || path.endsWith("/profile-request-rejected.html")) await loadProfileRequestResult();
    } catch (error) {
      const target = document.querySelector(".leave-list, #profileRequestList");
      if (target) target.innerHTML = `<p>無法載入真實資料：${escapeHtml(error.message)}</p>`;
    }
  });
})();
