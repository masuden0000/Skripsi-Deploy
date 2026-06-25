# ── Base image ────────────────────────────────────────────────────────────────
# Python 3.13 slim (Debian Bookworm) — sama dengan versi lokal.
# Slim dipilih agar image kecil; system font ditambah manual di bawah.
FROM python:3.13-slim

# ── System dependencies ────────────────────────────────────────────────────────
# PyMuPDF (MuPDF) membutuhkan font system untuk ekstraksi teks yang konsisten.
# Tanpa font ini, page-number detection bisa berbeda antara Windows (lokal) dan Linux (Railway).
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-liberation \
        fonts-dejavu-core \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ──────────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ────────────────────────────────────────────────────────
# Copy requirements dulu sebelum source code agar layer ini ter-cache
# saat hanya source code yang berubah.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application source ─────────────────────────────────────────────────────────
COPY backend/ ./backend/
COPY model/ ./model/

# Runtime data directory — dibuat pipeline saat proses berjalan
RUN mkdir -p data

# ── Runtime environment ────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

EXPOSE 8000

# Railway meng-inject env var PORT secara otomatis.
# Fallback ke 8000 untuk testing lokal dengan docker run.
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
