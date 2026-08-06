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
