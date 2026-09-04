#!/usr/bin/env bash
#
# Pengganti system cron untuk lingkungan kontainer.
#
# `deploy/crontab.example` tetap menjadi acuan untuk instalasi satu server
# tanpa Docker. Di dalam kontainer, loop ini lebih dipilih karena mewarisi
# environment layanan apa adanya dan menulis log ke stdout sehingga terbaca
# lewat `docker compose logs`.
#
# Jadwal mengikuti dokumen deploy:
#   - process_export_jobs  : setiap 5 menit
#   - run_automations      : sekali sehari pukul 01:00 waktu kontainer
#
# Fungsi di core/crons.py sudah memakai file lock, sehingga eksekusi yang
# kebetulan bertumpuk tidak akan menjalankan pekerjaan yang sama dua kali.

set -uo pipefail

EXPORT_INTERVAL_SECONDS="${EXPORT_INTERVAL_SECONDS:-300}"
EXPORT_LIMIT="${EXPORT_LIMIT:-10}"
DAILY_HOUR="${DAILY_HOUR:-01}"
TICK_SECONDS="${TICK_SECONDS:-30}"

log() {
    printf '[scheduler] %s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

log "mulai. export tiap ${EXPORT_INTERVAL_SECONDS}s, otomasi harian pukul ${DAILY_HOUR}:00."

last_daily_run=""
next_export_at=0

while true; do
    now_epoch="$(date +%s)"

    if [ "$now_epoch" -ge "$next_export_at" ]; then
        log "process_export_jobs --limit ${EXPORT_LIMIT}"
        python manage.py process_export_jobs --limit "$EXPORT_LIMIT" \
            || log "WARNING: process_export_jobs gagal, akan dicoba lagi."
        next_export_at=$((now_epoch + EXPORT_INTERVAL_SECONDS))
    fi

    current_hour="$(date +%H)"
    current_date="$(date +%F)"
    if [ "$current_hour" = "$DAILY_HOUR" ] && [ "$last_daily_run" != "$current_date" ]; then
        log "run_automations untuk ${current_date}"
        if python manage.py run_automations; then
            last_daily_run="$current_date"
        else
            log "WARNING: run_automations gagal, akan dicoba lagi pada tick berikutnya."
        fi
    fi

    sleep "$TICK_SECONDS"
done
