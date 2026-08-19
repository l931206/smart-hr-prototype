const assert = require("node:assert/strict");
const { chromium, request } = require("playwright");

const frontendUrl = process.env.HR_FRONTEND_URL || "http://127.0.0.1:5500";
const apiUrl = process.env.HR_API_URL || "http://127.0.0.1:8000";
const identities = {
  employee: "central-employee-001",
  manager: "central-manager-001",
  admin: "central-admin-001",
};

(async () => {
  const api = await request.newContext();
  const browser = await chromium.launch({ channel: "chrome", headless: true });

  const anonymous = await browser.newContext({ viewport: { width: 1280, height: 860 } });
  const loginPage = await anonymous.newPage();
  await loginPage.goto(`${frontendUrl}/`, { waitUntil: "networkidle" });
  await loginPage.getByRole("heading", { name: "登入系統" }).waitFor();
  assert.equal(await loginPage.locator("#loginForm").count(), 1, "首頁應直接顯示登入表單");
  assert.equal(await loginPage.locator(".role-grid").count(), 0, "首頁不應再要求使用者選擇角色");
  await loginPage.screenshot({ path: `${process.env.TEMP}/smart-hr-login-home.png`, fullPage: true });
  await anonymous.close();

  for (const [role, externalUserId] of Object.entries(identities)) {
    const loginResponse = await api.post(`${apiUrl}/api/mock-central/login/`, { data: { external_user_id: externalUserId } });
    assert.equal(loginResponse.status(), 200, `${role} 中控登入應成功`);
    const login = await loginResponse.json();
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    await context.addInitScript(({ token, user }) => {
      localStorage.setItem("hr_token", token);
      localStorage.setItem("hr_token_scheme", "Bearer");
      localStorage.setItem("hr_user", JSON.stringify(user));
    }, { token: login.access_token, user: login.user });
    const page = await context.newPage();
    await page.goto(`${frontendUrl}/`, { waitUntil: "networkidle" });
    await page.waitForURL(`**/${role}/index.html`);
    if (role === "employee") {
      await page.getByRole("heading", { name: "你今天要做什麼？" }).waitFor();
      assert.deepEqual(await page.locator(".task-card h3").allTextContents(), ["我要請假", "晚到通知", "請假紀錄", "通知中心"]);
      assert.equal(await page.locator(".task-card .task-icon svg").count(), 4, "任務卡應使用企業線性 SVG 圖示");
      assert.equal(await page.locator(".welcome-card").count(), 0, "不應再顯示大型裝飾性歡迎卡");
      await page.screenshot({ path: `${process.env.TEMP}/smart-hr-employee-task-home.png`, fullPage: true });
      await page.setViewportSize({ width: 390, height: 844 });
      await page.waitForTimeout(200);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      assert.ok(overflow <= 1, `員工手機首頁不應水平溢位，目前 ${overflow}px`);
      assert.equal(await page.locator(".mobile-nav svg").count(), 4, "手機導覽應使用一致的 SVG 圖示");
      await page.screenshot({ path: `${process.env.TEMP}/smart-hr-employee-task-home-mobile.png`, fullPage: true });
    }
    await context.close();
  }

  console.log(JSON.stringify({ passed: true, checks: ["首頁登入", "移除角色選擇", "員工自動導向", "主管自動導向", "管理者自動導向", "任務優先首頁", "企業 SVG 圖示", "手機無溢位"] }, null, 2));
  await browser.close();
  await api.dispose();
})().catch((error) => { console.error(error); process.exitCode = 1; });
