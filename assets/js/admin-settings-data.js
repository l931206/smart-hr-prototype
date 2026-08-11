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
    if (summary[2]) summary[2].textContent = String(types.filter((item) => item.is_paid).length);
    if (summary[3]) summary[3].textContent = String(types.filter((item) => !item.is_active).length);
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
        const item = await apiRequest("/leave-types/", {method:"POST", body:JSON.stringify({code:document.querySelector("#leaveCode").value.trim().toUpperCase(), name:document.querySelector("#leaveName").value.trim(), default_days:Number(document.querySelector("#annualQuota").value || 0), is_paid:document.querySelector("#payType").value.includes("給薪"), is_active:document.querySelector("#active").checked, description:document.querySelector("#description").value.trim()})});
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
      hero.querySelector("p").textContent = `假別代碼：${item.code}`;
      hero.querySelector(".status").textContent = item.is_active ? "啟用中" : "已停用";
    }
    const summary = document.querySelectorAll(".summary-grid .summary-card strong");
    if (summary[0]) summary[0].textContent = `${item.default_days} 天`;
    if (summary[1]) summary[1].textContent = item.is_paid ? "給薪" : "不給薪";
    if (summary[2]) summary[2].textContent = String(leaves.length);
    if (summary[3]) summary[3].textContent = String(leaves.filter((leave) => leave.status === "pending").length);
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
    document.querySelector("#payType").value = [...document.querySelector("#payType").options].find((option) => option.textContent.includes(item.is_paid ? "給薪" : "不給薪"))?.value || document.querySelector("#payType").value;
    document.querySelector("#active").checked = item.is_active;
    document.querySelectorAll('a[href="leave-type-detail.html"]').forEach((link) => { link.href = `leave-type-detail.html?id=${id}`; });
    document.querySelector("form.form-card").addEventListener("submit", async (event) => {
      event.preventDefault();
      await apiRequest(`/leave-types/${id}/`, {method:"PATCH", body:JSON.stringify({name:document.querySelector("#leaveName").value.trim(), description:document.querySelector("#description").value.trim(), is_paid:document.querySelector("#payType").selectedOptions[0].textContent.includes("給薪") && !document.querySelector("#payType").selectedOptions[0].textContent.includes("不給薪"), is_active:document.querySelector("#active").checked})});
      location.href = `leave-type-edit-success.html?id=${id}`;
    });
  }

  async function bindLeaveTypeDeactivate() {
    const id = new URLSearchParams(location.search).get("id");
    if (!id) return;
    const item = await apiRequest(`/leave-types/${id}/`);
    const values = document.querySelectorAll(".info-box .row strong, .info .row strong");
    if (values[0]) values[0].textContent = item.name;
    if (values[1]) values[1].textContent = item.code;
    if (values[2]) values[2].textContent = item.is_active ? "啟用中" : "已停用";
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
    if (infoValues[2]) infoValues[2].textContent = employee.role_label || "—";
    if (infoValues[3]) infoValues[3].textContent = new Date(requestItem.created_at).toLocaleString("zh-TW");
    const oldValues = document.querySelectorAll(".change-card.old .row strong");
    const newValues = document.querySelectorAll(".change-card.new .row strong");
    if (oldValues[0]) oldValues[0].textContent = employee.email || "—";
    if (oldValues[1]) oldValues[1].textContent = employee.phone || "—";
    if (newValues[0]) newValues[0].textContent = requestItem.requested_data.email || employee.email || "—";
    if (newValues[1]) newValues[1].textContent = requestItem.requested_data.phone || employee.phone || "—";
    document.querySelector(".reason-box").textContent = "員工申請更新個人聯絡資料。";
    const update = async (status) => {
      await apiRequest(`/profile-change-requests/${id}/`, {method:"PATCH", body:JSON.stringify({status, reviewer_comment:document.querySelector("#comment").value.trim()})});
      location.href = `${status === "approved" ? "profile-request-approved" : "profile-request-rejected"}.html?id=${id}`;
    };
    document.querySelector(".button.approve").addEventListener("click", (event) => { event.preventDefault(); void update("approved"); });
    document.querySelector(".button.reject").addEventListener("click", (event) => { event.preventDefault(); void update("rejected"); });
  }

  async function loadProfileRequestResult() {
    const id = new URLSearchParams(location.search).get("id");
    if (!id) return;
    const requestItem = await apiRequest(`/profile-change-requests/${id}/`);
    const values = document.querySelectorAll(".info .row strong");
    if (values[0]) values[0].textContent = requestItem.employee_name || "—";
    if (values[1]) values[1].textContent = `PROFILE-${requestItem.id}`;
    if (values[2]) values[2].textContent = Object.keys(requestItem.requested_data || {}).map((field) => ({display_name:"姓名",email:"電子郵件",phone:"聯絡電話",avatar_data:"頭貼"}[field] || field)).join("、") || "—";
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
