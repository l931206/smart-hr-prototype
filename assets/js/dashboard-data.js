(function () {
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[char]);
  const setValue = (selector, index, value) => {
    const nodes = document.querySelectorAll(selector);
    if (nodes[index]) nodes[index].textContent = value;
  };
  const asList = (payload) => Array.isArray(payload) ? payload : (payload?.results || []);

  async function loadEmployeeDashboard() {
    const [requestPayload, notificationPayload, balancePayload] = await Promise.all([apiRequest("/leave-requests/"), apiRequest("/notifications/"), apiRequest("/leave-balances/")]);
    const requests = asList(requestPayload);
    const notifications = asList(notificationPayload);
    const balances = asList(balancePayload);
    const annual = balances.find((item) => item.leave_type_name.includes("特休")) || balances[0];
    setValue(".stat-grid .stat-card strong", 0, annual ? String(Number(annual.remaining_days)) : "0");
    setValue(".stat-grid .stat-card strong", 1, String(requests.filter((item) => item.status === "pending").length));
    setValue(".stat-grid .stat-card strong", 2, String(notifications.filter((item) => !item.is_read).length));
    const units = document.querySelectorAll(".stat-grid .stat-card .stat-value span");
    if (units[0]) units[0].textContent = "天";
    const dateText = new Intl.DateTimeFormat("zh-TW", { year: "numeric", month: "long", day: "numeric" }).format(new Date());
    const welcomeDescription = document.querySelector("#dashboardDate");
    if (welcomeDescription) welcomeDescription.textContent = `今天是 ${dateText}`;
  }

  async function loadManagerDashboard() {
    const [user, employeesPayload, requestsPayload, latePayload] = await Promise.all([
      getCurrentUser(), apiRequest("/employees/"), apiRequest("/leave-requests/"), apiRequest("/late-notices/")
    ]);
    const employees = asList(employeesPayload).filter((employee) =>
      employee.role === "employee" && user.department && employee.department === user.department
    );
    const requests = asList(requestsPayload);
    const lateNotices = asList(latePayload);
    const pending = requests.filter((item) => item.status === "pending");
    const today = new Date().toISOString().slice(0, 10);
    const todayLate = lateNotices.filter((item) => String(item.late_date || item.date || "").slice(0, 10) === today);
    const todayLeave = requests.filter((item) =>
      item.status === "approved" && item.start_date <= today && item.end_date >= today
    );
    setValue(".manager-summary .summary-card strong", 0, String(pending.length));
    setValue(".manager-summary .summary-card strong", 1, String(todayLate.length));
    setValue(".manager-summary .summary-card strong", 2, String(employees.length));
    setValue(".manager-summary .summary-card strong", 3, String(todayLeave.length));

    const name = user.display_name || user.username;
    const heroTitle = document.querySelector(".manager-overview h1, .manager-hero h1");
    const heroDescription = document.querySelector(".manager-overview > div > p, .manager-hero p");
    const heroAvatar = document.querySelector(".manager-avatar");
    if (heroTitle) heroTitle.textContent = `${name}，您好`;
    if (heroDescription) heroDescription.textContent = pending.length ? `今天有 ${pending.length} 件請假申請需要處理。` : "目前沒有待審核的請假申請。";
    if (heroAvatar) heroAvatar.textContent = name.slice(0, 1);
    const profileName = document.querySelector(".manager-profile strong");
    const departmentMeta = document.querySelector("#managerDepartment");
    const teamMeta = document.querySelector("#managerTeamMeta");
    if (profileName) profileName.textContent = name;
    if (departmentMeta) departmentMeta.textContent = user.department_name || "尚未設定部門";
    if (teamMeta) teamMeta.textContent = `${employees.length} 位直屬員工`;
    const badges = document.querySelectorAll(".manager-action-badge");
    if (badges[0]) badges[0].textContent = `${pending.length} 件待處理`;
    if (badges[1]) badges[1].textContent = `${todayLate.length} 則通知`;

    const taskList = document.querySelector("#pendingTasksPanel");
    if (taskList) {
      const heading = taskList.querySelector("h2");
      taskList.innerHTML = "";
      if (heading) taskList.appendChild(heading);
      const content = pending.length ? pending.slice(0, 3).map((request) => `
        <a class="manager-task" href="leave-request-detail.html?id=${request.id}">
          <div><h3>${escapeHtml(request.employee_name || "未提供姓名")}－${escapeHtml(request.leave_type)}</h3>
          <p>${escapeHtml(request.start_date)} 至 ${escapeHtml(request.end_date)}，共 ${escapeHtml(formatLeaveDuration(request.days))}</p></div>
          <span class="manager-task-status">${escapeHtml(request.status_label || "待審核")}</span>
        </a>
      `).join("") : "<p>目前沒有待審核申請。</p>";
      taskList.insertAdjacentHTML("beforeend", content);
    }

    const teamList = document.querySelector("#teamPreviewList");
    if (teamList) {
      teamList.innerHTML = employees.map((employee) => `
        <a class="manager-employee" href="team-member-detail.html?id=${employee.id}">
          <div class="manager-employee-avatar">${escapeHtml((employee.display_name || employee.username || "員").slice(0, 1))}</div>
          <div><h3>${escapeHtml(employee.display_name || employee.username)}</h3><p>${escapeHtml(employee.department_name || "—")}</p></div>
        </a>
      `).join("") || "<p>目前沒有直屬員工資料。</p>";
    }
  }

  async function loadAdminDashboard() {
    const [employeesPayload, accountsPayload, departmentsPayload, requestsPayload, auditPayload] = await Promise.all([
      apiRequest("/employees/"), apiRequest("/accounts/"), apiRequest("/departments/"), apiRequest("/profile-change-requests/"), apiRequest("/audit-logs/")
    ]);
    const employees = asList(employeesPayload);
    const accounts = asList(accountsPayload);
    const departments = asList(departmentsPayload);
    const requests = asList(requestsPayload);
    const audits = asList(auditPayload);
    setValue(".summary-grid .summary-card strong", 0, String(employees.filter((item) => item.is_active).length));
    setValue(".summary-grid .summary-card strong", 1, String(departments.filter((item) => item.is_active).length));
    setValue(".summary-grid .summary-card strong", 2, String(requests.filter((item) => item.status === "pending").length));
    setValue(".summary-grid .summary-card strong", 3, String(accounts.filter((item) => item.is_active).length));

    const pending = requests.filter((item) => item.status === "pending");
    const profileCard = [...document.querySelectorAll(".action-card")].find((card) => card.getAttribute("href") === "profile-requests.html");
    const badge = profileCard?.querySelector(".badge");
    if (badge) badge.textContent = `${pending.length} 件待處理`;

    const panels = document.querySelectorAll(".panel-grid .panel");
    if (panels[0]) {
      panels[0].innerHTML = `<h2>等待處理</h2>${pending.length ? pending.slice(0, 5).map((request) => `
        <a class="task" href="profile-request-detail.html?id=${request.id}">
          <div><h3>${escapeHtml(request.employee_name || "未提供姓名")}－個人資料修改申請</h3>
          <p>申請編號：PROFILE-${escapeHtml(request.id)}</p></div><span class="task-status">等待審核</span>
        </a>`).join("") : "<p>目前沒有待處理的資料修改申請。</p>"}`;
    }
    if (panels[1]) panels[1].innerHTML = `<h2>近期系統活動</h2>${audits.length ? audits.slice(0, 5).map((item) => `<div class="activity"><h3>${escapeHtml(item.action)} ${escapeHtml(item.target_type)}</h3><p>${escapeHtml(item.actor_name)}｜${escapeHtml(item.target_label || "—")}｜${escapeHtml(new Date(item.created_at).toLocaleString("zh-TW"))}</p></div>`).join("") : "<p>目前尚無可顯示的操作紀錄。</p>"}`;
  }

  document.addEventListener("DOMContentLoaded", async () => {
    if (!localStorage.getItem("hr_token")) return;
    try {
      const user = JSON.parse(localStorage.getItem("hr_user") || "{}");
      if (user.role === "employee") await loadEmployeeDashboard();
      if (user.role === "manager") await loadManagerDashboard();
      if (user.role === "admin") await loadAdminDashboard();
    } catch (error) {
      document.querySelectorAll(".summary-grid .summary-card strong, .stat-grid .stat-card strong").forEach((node) => { node.textContent = "無法載入"; });
      console.error("Dashboard data load failed", error);
    }
  });
})();
