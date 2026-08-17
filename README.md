# Smart HR 智慧人資管理平台

這是一套可實際操作的前後端分離人資系統，不是純靜態原型。前端部署於 GitHub Pages，後端使用 Django REST Framework，正式資料儲存在 Render PostgreSQL。

## 線上環境

- 前端：https://l931206.github.io/smart-hr-prototype/
- API 健康檢查：https://smart-hr-api-8rxh.onrender.com/api/health/
- Swagger API 文件：https://smart-hr-api-8rxh.onrender.com/api/docs/
- OpenAPI Schema：https://smart-hr-api-8rxh.onrender.com/api/schema/

GitHub repository 的既有網址仍保留 `smart-hr-prototype` slug，以避免已分享的 Pages 與 API 整合連結失效；產品名稱與文件定位皆以「Smart HR 智慧人資管理平台」為準。

測試帳號的帳號名稱由 `DEMO_*_USERNAME` 設定，密碼屬於機密，只放在 Render Environment，不寫入 GitHub。需要展示帳號時，請向專案管理者取得。

## 系統架構

```text
瀏覽器（GitHub Pages HTML/CSS/JavaScript）
              │ HTTPS / JSON / Token 或 Bearer Token
              ▼
Render（Django REST API）
              │ Django ORM
              ▼
Render PostgreSQL（正式資料）
```

三種角色：

- `employee/`：員工申請請假、晚到通知、公告、通知與個人資料。
- `manager/`：主管審核、團隊、日曆、晚到通知與公告。
- `admin/`：員工、部門、帳號權限、假別、資料修改申請與稽核紀錄。

## 本機啟動

瀏覽器會阻擋 `file://` 頁面呼叫網路 API，因此不要直接雙擊 HTML。請在專案根目錄啟動 HTTP Server：

```powershell
python -m http.server 5500
```

再開啟 http://127.0.0.1:5500/ 。本機前端預設連接 `http://127.0.0.1:8000/api`，後端啟動方式如下：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py bootstrap_demo
python manage.py runserver
```

## 環境變數

| 名稱 | 用途 | 是否機密 |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django 簽章金鑰 | 是 |
| `DATABASE_URL` | PostgreSQL 連線字串 | 是 |
| `DEMO_EMPLOYEE_USERNAME` / `DEMO_EMPLOYEE_PASSWORD` | 員工展示帳號 | 帳號否／密碼是 |
| `DEMO_MANAGER_USERNAME` / `DEMO_MANAGER_PASSWORD` | 主管展示帳號 | 帳號否／密碼是 |
| `DEMO_ADMIN_USERNAME` / `DEMO_ADMIN_PASSWORD` | 管理者展示帳號 | 帳號否／密碼是 |
| `AUTH_MODE` | `local`、`central` 或 `hybrid` | 否 |
| `CENTRAL_TOKEN_VERIFY_URL` | 中控 Token 驗證端點 | 視環境而定 |
| `CENTRAL_API_KEY` | 呼叫中控服務的金鑰 | 是 |
| `ENABLE_MOCK_CENTRAL` | 是否啟用展示用中控登入 | 否 |
| `CORS_ALLOWED_ORIGINS` | 允許呼叫 API 的前端網址 | 否 |

`render.yaml` 只宣告變數名稱；密碼與金鑰必須在 Render Dashboard 設定，不得提交到版本庫。

## 測試

```powershell
cd backend
python manage.py test
```

## 主要目錄

- `assets/css/`：三份共用企業版與 RWD 樣式。
- `assets/js/`：API、權限與各功能資料同步。
- `backend/hr/`：資料模型、API、權限與測試。
- `backend/config/`：Django 與部署設定。
