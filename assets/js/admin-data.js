(function () {
  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>\"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
    }[char]));
  }

  function formatDate(value) {
    return value ? String(value).replaceAll("-", "/") : "—";
  }

  async function loadEmployees() {
    const list = document.querySelector(".employee-list");
    if (!list) return;
    const search = document.querySelector(".toolbar input[type=search]");
    const role = document.querySelector(".toolbar select");
    const status = document.querySelectorAll(".toolbar select")[1];
    let employees = [];
    try {
      employees = await apiRequest("/employees/");
    } catch (error) {
      list.innerHTML = `<p class="empty-state">無法載入員工資料：${escapeHtml(error.message)}</p>`;
      return;
    }

    const render = () => {
      const keyword = (search?.value || "").trim().toLowerCase();
      const roleValue = role?.value || "";
      const statusValue = status?.value || "";
      const filtered = employees.filter((employee) => {
        const text = `${employee.display_name} ${employee.employee_no} ${employee.email} ${employee.department_name}`.toLowerCase();
        const roleMatch = !roleValue || roleValue.includes("券") || roleValue.includes("全部") ||
          (roleValue.includes("員工") && employee.role === "employee") ||
          (roleValue.includes("主管") && employee.role === "manager") ||
          (roleValue.includes("管理") && employee.role === "admin");
        const statusMatch = !statusValue || statusValue.includes("全部") ||
          (statusValue.includes("啟") && employee.is_active) ||
          (statusValue.includes("停") && !employee.is_active);
        return text.includes(keyword) && roleMatch && statusMatch;
      });
      list.innerHTML = filtered.length ? filtered.map((employee) => `
        <a class="employee-card" href="employee-detail.html?id=${employee.id}">
          <div class="employee-head"><div class="employee-main">
            <div class="avatar">${escapeHtml((employee.display_name || employee.username).slice(0, 1))}</div>
            <div><h2>${escapeHtml(employee.display_name || employee.username)}</h2>
            <p>員工編號：${escapeHtml(employee.employee_no || "—")}</p></div>
          </div><span class="status ${employee.is_active ? "active" : "inactive"}">${employee.is_active ? "啟用" : "停用"}</span></div>
          <div class="employee-info">
            <div class="info-item"><span>部門</span><strong>${escapeHtml(employee.department_name || "—")}</strong></div>
            <div class="info-item"><span>角色</span><strong>${escapeHtml(employee.role_label || employee.role)}</strong></div>
            <div class="info-item"><span>電子郵件</span><strong>${escapeHtml(employee.email || "—")}</strong></div>
            <div class="info-item"><span>到職日期</span><strong>${formatDate(employee.hire_date)}</strong></div>
          </div><span class="view-link">查看員工資料 →</span>
        </a>`).join("") : `<p class="empty-state">目前沒有符合條件的員工資料。</p>`;
    };
    [search, role, status].filter(Boolean).forEach((element) => element.addEventListener("input", render));
    render();
  }

  async function loadDepartments() {
    const list = document.querySelector(".department-list");
    if (!list) return;
    const search = document.querySelector(".toolbar input[type=search]");
    const status = document.querySelector(".toolbar select");
    let departments = [];
    try {
      departments = await apiRequest("/departments/");
    } catch (error) {
      list.innerHTML = `<p class="empty-state">無法載入部門資料：${escapeHtml(error.message)}</p>`;
      return;
    }
    const render = () => {
      const keyword = (search?.value || "").trim().toLowerCase();
      const statusValue = status?.value || "";
      const filtered = departments.filter((department) =>
        `${department.code} ${department.name}`.toLowerCase().includes(keyword) &&
        (!statusValue || statusValue.includes("全部") ||
          (statusValue.includes("啟") && department.is_active) ||
          (statusValue.includes("停") && !department.is_active))
      );
      list.innerHTML = filtered.length ? filtered.map((department) => `
        <a class="department-card" href="department-detail.html?id=${department.id}">
          <div class="department-head"><div class="department-main"><div class="icon">▦</div>
            <div><h2>${escapeHtml(department.name)}</h2><p>部門代碼：${escapeHtml(department.code)}</p></div>
          </div><span class="status">${department.is_active ? "啟用" : "停用"}</span></div>
          <div class="department-info"><div class="info-item"><span>部門人數</span><strong>${department.employee_count} 人</strong></div>
            <div class="info-item"><span>建立日期</span><strong>${formatDate(String(department.created_at || "").slice(0, 10))}</strong></div>
          </div><span class="view-link">查看部門資料 →</span>
        </a>`).join("") : `<p class="empty-state">目前沒有符合條件的部門資料。</p>`;
    };
    const activeDepartments = departments.filter((department) => department.is_active);
    const employeeCount = departments.reduce((total, department) => total + Number(department.employee_count || 0), 0);
    const totalCount = document.querySelector("#departmentTotalCount");
    const activeCount = document.querySelector("#departmentActiveCount");
    const totalEmployees = document.querySelector("#departmentEmployeeCount");
    if (totalCount) totalCount.textContent = String(departments.length);
    if (activeCount) activeCount.textContent = String(activeDepartments.length);
    if (totalEmployees) totalEmployees.textContent = String(employeeCount);
    [search, status].filter(Boolean).forEach((element) => element.addEventListener("input", render));
    render();
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!localStorage.getItem("hr_token")) return;
    loadEmployees();
    loadDepartments();
  });
})();
