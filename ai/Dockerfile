# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.13-slim

# ── System dependencies ────────────────────────────────────────────────────────
# Font sistem dibutuhkan PyMuPDF/MuPDF agar ekstraksi teks konsisten di Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-liberation \
        fonts-dejavu-core \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ────────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application source ─────────────────────────────────────────────────────────
COPY backend/ ./backend/
COPY model/ ./model/

# Data dir untuk file PDF sementara per project
RUN mkdir -p model/data

# ── Runtime ───────────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

EXPOSE 8000

# Jalankan uvicorn dari /app agar "backend.main:app" bisa diimport sebagai package.
# backend/__init__.py membuat backend/ dikenali sebagai Python package.
# sys.path manipulation di main.py menambah /app/backend dan /app/model secara otomatis.
WORKDIR /app
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
