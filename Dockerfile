FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py recommendations.py schema.sql ./
COPY templates ./templates
COPY static ./static

RUN useradd --system --uid 10001 --create-home appuser
USER appuser

EXPOSE 5000
CMD ["gunicorn", "--workers=2", "--threads=4", "--timeout=30", "--bind=0.0.0.0:5000", "app:create_app()"]
