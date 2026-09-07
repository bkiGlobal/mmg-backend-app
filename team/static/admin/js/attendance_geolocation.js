(function (global) {
  "use strict";

  const PERMISSION_DENIED = 1;
  const POSITION_UNAVAILABLE = 2;
  const TIMEOUT = 3;
  const LOCATION_ATTEMPTS = [
    {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 15000,
    },
    {
      enableHighAccuracy: false,
      timeout: 20000,
      maximumAge: 60000,
    },
  ];

  function requestPosition(geolocation, options) {
    return new Promise((resolve, reject) => {
      geolocation.getCurrentPosition(resolve, reject, options);
    });
  }

  function locationError(error) {
    if (error && error.code === PERMISSION_DENIED) {
      return new Error(
        "Izin lokasi ditolak oleh browser atau sistem operasi. " +
          "Aktifkan izin lokasi untuk browser lalu coba kembali."
      );
    }
    if (error && error.code === POSITION_UNAVAILABLE) {
      return new Error(
        "Browser belum dapat menentukan lokasi. Aktifkan Location Services " +
          "pada Windows/macOS, nyalakan Wi-Fi, lalu tekan Ambil foto lagi."
      );
    }
    if (error && error.code === TIMEOUT) {
      return new Error(
        "Lokasi belum diperoleh dalam batas waktu. Pastikan Location Services " +
          "dan Wi-Fi aktif, lalu tekan Ambil foto lagi."
      );
    }
    return new Error(
      "Lokasi gagal diambil. Muat ulang halaman dan pastikan browser memakai HTTPS."
    );
  }

  async function getCurrentLocation(options) {
    const config = options || {};
    const navigatorObject = config.navigator || global.navigator;
    const secureContext =
      config.isSecureContext === undefined
        ? global.isSecureContext
        : config.isSecureContext;

    if (secureContext === false) {
      throw new Error(
        "Lokasi browser hanya tersedia melalui koneksi HTTPS yang aman."
      );
    }
    if (!navigatorObject || !navigatorObject.geolocation) {
      throw new Error("Geolocation tidak didukung oleh browser ini.");
    }

    let lastError = null;
    for (const attempt of LOCATION_ATTEMPTS) {
      try {
        return await requestPosition(
          navigatorObject.geolocation,
          attempt
        );
      } catch (error) {
        lastError = error;
        if (error && error.code === PERMISSION_DENIED) {
          break;
        }
      }
    }
    throw locationError(lastError);
  }

  global.MMGAttendanceGeolocation = Object.freeze({
    getCurrentLocation,
  });
})(typeof window === "undefined" ? globalThis : window);
