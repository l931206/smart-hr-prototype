const assert = require("node:assert/strict");
const { chromium, request } = require("playwright");

const frontendUrl = process.env.HR_FRONTEND_URL || "http://127.0.0.1:5500";
const apiUrl = process.env.HR_API_URL || "http://127.0.0.1:8000";

(async () => {
  const api = await request.newContext();
  const loginResponse = await api.post(`${apiUrl}/api/mock-central/login/`, {
    data: { external_user_id: "central-employee-001" },
  });
  assert.equal(loginResponse.status(), 200, "示範中控登入應成功");
  const login = await loginResponse.json();

  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await context.addInitScript(({ token, user }) => {
    localStorage.setItem("hr_token", token);
    localStorage.setItem("hr_token_scheme", "Bearer");
    localStorage.setItem("hr_user", JSON.stringify(user));
  }, { token: login.access_token, user: login.user });

  const page = await context.newPage();
  const browserErrors = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  await page.goto(`${frontendUrl}/employee/leave-assistant.html`, { waitUntil: "networkidle" });
  await page.getByText(/你好，員工示範帳號/).waitFor();

  await page.locator("#assistantInput").fill("我要請假");
  await page.locator("#assistantForm button[type=submit]").click();
  await page.getByText(/還需要提供/).waitFor();

  await page.locator("#assistantInput").fill("我要請 9 月 3 日公假，原因是參加教育訓練");
  await page.locator("#assistantForm button[type=submit]").click();
  const summary = page.locator(".summary-card").last();
  await summary.waitFor();
  assert.match(await summary.innerText(), /公假/);
  assert.match(await summary.innerText(), /2026-09-03 至 2026-09-03/);
  assert.match(await summary.innerText(), /參加教育訓練/);
  assert.equal(await page.locator(".confirm-draft").count(), 1, "預覽後應顯示確認送出按鈕");
  assert.equal(browserErrors.length, 0, `頁面不應出現 JavaScript 錯誤：${browserErrors.join("；")}`);

  const desktopShot = `${process.env.TEMP}/smart-hr-leave-assistant-desktop.png`;
  await page.screenshot({ path: desktopShot, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(200);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const overflowElements = overflow > 1 ? await page.evaluate(() => [...document.querySelectorAll("body *")]
    .filter((element) => element.getBoundingClientRect().right > window.innerWidth + 1)
    .slice(0, 8)
    .map((element) => `${element.tagName.toLowerCase()}.${element.className}`)) : [];
  assert.ok(overflow <= 1, `手機版不應產生水平捲動，目前超出 ${overflow}px：${overflowElements.join("、")}`);
  const mobileShot = `${process.env.TEMP}/smart-hr-leave-assistant-mobile.png`;
  await page.screenshot({ path: mobileShot, fullPage: true });

  console.log(JSON.stringify({
    passed: true,
    checks: ["登入身分", "缺漏追問", "請假預覽", "確認按鈕", "手機無水平溢位", "無 JavaScript 錯誤"],
    screenshots: [desktopShot, mobileShot],
  }, null, 2));
  await browser.close();
  await api.dispose();
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
