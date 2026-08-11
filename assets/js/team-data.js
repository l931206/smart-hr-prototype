(function () {
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>\"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[char]));

  document.addEventListener("DOMContentLoaded", async () => {
    const list = document.querySelector(".team-grid");
    if (!list || !localStorage.getItem("hr_token")) return;
    try {
      const [user, employeesPayload, requestsPayload, balancesPayload] = await Promise.all([
        getCurrentUser(), apiRequest("/employees/"), apiRequest("/leave-requests/"), apiRequest("/leave-balances/")
      ]);
      const employees = Array.isArray(employeesPayload) ? employeesPayload : (employeesPayload.results || []);
      const requests = Array.isArray(requestsPayload) ? requestsPayload : (requestsPayload.results || []);
      const balances = Array.isArray(balancesPayload) ? balancesPayload : (balancesPayload.results || []);
      const team = employees.filter((employee) =>
        user.department && employee.department === user.department && employee.role === "employee"
      );
      const pendingByEmployee = new Set(requests.filter((request) => request.status === "pending").map((request) => request.employee));
      const summary = document.querySelectorAll(".team-summary .summary-card strong");
      if (summary[0]) summary[0].textContent = String(team.length);
      if (summary[1]) summary[1].textContent = String(team.filter((employee) => employee.is_active).length);
      if (summary[2]) summary[2].textContent = String(team.filter((employee) => pendingByEmployee.has(employee.id)).length);
      const render = () => {
        const keyword = (document.querySelector(".team-toolbar input")?.value || "").trim().toLowerCase();
        const filtered = team.filter((employee) => `${employee.display_name} ${employee.employee_no} ${employee.email}`.toLowerCase().includes(keyword));
        list.innerHTML = filtered.length ? filtered.map((employee) => {
          const name = employee.display_name || employee.username;
          const pending = pendingByEmployee.has(employee.id);
          const employeeBalances = balances.filter((balance) => String(balance.employee) === String(employee.id));
          const annualBalance = employeeBalances.find((balance) => String(balance.leave_type_name || "").includes("特休")) || employeeBalances[0];
          const balanceText = annualBalance ? `${Number(annualBalance.remaining_days)} 天` : "未設定額度";
          return `<a class="team-member-card" href="team-member-detail.html?id=${employee.id}">
            <div class="team-member-head"><div class="team-member-main"><div class="team-member-avatar">${escapeHtml(name.slice(0, 1))}</div>
              <div><h2>${escapeHtml(name)}</h2><p>員工編號：${escapeHtml(employee.employee_no || "—")}</p></div>
            </div><span class="attendance-status ${pending ? "leave" : "normal"}">${pending ? "請假審核中" : (employee.is_active ? "在職" : "已停用")}</span></div>
            <div class="team-member-info"><div class="team-info-item"><span>電子郵件</span><strong>${escapeHtml(employee.email || "—")}</strong></div>
              <div class="team-info-item"><span>聯絡電話</span><strong>${escapeHtml(employee.phone || "—")}</strong></div>
              <div class="team-info-item"><span>到職日期</span><strong>${escapeHtml(employee.hire_date || "—")}</strong></div>
              <div class="team-info-item"><span>假期餘額</span><strong>${escapeHtml(balanceText)}</strong></div></div>
            <span class="team-view-link">查看員工資料 →</span></a>`;
        }).join("") : "<p class=\"empty-state\">目前沒有直屬員工資料。</p>";
      };
      document.querySelector(".team-toolbar input")?.addEventListener("input", render);
      render();
    } catch (error) {
      list.innerHTML = `<p class="empty-state">無法載入團隊資料：${escapeHtml(error.message)}</p>`;
    }
  });
})();
