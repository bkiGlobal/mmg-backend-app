# Deploy MMG dengan Docker

Paket deploy terdiri dari:

- `Dockerfile`: image produksi Django + Gunicorn, GeoDjango, dan WhiteNoise.
- `docker-compose.yml`: PostgreSQL/PostGIS, web, dan scheduler.
- `deploy/entrypoint.sh`: menunggu database lalu menjalankan migrasi.
- `deploy/scheduler.sh`: memproses antrean export dan otomasi harian.

## 1. Siapkan environment

Jika server belum mempunyai `.env`:

```bash
cp deploy/.env.docker.example .env
```

Jika `.env` dari instalasi lama sudah ada, jangan menimpanya. Pertahankan nilai
`ENCRYPTED_FILEFIELD_KEY` dan `ENCRYPTED_FILEFIELD_SALT` yang lama, lalu gabungkan
variabel Docker dari file contoh. Mengganti kedua nilai tersebut membuat file
terenkripsi yang sudah tersimpan tidak dapat dibuka kembali.

Hal yang wajib diperiksa sebelum start:

- isi `SECRET_KEY`, password database, dan dua kunci encrypted file dengan nilai
  rahasia yang kuat;
- gunakan host `db` pada `DATABASE_URL`, bukan `localhost` atau `127.0.0.1`;
- URL-encode password bila password di dalam `DATABASE_URL` mengandung karakter
  khusus seperti `@`, `:`, `/`, `#`, atau `%`;
- set `DEBUG=False` dan isi domain pada `ALLOWED_HOSTS`,
  `CSRF_TRUSTED_ORIGINS`, serta `CORS_ALLOWED_ORIGINS`;
- saat baru menguji melalui HTTP/IP tanpa TLS, set `SECURE_SSL_REDIRECT=False`,
  `SESSION_COOKIE_SECURE=False`, dan `CSRF_COOKIE_SECURE=False`.

File `.env` tidak dimasukkan ke image oleh `.dockerignore` dan tidak boleh
di-commit.

## 2. Validasi dan jalankan

Jalankan dari direktori yang berisi `docker-compose.yml`:

```bash
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f web scheduler
```

Service `web` otomatis menunggu PostGIS siap dan menjalankan migrasi sebelum
Gunicorn start. Database dan upload disimpan pada named volume
`postgres-data` dan `media-data`, sehingga tidak hilang saat container diganti.
Gambar profil bawaan akan disalin ke volume media baru tanpa menimpa file yang
sudah ada.

Untuk membuat admin pertama:

```bash
docker compose exec web python manage.py createsuperuser
```

Untuk rilis berikutnya:

```bash
git pull
docker compose up -d --build
docker compose ps
```

## 3. Domain, HTTPS, dan media

Gunicorn dipublikasikan pada `WEB_PORT` (default `8000`). Tempatkan reverse
proxy seperti Nginx, Caddy, atau Traefik di depannya untuk domain dan HTTPS.
Proxy harus meneruskan header berikut:

```text
Host: host asli request
X-Forwarded-Proto: skema asli request (https)
X-Forwarded-For: alamat IP klien
```

Aktifkan `USE_X_FORWARDED_PROTO=True` hanya jika aplikasi tidak dapat diakses
langsung dari internet dan proxy tepercaya selalu menimpa
`X-Forwarded-Proto`.

WhiteNoise melayani `/static/`. Upload biasa berada pada volume `media-data`
dan URL `/media/` dilayani Django hanya untuk user admin/staff yang sudah
login. Jangan konfigurasi reverse proxy untuk melayani `/media/` langsung,
karena itu akan melewati pemeriksaan login. Endpoint encrypted media tetap
dilayani Django dan menerapkan otorisasi pemilik file.

Untuk bind mount Dokploy, buat direktori host sebelum deploy dan pastikan
owner-nya sama dengan user `mmg` di container. Image saat ini menggunakan UID
dan GID `999`; konfirmasikan pada container yang aktif dengan `id mmg`, lalu
terapkan nilai yang ditampilkan:

```bash
install -d -m 0750 -o 999 -g 999 /var/lib/dokploy/media_mmg
chown -R 999:999 /var/lib/dokploy/media_mmg
find /var/lib/dokploy/media_mmg -type d -exec chmod 0750 {} +
find /var/lib/dokploy/media_mmg -type f -exec chmod 0640 {} +
```

Di Dokploy, gunakan host path `/var/lib/dokploy/media_mmg` dan mount path
`/app/media`, lalu lakukan redeploy setiap kali konfigurasi mount berubah.
Entrypoint akan mencetak peringatan bila menemukan direktori media yang tidak
dapat ditulis oleh aplikasi.

## 4. Operasional

Perintah pemeriksaan yang berguna:

```bash
docker compose exec web python manage.py check --deploy
docker compose exec web python manage.py showmigrations
docker compose logs --tail=200 web scheduler db
```

Backup volume database dan media sebelum upgrade besar atau perubahan schema.
Menjalankan `docker compose down` tidak menghapus volume, tetapi
`docker compose down -v` menghapus database dan media secara permanen.

## Penjadwalan tanpa Docker

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
