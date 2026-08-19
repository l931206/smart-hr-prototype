# Smart HR Backend

Django + Django REST Framework backend for the Smart HR platform.

## Local setup

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py manage.py migrate
py manage.py createsuperuser
uvicorn config.asgi:application --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000/api/`.

## Deploy with Render

The repository includes `render.yaml` for a web service and PostgreSQL database.
Create a new Blueprint in Render, connect this repository, and select the `backend`
directory as the Blueprint root. Render will run migrations and collect static files
before starting the ASGI application with Uvicorn. The same Render service hosts
the Django REST API and the remote MCP endpoint.

Before deployment, configure the three `DEMO_*_PASSWORD` values in Render's
Environment page. They are declared with `sync: false` in `render.yaml` so secrets
are never committed to Git. Production data is stored in the PostgreSQL service
referenced by `DATABASE_URL`.

- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `GET /api/auth/me/`
- `POST /api/leave-assistant/preview/`
- `POST /api/leave-assistant/submit/`
- `/api/departments/`
- `/api/employees/`

## API 文件與中控整合

- Swagger UI: `/api/docs/`
- OpenAPI schema: `/api/schema/`
- 系統角色與權限清單: `/api/integration/manifest/`
- 目前登入者身分與權限: `/api/integration/me/`

預設使用 `AUTH_MODE=local`，沿用 DRF Token。中控規格確定後可改成
`AUTH_MODE=hybrid`（兩種 Token 並行測試）或 `AUTH_MODE=central`（只接受
中控 Bearer Token）。中控驗證 API 的網址填入 `CENTRAL_TOKEN_VERIFY_URL`。
中控回應必須至少包含 `active: true`，以及 `external_user_id`、`user_id`
或 `sub` 其中一個穩定識別碼。該識別碼須先綁定到 HR User 的
`external_user_id`；系統不會自動建立員工資料。

## 模擬中控展示流程

展示環境可設定 `AUTH_MODE=hybrid`、`ENABLE_MOCK_CENTRAL=1`，再開啟前端
`central-login.html`。系統只允許三個示範帳號取得模擬中控 Token，Token
由 Django 簽章且預設 15 分鐘過期。此功能用來在正式中控尚未提供規格前
驗證完整流程；正式上線時必須設定 `ENABLE_MOCK_CENTRAL=0`，並填入真正的
`CENTRAL_TOKEN_VERIFY_URL`。

## MCP 中控／AI 串接

- Streamable HTTP endpoint: `/mcp`
- Authorization: `Authorization: Bearer <central-token>`
- Integration guide: `docs/MCP_INTEGRATION.md`
- Local end-to-end check: `python scripts/test_mcp_flow.py`

MCP 與 REST API 使用同一組中控 Token 驗證及 Django 請假規則。AI 必須先呼叫
`preview_leave_request` 取得短效 `draft_id`，向使用者顯示明確日期、時段、
天數與剩餘額度，取得確認後才能呼叫 `submit_leave_request`。同一個草稿只能
成功送出一次，預設 10 分鐘後失效。
