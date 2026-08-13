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
py manage.py runserver
```

The API is available at `http://127.0.0.1:8000/api/`.

## Deploy with Render

The repository includes `render.yaml` for a web service and PostgreSQL database.
Create a new Blueprint in Render, connect this repository, and select the `backend`
directory as the Blueprint root. Render will run migrations and collect static files
before starting Gunicorn.

- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `GET /api/auth/me/`
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
