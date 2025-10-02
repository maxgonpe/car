#!/usr/bin/env bash
set -euo pipefail

echo "[start] DB: host=${DB_HOST:-?} port=${DB_PORT:-?} name=${DB_NAME:-?} user=${DB_USER:-?}"
echo "[start] DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-myproject.settings}"

# 1) Esperar Postgres (usa psycopg2-binary dentro del contenedor)
echo "[start] Waiting for Postgres..."
until python - <<'PY'
import os, sys
import psycopg2
host=os.getenv("DB_HOST","localhost")
port=int(os.getenv("DB_PORT","5432"))
user=os.getenv("DB_USER","postgres")
pwd=os.getenv("DB_PASSWORD","")
name=os.getenv("DB_NAME","postgres")
try:
    psycopg2.connect(host=host, port=port, user=user, password=pwd, dbname=name).close()
except Exception:
    sys.exit(1)
PY
do
  sleep 2
done

# 2) Mostrar a qué DB apunta Django
echo "[start] Checking Django DB settings..."
python - <<'PY'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE","myproject.settings")
django.setup()
from django.conf import settings
print("[start] DATABASES['default'] =", settings.DATABASES['default'])
PY

# 3) Migraciones contra esa BD (models.py + migrations)
echo "[start] Running migrations..."
python manage.py migrate --noinput

# 4) Crear superusuario del cliente (si se pasaron variables)
if [ -n "${CLIENT_ADMIN_USERNAME:-}" ] && [ -n "${CLIENT_ADMIN_EMAIL:-}" ] && [ -n "${CLIENT_ADMIN_PASSWORD:-}" ]; then
  echo "[start] Ensuring client admin user exists..."
  python - <<'PY'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE","myproject.settings")
django.setup()
from django.contrib.auth import get_user_model
u=os.environ["CLIENT_ADMIN_USERNAME"]
e=os.environ["CLIENT_ADMIN_EMAIL"]
p=os.environ["CLIENT_ADMIN_PASSWORD"]
User=get_user_model()
if not User.objects.filter(username=u).exists():
    User.objects.create_superuser(u, e, p)
    print("[start] Created superuser", u)
else:
    print("[start] Superuser", u, "already exists")
PY
else
  echo "[start] Skipping client admin creation (vars not set)"
fi

# 5) Collectstatic (opcional)
echo "[start] collectstatic (optional)"
python manage.py collectstatic --noinput || true

# 6) Lanza gunicorn
echo "[start] Launching gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 myproject.wsgi:application
