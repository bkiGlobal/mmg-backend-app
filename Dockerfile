# syntax=docker/dockerfile:1

# Image produksi untuk backend MMG.
#
# Proyek ini memakai GeoDjango, sehingga image wajib menyediakan GDAL, GEOS,
# dan PROJ. Path pustaka sengaja tidak dipatok lewat environment: pada Linux
# GeoDjango menemukannya sendiri berdasarkan nama, sehingga image yang sama
# tetap jalan di amd64 maupun arm64.

############################  Tahap 1 — wheel  ###############################
# Dependensi dibangun terpisah agar toolchain kompilasi tidak ikut terbawa ke
# image akhir.
FROM python:3.10-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        libgdal-dev \
        libgeos-dev \
        libpq-dev \
        libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt ./
RUN pip wheel --wheel-dir /wheels -r requirements.txt

############################  Tahap 2 — runtime  #############################
FROM python:3.10-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=mmg_backend_app.settings \
    TZ=Asia/Makassar \
    APP_HOME=/app

# UID/GID dibuat stabil karena deployment Dokploy memakai bind mount host.
# Dengan nilai tetap, ownership volume tidak berubah diam-diam saat image
# dasar atau daftar paket diperbarui.
ARG APP_UID=999
ARG APP_GID=999

# gdal-bin menarik libgdal beserta PROJ sesuai versi Debian yang dipakai,
# sehingga nama paket berversi tidak perlu dipatok di sini. libmagic1
# dibutuhkan python-magic, dan libpq5 dibutuhkan psycopg varian murni Python.
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        gdal-bin \
        libgeos-c1v5 \
        libmagic1 \
        libpq5 \
        postgresql-client \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels

# Berjalan sebagai user biasa; root tidak diperlukan setelah paket terpasang.
RUN groupadd --system --gid "$APP_GID" mmg \
    && useradd --system --uid "$APP_UID" --gid mmg --home-dir "$APP_HOME" \
       --shell /usr/sbin/nologin mmg

WORKDIR $APP_HOME
COPY --chown=mmg:mmg . .

RUN chmod +x deploy/entrypoint.sh deploy/scheduler.sh \
    && mkdir -p "$APP_HOME/media" "$APP_HOME/static" \
    && chown -R mmg:mmg "$APP_HOME/media" "$APP_HOME/static"

# collectstatic dijalankan saat build supaya berkas ber-hash dan versi
# terkompresinya ikut menjadi bagian image; kontainer tidak perlu menulis
# apa pun saat start. Nilai di bawah hanya memenuhi syarat impor settings dan
# tidak ikut tersimpan pada image karena diberikan per-perintah. Jalankan
# sebagai user runtime agar seluruh hasilnya pasti dapat dibaca WhiteNoise.
USER mmg

RUN SECRET_KEY=build-time-only \
    ENCRYPTED_FILEFIELD_KEY=build-time-only \
    ENCRYPTED_FILEFIELD_SALT=build-time-only \
    DEBUG=False \
    python manage.py collectstatic --noinput

EXPOSE 8000

# HTTPConnection dipakai agar redirect tidak diikuti: dengan
# SECURE_SSL_REDIRECT aktif, permintaan HTTP internal dijawab 301 ke https dan
# kontainer akan salah dinilai tidak sehat bila redirect tersebut ditelusuri.
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import http.client, sys; c = http.client.HTTPConnection('127.0.0.1', 8000, timeout=4); c.request('GET', '/admin/login/'); sys.exit(0 if c.getresponse().status < 500 else 1)"

ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["gunicorn", "mmg_backend_app.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
