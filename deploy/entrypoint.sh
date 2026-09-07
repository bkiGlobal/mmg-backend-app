#!/usr/bin/env bash
#
# Entrypoint kontainer web.
#
# Menunggu database siap, menjalankan migrasi bila diizinkan, lalu menyerahkan
# proses ke perintah utama (gunicorn) melalui exec agar sinyal berhenti dari
# Docker diterima langsung oleh gunicorn.

set -euo pipefail

log() {
    printf '[entrypoint] %s\n' "$*"
}

# Pisahkan kegagalan import/settings dari kegagalan koneksi database. Tanpa
# pemeriksaan ini dependency yang hilang akan tampak keliru sebagai "database
# belum siap" sampai seluruh retry habis.
log "memvalidasi konfigurasi Django."
python -c "
from django.core.wsgi import get_wsgi_application
get_wsgi_application()
"

# ── Menunggu database ────────────────────────────────────────────────────────
# Pemeriksaan dilakukan lewat Django agar DATABASE_URL diurai dengan aturan
# yang sama seperti aplikasi, termasuk ketika memakai PostGIS.
wait_for_database() {
    local attempt=1
    local max_attempts="${DB_WAIT_ATTEMPTS:-30}"
    local delay="${DB_WAIT_DELAY:-2}"

    while [ "$attempt" -le "$max_attempts" ]; do
        if python -c "
import django
django.setup()
from django.db import connection
connection.ensure_connection()
" >/dev/null 2>&1; then
            log "database siap setelah percobaan ke-$attempt."
            return 0
        fi
        log "database belum siap (percobaan $attempt/$max_attempts), menunggu ${delay}s."
        attempt=$((attempt + 1))
        sleep "$delay"
    done

    log "ERROR: database tidak dapat dihubungi setelah $max_attempts percobaan."
    return 1
}

if [ "${WAIT_FOR_DATABASE:-1}" = "1" ]; then
    wait_for_database
fi

# ── Media bawaan ────────────────────────────────────────────────────────────
# Folder media tidak dipanggang ke image karena merupakan data runtime. Satu
# gambar profil bawaan disimpan terpisah dan disalin hanya ketika volume masih
# kosong, sehingga file milik pengguna tidak pernah ditimpa saat redeploy.
seed_default_media() {
    local source="$APP_HOME/default_photo/default_profile.png"
    local destination="$APP_HOME/media/default_photo/default_profile.png"

    if [ -f "$source" ] && [ ! -f "$destination" ]; then
        if ! mkdir -p "$(dirname "$destination")" \
            || ! cp "$source" "$destination"; then
            log "WARNING: gambar profil bawaan tidak dapat ditulis ke volume media."
            return 0
        fi
        log "gambar profil bawaan disalin ke volume media."
    fi
}

check_media_permissions() {
    local unwritable_directory

    unwritable_directory="$(
        find "$APP_HOME/media" -type d ! -writable -print -quit
    )"
    if [ -n "$unwritable_directory" ]; then
        log "WARNING: direktori media tidak dapat ditulis: $unwritable_directory"
        log "WARNING: perbaiki owner bind mount agar sesuai UID/GID user mmg."
    fi
}

check_media_permissions

if [ "${SEED_DEFAULT_MEDIA:-1}" = "1" ]; then
    seed_default_media
fi

# ── Migrasi ─────────────────────────────────────────────────────────────────
# Saat menjalankan lebih dari satu replika web, setel RUN_MIGRATIONS=0 dan
# jalankan migrasi sebagai langkah rilis tersendiri supaya tidak ada dua
# proses yang bermigrasi bersamaan.
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    log "menjalankan migrasi."
    python manage.py migrate --noinput
else
    log "migrasi dilewati (RUN_MIGRATIONS=0)."
fi

# collectstatic sudah dikerjakan saat build image. Setel COLLECTSTATIC_ON_BOOT=1
# hanya bila berkas statis dipasang dari volume eksternal.
if [ "${COLLECTSTATIC_ON_BOOT:-0}" = "1" ]; then
    log "menjalankan collectstatic."
    python manage.py collectstatic --noinput
fi

log "menjalankan: $*"
exec "$@"
