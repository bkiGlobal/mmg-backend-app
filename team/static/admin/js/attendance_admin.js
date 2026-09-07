/* app_name/static/js/attendance_control.js */

(function ($) {
  $(document).ready(function () {
    // Mendapatkan status superuser dari hidden field
    const isNonSuperuser = $("#id_request_user_is_superuser").val() === "False";

    if (!isNonSuperuser) {
      return; // Logika ini hanya untuk non-superuser
    }

    const $photoCheckIn = $("#id_photo_check_in");
    const $photoCheckOut = $("#id_photo_check_out");
    const $locCheckIn = $("#id_check_in_location"); // Hidden PointField input
    const $locCheckOut = $("#id_check_out_location"); // Hidden PointField input

    // Fungsi Geolocation API
    function getGeolocation(targetField) {
      // Poin 2: Mengambil Lokasi Saat Ini
      if (navigator.geolocation) {
        // Tampilkan pesan loading/izin
        alert("Meminta izin lokasi...");

        navigator.geolocation.getCurrentPosition(
          // Callback Sukses
          (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;

            // Penting: Format WKT GeoDjango PointField adalah POINT(longitude latitude) [1]
            const wktPoint = `POINT(${lng} ${lat})`;

            // Mengisi field lokasi (yang disetel read-only oleh Python)
            targetField.val(wktPoint);
            // Trigger event 'change' pada field tersembunyi
            targetField.trigger("change");
            alert(`Lokasi Check-in/Check-out berhasil ditangkap: ${wktPoint}`);
          },
          // Callback Gagal (Penolakan Izin atau Error Jaringan/Browser)
          (error) => {
            console.error("Geolocation Error: ", error);
            let errorMessage;
            if (error.code === error.PERMISSION_DENIED) {
              errorMessage =
                "Akses lokasi ditolak oleh pengguna. Harap berikan izin di pengaturan browser Anda.";
            } else if (error.code === error.POSITION_UNAVAILABLE) {
              errorMessage =
                "Informasi lokasi tidak tersedia (Error Jaringan).";
            } else if (error.code === error.TIMEOUT) {
              errorMessage = "Permintaan waktu tunggu lokasi habis.";
            } else {
              // Ini mencakup error Secure Context jika menggunakan HTTP di luar localhost
              errorMessage =
                "Gagal mengambil lokasi. Pastikan menggunakan HTTPS atau localhost, dan layanan lokasi aktif.";
            }
            alert(errorMessage);
          },
          // Options: Meminta akurasi tinggi dan batas waktu
          { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
        );
      } else {
        alert("Geolocation tidak didukung oleh browser ini.");
      }
    }

    // Cek-In Trigger (Mengambil Lokasi Check-in)
    $photoCheckIn.on("change", function () {
      if (this.files.length > 0) {
        // Trigger: Foto dipilih -> Ambil Lokasi Check-in
        getGeolocation($locCheckIn);

        // Poin 3: Aktifkan field Check-out (Dynamic Control)
        $photoCheckOut.prop("disabled", false);
        $locCheckOut.prop("disabled", false);
      } else {
        //... (Logika disable jika file dihapus)
      }
    });

    // Cek-Out Trigger (Mengambil Lokasi Check-out)
    $photoCheckOut.on("change", function () {
      if (this.files.length > 0) {
        // Pengecekan klien-side memastikan check-in sudah ada
        // Cek apakah ada file check-in yang baru diupload ATAU sudah ada lokasi check-in
        const hasCheckInPhoto =
          $photoCheckIn.get(0).files.length > 0 ||
          $locCheckIn.val().length > 10;

        if (hasCheckInPhoto) {
          // Trigger: Foto dipilih -> Ambil Lokasi Check-out
          getGeolocation($locCheckOut);
        } else {
          alert("Harap lengkapi Check-in (foto dan lokasi) terlebih dahulu.");
          $(this).val(""); // Hapus file yang dipilih jika validasi gagal
        }
      }
    });
  });
})(django.jQuery);
