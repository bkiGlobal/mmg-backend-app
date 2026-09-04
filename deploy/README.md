# Penjadwalan MMG

Untuk instalasi satu server, gunakan system `crontab` agar otomasi tetap
berjalan terpisah dari proses web Django.

Fungsi terjadwal berada di `core/crons.py`. File tersebut menangani
logging, pembersihan koneksi database lama, dan file lock untuk mencegah
job yang sama berjalan bertumpuk. Management command menjadi antarmuka
antara system cron dan fungsi tersebut:

- `run_automations` menjalankan otomasi operasional harian.
- `process_export_jobs` memproses antrean export secara berkala.

1. Buka `deploy/crontab.example`.
2. Ganti `MMG_PROJECT_DIR` dan `MMG_PYTHON_BIN` dengan path absolut server.
3. Jalankan `crontab -e`, lalu tempel konfigurasi tersebut.
4. Pastikan zona waktu sistem server adalah `Asia/Makassar`.
5. Periksa log di `/tmp/mmg-daily-automation.log` dan
   `/tmp/mmg-export-jobs.log`.

Jangan menjalankan `run_automations` dari cron sekaligus scheduler lain,
agar pekerjaan yang sama tidak dipicu ganda.

## Pemeriksaan

Jalankan command secara manual sebelum memasang cron:

```bash
python manage.py run_automations
python manage.py process_export_jobs --limit 10
```

Setelah memasang jadwal, periksa entry aktif menggunakan:

```bash
crontab -l
```

Lokasi lock dapat diubah melalui environment variable `CRON_LOCK_DIR`.
Direktori tersebut harus dapat ditulis oleh user yang menjalankan cron.
