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
  await loginPage.goto(`${frontendUrl}/login.html`, { waitUntil: "domcontentloaded" });
  await loginPage.waitForURL((url) => url.pathname === "/index.html");
  await loginPage.goto(`${frontendUrl}/`, { waitUntil: "networkidle" });
  await loginPage.getByRole("heading", { name: "登入系統" }).waitFor();
  assert.equal(await loginPage.locator("#loginForm").count(), 1, "首頁應直接顯示登入表單");
  assert.equal(await loginPage.locator(".role-grid").count(), 0, "首頁不應再要求使用者選擇角色");
  await loginPage.screenshot({ path: `${process.env.TEMP}/smart-hr-login-home.png`, fullPage: true });
  await loginPage.setViewportSize({ width: 390, height: 844 });
  await loginPage.goto(`${frontendUrl}/central-login.html`, { waitUntil: "networkidle" });
  assert.equal(await loginPage.locator(".role-icon svg").count(), 3, "中控示範身分應使用企業 SVG 圖示");
  const centralOverflow = await loginPage.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  assert.ok(centralOverflow <= 1, `中控登入手機版不應水平溢位，目前 ${centralOverflow}px`);
  await anonymous.close();

  for (const [role, externalUserId] of Object.entries(identities)) {
    const loginResponse = await api.post(`${apiUrl}/api/mock-central/login/`, { data: { external_user_id: externalUserId } });
    assert.equal(loginResponse.status(), 200, `${role} 中控登入應成功`);
    const login = await loginResponse.json();
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    await context.addInitScript(({ token, user }) => {
      if (sessionStorage.getItem("hr_test_session_initialized")) return;
      sessionStorage.setItem("hr_test_session_initialized", "1");
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
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.goto(`${frontendUrl}/employee/profile.html`, { waitUntil: "networkidle" });
      await page.getByRole("heading", { name: "我的資料" }).waitFor();
      assert.equal(await page.locator(".profile-hero").count(), 0, "個人資料頁不應顯示大型裝飾性區塊");
      assert.equal(await page.locator(".profile-content .profile-card").count(), 2, "個人與職務資料應使用緊湊雙區塊");
      assert.equal(await page.locator("a[aria-label='返回員工首頁'] svg").count(), 1, "個人資料頁右上角應提供返回員工首頁圖示");
      assert.equal(await page.locator("button[aria-label='登出']").count(), 0, "個人資料子頁不應將返回操作設為登出");
      await page.getByRole("link", { name: "申請修改資料" }).first().waitFor();
      await page.screenshot({ path: `${process.env.TEMP}/smart-hr-profile-desktop.png`, fullPage: true });
      await page.setViewportSize({ width: 390, height: 844 });
      await page.waitForTimeout(150);
      const mobileEditButton = page.locator(".mobile-profile-action");
      await mobileEditButton.waitFor();
      const editBox = await mobileEditButton.boundingBox();
      assert.ok(editBox && editBox.y < 844, "手機版修改資料按鈕應固定顯示在第一視線");
      const profileOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      assert.ok(profileOverflow <= 1, `個人資料手機版不應水平溢位，目前 ${profileOverflow}px`);
      await page.screenshot({ path: `${process.env.TEMP}/smart-hr-profile-mobile.png`, fullPage: true });
    }
    if (role === "manager") {
      await page.getByRole("heading", { name: "你今天要處理什麼？" }).waitFor();
      assert.deepEqual(await page.locator(".manager-action-card h3").allTextContents(), ["審核請假", "晚到通知", "我的團隊", "部門日曆"]);
      assert.equal(await page.locator(".manager-action-card .manager-action-icon svg").count(), 4, "主管任務卡應使用企業線性 SVG 圖示");
      assert.equal(await page.locator("button[aria-label='登出'] svg").count(), 1, "主管應顯示統一登出圖示");
      assert.equal(await page.locator(".manager-hero").count(), 0, "主管首頁不應再顯示大型裝飾性橫幅");
      await page.screenshot({ path: `${process.env.TEMP}/smart-hr-manager-task-home.png`, fullPage: true });
      await page.setViewportSize({ width: 390, height: 844 });
      await page.waitForTimeout(200);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      assert.ok(overflow <= 1, `主管手機首頁不應水平溢位，目前 ${overflow}px`);
      assert.equal(await page.locator(".mobile-nav svg").count(), 4, "主管手機導覽應使用一致的 SVG 圖示");
      await page.screenshot({ path: `${process.env.TEMP}/smart-hr-manager-task-home-mobile.png`, fullPage: true });
    }
    if (role === "admin") {
      await page.getByRole("heading", { name: "你要管理什麼？" }).waitFor();
      assert.deepEqual(await page.locator(".action-card h2").allTextContents(), ["員工管理", "帳號與權限", "部門管理", "資料修改申請"]);
      assert.equal(await page.locator(".action-card .admin-action-icon svg").count(), 4, "管理者任務卡應使用企業線性 SVG 圖示");
      assert.equal(await page.locator("button[aria-label='登出'] svg").count(), 1, "管理者應顯示統一登出圖示");
      assert.equal(await page.locator(".hero").count(), 0, "管理者首頁不應再顯示大型裝飾性橫幅");
      await page.screenshot({ path: `${process.env.TEMP}/smart-hr-admin-task-home.png`, fullPage: true });
      await page.setViewportSize({ width: 390, height: 844 });
      await page.waitForTimeout(200);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      assert.ok(overflow <= 1, `管理者手機首頁不應水平溢位，目前 ${overflow}px`);
      await page.screenshot({ path: `${process.env.TEMP}/smart-hr-admin-task-home-mobile.png`, fullPage: true });
    }
    await page.evaluate(() => logout());
    await page.waitForURL((url) => url.pathname === "/index.html" || url.pathname === "/");
    await page.waitForLoadState("domcontentloaded");
    await page.waitForTimeout(100);
    assert.equal(await page.evaluate(() => localStorage.getItem("hr_token")), null, `${role} 登出後應清除 token`);
    await page.getByRole("heading", { name: "登入系統" }).waitFor();
    await context.close();
  }

  console.log(JSON.stringify({ passed: true, checks: ["首頁登入", "移除角色選擇", "員工自動導向", "主管自動導向", "管理者自動導向", "任務優先首頁", "企業 SVG 圖示", "手機無溢位"] }, null, 2));
  await browser.close();
  await api.dispose();
})().catch((error) => { console.error(error); process.exitCode = 1; });
