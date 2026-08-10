(function () {
  const setValue = (selector, index, value) => {
    const nodes = document.querySelectorAll(selector);
    if (nodes[index]) nodes[index].textContent = value;
  };
  const asList = (payload) => Array.isArray(payload) ? payload : (payload?.results || []);

  async function loadEmployeeDashboard() {
    const requests = asList(await apiRequest("/leave-requests/"));
    setValue(".summary-grid .summary-card strong", 0, "尚未設定");
    setValue(".summary-grid .summary-card strong", 1, String(requests.length));
    setValue(".summary-grid .summary-card strong", 2, "尚無資料");
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
    const todayLate = lateNotices;
    const todayLeave = requests.filter((item) =>
      item.status === "approved" && item.start_date <= today && item.end_date >= today
    );
    setValue(".manager-summary .summary-card strong", 0, String(pending.length));
    setValue(".manager-summary .summary-card strong", 1, String(todayLate.length));
    setValue(".manager-summary .summary-card strong", 2, String(employees.length));
    setValue(".manager-summary .summary-card strong", 3, String(todayLeave.length));

    const name = user.display_name || user.username;
    const heroTitle = document.querySelector(".manager-hero h1");
    const heroDescription = document.querySelector(".manager-hero p");
    const heroAvatar = document.querySelector(".manager-avatar");
    if (heroTitle) heroTitle.textContent = `${name}，您好`;
    if (heroDescription) heroDescription.textContent = `${user.department_name || "目前部門"}目前有 ${employees.length} 位直屬員工，待處理事項 ${pending.length} 件。`;
    if (heroAvatar) heroAvatar.textContent = name.slice(0, 1);
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
          <div><h3>${request.employee_name || "未提供姓名"}－${request.leave_type}</h3>
          <p>${request.start_date} 至 ${request.end_date}，共 ${request.days} 天</p></div>
          <span class="manager-task-status">${request.status_label || "待審核"}</span>
        </a>
      `).join("") : "<p>目前沒有待審核申請。</p>";
      taskList.insertAdjacentHTML("beforeend", content);
    }

    const teamList = document.querySelector("#teamPreviewList");
    if (teamList) {
      teamList.innerHTML = employees.map((employee) => `
        <a class="manager-employee" href="team-member-detail.html?id=${employee.id}">
          <div class="manager-employee-avatar">${(employee.display_name || employee.username || "員").slice(0, 1)}</div>
          <div><h3>${employee.display_name || employee.username}</h3><p>${employee.department_name || "—"}</p></div>
        </a>
      `).join("") || "<p>目前沒有直屬員工資料。</p>";
    }
  }

  async function loadAdminDashboard() {
    const [employeesPayload, departmentsPayload, requestsPayload] = await Promise.all([
      apiRequest("/employees/"), apiRequest("/departments/"), apiRequest("/leave-requests/")
    ]);
    const employees = asList(employeesPayload);
    const departments = asList(departmentsPayload);
    const requests = asList(requestsPayload);
    setValue(".summary-grid .summary-card strong", 0, String(employees.filter((item) => item.is_active).length));
    setValue(".summary-grid .summary-card strong", 1, String(departments.filter((item) => item.is_active).length));
    setValue(".summary-grid .summary-card strong", 2, String(requests.filter((item) => item.status === "pending").length));
    setValue(".summary-grid .summary-card strong", 3, String(employees.length));
  }

  document.addEventListener("DOMContentLoaded", async () => {
    if (!localStorage.getItem("hr_token")) return;
    try {
      const user = JSON.parse(localStorage.getItem("hr_user") || "{}");
      if (user.role === "employee") await loadEmployeeDashboard();
      if (user.role === "manager") await loadManagerDashboard();
      if (user.role === "admin") await loadAdminDashboard();
    } catch (error) {
      document.querySelectorAll(".summary-grid .summary-card strong").forEach((node) => { node.textContent = "無法載入"; });
      console.error("Dashboard data load failed", error);
    }
  });
})();
