(function () {
  const setValue = (selector, index, value) => {
    const nodes = document.querySelectorAll(selector);
    if (nodes[index]) nodes[index].textContent = value;
  };

  const asList = (payload) => Array.isArray(payload) ? payload : (payload?.results || []);

  async function loadEmployeeDashboard() {
    const requests = asList(await apiRequest("/leave-requests/"));
    const summary = ".summary-grid .summary-card strong";
    // Leave balances and notifications need their own backend modules; do not show demo values.
    setValue(summary, 0, "尚未設定");
    setValue(summary, 1, String(requests.length));
    setValue(summary, 2, "尚無資料");
  }

  async function loadManagerDashboard() {
    const requests = asList(await apiRequest("/leave-requests/"));
    const summary = ".manager-summary .summary-card strong";
    setValue(summary, 0, String(requests.filter((item) => item.status === "pending").length));
    setValue(summary, 1, String(requests.filter((item) => item.status === "approved").length));
    setValue(summary, 2, String(requests.filter((item) => item.status === "rejected").length));
    setValue(summary, 3, "尚無資料");
  }

  async function loadAdminDashboard() {
    const [employeesPayload, departmentsPayload, requestsPayload] = await Promise.all([
      apiRequest("/employees/"), apiRequest("/departments/"), apiRequest("/leave-requests/")
    ]);
    const employees = asList(employeesPayload);
    const departments = asList(departmentsPayload);
    const requests = asList(requestsPayload);
    const summary = ".summary-grid .summary-card strong";
    setValue(summary, 0, String(employees.filter((item) => item.is_active).length));
    setValue(summary, 1, String(departments.filter((item) => item.is_active).length));
    setValue(summary, 2, String(requests.filter((item) => item.status === "pending").length));
    setValue(summary, 3, String(employees.length));
  }

  document.addEventListener("DOMContentLoaded", async () => {
    if (!localStorage.getItem("hr_token")) return;
    try {
      const user = JSON.parse(localStorage.getItem("hr_user") || "{}");
      if (user.role === "employee") await loadEmployeeDashboard();
      if (user.role === "manager") await loadManagerDashboard();
      if (user.role === "admin") await loadAdminDashboard();
    } catch (error) {
      document.querySelectorAll(".summary-grid .summary-card strong").forEach((node) => {
        node.textContent = "無法載入";
      });
      console.error("Dashboard data load failed", error);
    }
  });
})();
