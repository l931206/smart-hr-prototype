const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium, request } = require("playwright");

const frontendUrl = process.env.HR_FRONTEND_URL || "http://127.0.0.1:5500";
const apiUrl = process.env.HR_API_URL || "http://127.0.0.1:8000";
const projectRoot = path.resolve(__dirname, "..", "..");
const identities = { employee: "central-employee-001", manager: "central-manager-001", admin: "central-admin-001" };

function rolePages(role) {
  return fs.readdirSync(path.join(projectRoot, role))
    .filter((name) => name.endsWith(".html"))
    .sort();
}

(async () => {
  const api = await request.newContext();
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const failures = [];
  let checked = 0;

  for (const [role, externalUserId] of Object.entries(identities)) {
    const loginResponse = await api.post(`${apiUrl}/api/mock-central/login/`, { data: { external_user_id: externalUserId } });
    assert.equal(loginResponse.status(), 200, `${role} 測試登入應成功`);
    const login = await loginResponse.json();
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    await context.addInitScript(({ token, user }) => {
      localStorage.setItem("hr_token", token);
      localStorage.setItem("hr_token_scheme", "Bearer");
      localStorage.setItem("hr_user", JSON.stringify(user));
    }, { token: login.access_token, user: login.user });
    const page = await context.newPage();

    for (const file of rolePages(role)) {
      const suffix = /(?:detail|edit|deactivate|disable|reset|confirm)/.test(file) ? "?id=1" : "";
      await page.goto(`${frontendUrl}/${role}/${file}${suffix}`, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(180);
      const result = await page.evaluate(() => {
        const visible = (element) => {
          const style = getComputedStyle(element);
          return style.display !== "none" && style.visibility !== "hidden" && element.getBoundingClientRect().width > 0;
        };
        const undersizedButtons = [...document.querySelectorAll("button, a.button, .round-button")]
          .filter(visible)
          .map((element) => element.getBoundingClientRect())
          .filter((box) => box.height < 36 || box.width < 36).length;
        const unresolvedTextIcons = [...document.querySelectorAll(".function-icon, .manager-action-icon, .admin-action-icon, .warning-icon, .success-icon, .result-icon")]
          .filter(visible)
          .filter((element) => !element.querySelector("svg")).length;
        return {
          overflow: document.documentElement.scrollWidth - window.innerWidth,
          mainWidth: document.querySelector("main")?.getBoundingClientRect().width || 0,
          hasHeading: Boolean(document.querySelector("h1")),
          undersizedButtons,
          unresolvedTextIcons,
          pathname: location.pathname,
        };
      });
      checked += 1;
      if (result.overflow > 1) failures.push(`${role}/${file}: 手機水平溢位 ${result.overflow}px`);
      if (result.mainWidth && result.mainWidth < 300) failures.push(`${role}/${file}: 手機主內容過窄 ${Math.round(result.mainWidth)}px`);
      if (!result.pathname.includes(`/${role}/`)) failures.push(`${role}/${file}: 非預期導向 ${result.pathname}`);
      if (result.undersizedButtons) failures.push(`${role}/${file}: ${result.undersizedButtons} 個操作按鈕觸控範圍過小`);
      if (result.unresolvedTextIcons) failures.push(`${role}/${file}: ${result.unresolvedTextIcons} 個功能圖示仍為文字`);
      if (["employee/leave-apply.html", "manager/leave-request-detail.html", "admin/employee-detail.html", "admin/account-create.html"].includes(`${role}/${file}`)) {
        await page.screenshot({ path: `${process.env.TEMP}/smart-hr-audit-${role}-${file.replace(".html", "")}.png`, fullPage: true });
      }
    }
    await context.close();
  }

  await browser.close();
  await api.dispose();
  if (failures.length) {
    console.error(JSON.stringify({ passed: false, checked, failures }, null, 2));
    process.exitCode = 1;
    return;
  }
  console.log(JSON.stringify({ passed: true, checked, roles: Object.keys(identities), checks: ["手機無水平溢位", "主內容寬度正常", "角色頁面未錯誤導向", "操作按鈕觸控範圍", "企業 SVG 功能圖示"] }, null, 2));
})().catch((error) => { console.error(error); process.exitCode = 1; });
