# Imagen base con Python
FROM python:3.11-slim

# Instalar dependencias del sistema necesarias para compilar y para PostgreSQL
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar requirements.txt primero (esto ayuda a usar cache de Docker)
COPY requirements.txt /app/

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && pip install -r requirements.txt


# EntryPoint
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Asegúrate que settings apunten bien
ENV DJANGO_SETTINGS_MODULE=myproject.settings

ENTRYPOINT ["/start.sh"]


# Copiar el resto del proyecto dentro del contenedor
COPY . /app/

# Recoger archivos estáticos (puede ejecutarse también en runtime si prefieres)
#RUN python3 manage.py collectstatic --noinput

# Comando de inicio: Gunicorn usando socket Unix
#CMD ["gunicorn", "--bind", "unix:/app/myproject.sock", "myproject.wsgi:application"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "myproject.wsgi:application"]
