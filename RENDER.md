# Deploy SmartChat on Render (free tier)

## What you need on Render

1. **Web Service** — runs the Django app (ASGI for WebSockets).
2. **PostgreSQL** (free instance) — Render sets `DATABASE_URL` automatically when you link the DB to the service.

## 1. Create PostgreSQL

- Dashboard → **New** → **PostgreSQL**.
- Note the **Internal Database URL** (or use the auto-injected `DATABASE_URL` when the DB is **linked** to your web service).

## 2. Create Web Service

- **New** → **Web Service** → connect your Git repo (or deploy from Dockerfile).
- **Runtime**: Python 3.12.
- **Build command**:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

- **Start command** (ASGI, required for chat WebSockets):

```bash
daphne -b 0.0.0.0 -p $PORT smartchat.asgi:application
```

- **Root directory**: repository root (where `manage.py` lives).

## 3. Environment variables (Web Service)

Set these in the service → **Environment**:

| Variable | Example / notes |
|----------|------------------|
| `DATABASE_URL` | Injected automatically if PostgreSQL is **linked** to the web service. |
| `DJANGO_SECRET_KEY` | Long random string (generate locally: `python -c "import secrets; print(secrets.token_urlsafe(50))"`). |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_ALLOWED_HOSTS` | `your-app.onrender.com` (comma-separated if multiple). |
| `CSRF_TRUSTED_ORIGINS` | `https://your-app.onrender.com` |
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_HOST_USER` | Your Gmail address |
| `EMAIL_APP_PASSWORD` | Gmail **App Password** (not your normal password) |
| `EMAIL_HOST_PORT` | `587` |
| `EMAIL_USE_TLS` | `1` |
| `DEFAULT_FROM_EMAIL` | Same as `EMAIL_HOST_USER` or `Your Name <you@gmail.com>` |

Optional:

- `PYTHON_VERSION` — `3.12.0` (or whatever Render supports for your stack).

## 4. First deploy: run migrations

After the first successful deploy, open **Shell** on the Web Service (or use a one-off job) and run:

```bash
python manage.py migrate
python manage.py createsuperuser
```

Use **email** + password for the superuser (custom user model).

## 5. Scheduled messages on free tier

The app does **not** run the in-process scheduler when `DEBUG=0`. On free Render you have no built-in cron.

**Options:**

- Manually run in Shell when testing: `python manage.py process_scheduled_messages`
- Use an external cron (e.g. cron-job.org) to `POST` a **secret** URL that runs that command (you would add a small guarded endpoint), or upgrade to a plan with **Cron Jobs**.

## 6. Limitations (free tier)

- **Ephemeral disk** — uploaded chat files can be lost on restart. For durable media, add S3/R2 later.
- **In-memory Channels layer** — OK for a single instance; if you scale to multiple instances, add **Redis** and `channels-redis`.

## Local vs Render database

- **Local:** leave `DATABASE_URL` unset; use MySQL variables (`DB_NAME`, `DB_USER`, etc.) in `.env`.
- **Render:** `DATABASE_URL` is set → Django uses **PostgreSQL** via `dj-database-url`.
