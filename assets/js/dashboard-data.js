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
    const [user, employeesPayload, requestsPayload] = await Promise.all([
      getCurrentUser(), apiRequest("/employees/"), apiRequest("/leave-requests/")
    ]);
    const employees = asList(employeesPayload).filter((employee) =>
      employee.role === "employee" && user.department && employee.department === user.department
    );
    const requests = asList(requestsPayload);
    const pending = requests.filter((item) => item.status === "pending");
    const today = new Date().toISOString().slice(0, 10);
    const todayLeave = requests.filter((item) =>
      item.status === "approved" && item.start_date <= today && item.end_date >= today
    );
    setValue(".manager-summary .summary-card strong", 0, String(pending.length));
    setValue(".manager-summary .summary-card strong", 1, "尚無資料");
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
    if (badges[1]) badges[1].textContent = "尚無資料";
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
