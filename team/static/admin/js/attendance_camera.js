(function () {
  "use strict";

  const CAMERA_SELECTOR = '[data-mmg-camera-required="true"]';
  const MAX_IMAGE_WIDTH = 1280;
  const JPEG_QUALITY = 0.9;
  const MAX_REUSABLE_LOCATION_AGE = 60000;

  function createElement(tagName, className, text) {
    const element = document.createElement(tagName);
    if (className) {
      element.className = className;
    }
    if (text) {
      element.textContent = text;
    }
    return element;
  }

  function createButton(label, icon, variant) {
    const button = createElement(
      "button",
      `mmg-camera__button mmg-camera__button--${variant}`
    );
    button.type = "button";

    const iconElement = createElement(
      "span",
      "material-symbols-outlined",
      icon
    );
    button.append(iconElement, document.createTextNode(label));
    return button;
  }

  function initializeCamera(input) {
    if (input.dataset.mmgCameraInitialized === "true") {
      return;
    }
    input.dataset.mmgCameraInitialized = "true";

    const label = input.dataset.mmgCameraLabel || "Foto absensi";
    const locationInput = document.getElementById(
      input.dataset.mmgLocationInput || ""
    );
    const accuracyInput = document.getElementById(
      input.dataset.mmgAccuracyInput || ""
    );
    let facingMode = input.dataset.mmgCameraFacingMode || "user";
    let stream = null;
    let locationRequest = null;
    let latestPosition = null;

    const camera = createElement("section", "mmg-camera");
    camera.setAttribute("aria-label", label);

    const header = createElement("div", "mmg-camera__header");
    const headerIcon = createElement(
      "span",
      "material-symbols-outlined mmg-camera__header-icon",
      "photo_camera"
    );
    const heading = createElement("div");
    const title = createElement("div", "mmg-camera__title", label);
    const hint = createElement(
      "div",
      "mmg-camera__hint",
      "Foto dan lokasi GPS terkini akan diambil pada saat yang sama."
    );
    heading.append(title, hint);
    header.append(headerIcon, heading);

    const viewport = createElement("div", "mmg-camera__viewport");
    viewport.hidden = true;
    const video = createElement("video", "mmg-camera__video");
    video.autoplay = true;
    video.muted = true;
    video.playsInline = true;
    video.setAttribute("data-facing-mode", facingMode);
    const preview = createElement("img", "mmg-camera__preview");
    preview.alt = `Pratinjau ${label.toLowerCase()}`;
    preview.hidden = true;
    viewport.append(video, preview);

    const actions = createElement("div", "mmg-camera__actions");
    const openButton = createButton("Buka kamera", "photo_camera", "primary");
    const captureButton = createButton(
      "Ambil foto",
      "camera",
      "primary"
    );
    const switchButton = createButton(
      "Balik kamera",
      "cameraswitch",
      "secondary"
    );
    const retakeButton = createButton(
      "Ambil ulang",
      "refresh",
      "secondary"
    );
    const cancelButton = createButton("Tutup", "close", "secondary");
    captureButton.hidden = true;
    switchButton.hidden = true;
    retakeButton.hidden = true;
    cancelButton.hidden = true;
    actions.append(
      openButton,
      captureButton,
      switchButton,
      retakeButton,
      cancelButton
    );

    const status = createElement(
      "div",
      "mmg-camera__status",
      "Kamera belum dibuka."
    );
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");

    camera.append(header, viewport, actions, status);
    input.insertAdjacentElement("afterend", camera);

    function setStatus(message, type) {
      status.textContent = message;
      status.classList.remove(
        "mmg-camera__status--success",
        "mmg-camera__status--error"
      );
      if (type) {
        status.classList.add(`mmg-camera__status--${type}`);
      }
    }

    function stopCamera() {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
        stream = null;
      }
      video.srcObject = null;
    }

    function showReadyState() {
      viewport.hidden = false;
      video.hidden = false;
      preview.hidden = true;
      openButton.hidden = true;
      captureButton.hidden = false;
      switchButton.hidden = false;
      cancelButton.hidden = false;
      retakeButton.hidden = true;
    }

    function showIdleState() {
      stopCamera();
      viewport.hidden = true;
      video.hidden = false;
      preview.hidden = true;
      openButton.hidden = false;
      captureButton.hidden = true;
      switchButton.hidden = true;
      cancelButton.hidden = true;
      retakeButton.hidden = true;
    }

    function showCapturedState(previewUrl) {
      stopCamera();
      preview.src = previewUrl;
      viewport.hidden = false;
      video.hidden = true;
      preview.hidden = false;
      openButton.hidden = true;
      captureButton.hidden = true;
      switchButton.hidden = true;
      cancelButton.hidden = true;
      retakeButton.hidden = false;
    }

    async function startCamera() {
      if (
        !navigator.mediaDevices ||
        typeof navigator.mediaDevices.getUserMedia !== "function"
      ) {
        setStatus(
          "Kamera browser tidak tersedia. Gunakan HTTPS atau localhost dan browser terbaru.",
          "error"
        );
        return;
      }

      openButton.disabled = true;
      retakeButton.disabled = true;
      setStatus("Meminta izin dan membuka kamera...");

      try {
        stopCamera();
        stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            facingMode: { ideal: facingMode },
            width: { ideal: 1280 },
            height: { ideal: 960 },
          },
        });
        video.srcObject = stream;
        video.setAttribute("data-facing-mode", facingMode);
        await video.play();
        showReadyState();
        setStatus("Kamera aktif. Sedang menyiapkan lokasi...");
        prepareLocation()
          .then(() => {
            if (stream) {
              setStatus(
                "Kamera dan lokasi siap. Posisikan wajah lalu tekan Ambil foto."
              );
            }
          })
          .catch((error) => {
            if (stream) {
              setStatus(error.message, "error");
            }
          });
      } catch (error) {
        showIdleState();
        const permissionDenied =
          error && (
            error.name === "NotAllowedError" ||
            error.name === "PermissionDeniedError"
          );
        setStatus(
          permissionDenied
            ? "Izin kamera ditolak. Aktifkan izin kamera pada pengaturan browser."
            : "Kamera tidak dapat dibuka. Pastikan kamera tidak sedang dipakai aplikasi lain.",
          "error"
        );
      } finally {
        openButton.disabled = false;
        retakeButton.disabled = false;
      }
    }

    function hasReusableLocation() {
      return (
        latestPosition &&
        Number.isFinite(latestPosition.timestamp) &&
        Date.now() - latestPosition.timestamp <= MAX_REUSABLE_LOCATION_AGE
      );
    }

    function prepareLocation() {
      if (hasReusableLocation()) {
        return Promise.resolve(latestPosition);
      }
      if (locationRequest) {
        return locationRequest;
      }
      if (
        !window.MMGAttendanceGeolocation ||
        typeof window.MMGAttendanceGeolocation.getCurrentLocation !==
          "function"
      ) {
        return Promise.reject(
          new Error("Komponen lokasi gagal dimuat. Muat ulang halaman.")
        );
      }

      locationRequest = window.MMGAttendanceGeolocation
        .getCurrentLocation()
        .then((position) => {
          latestPosition = position;
          return position;
        })
        .finally(() => {
          locationRequest = null;
        });
      return locationRequest;
    }

    function canvasToBlob(canvas) {
      return new Promise((resolve, reject) => {
        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(blob);
            } else {
              reject(new Error("Foto gagal diproses."));
            }
          },
          "image/jpeg",
          JPEG_QUALITY
        );
      });
    }

    async function capturePhoto() {
      if (!stream || !video.videoWidth || !video.videoHeight) {
        setStatus("Kamera belum siap. Silakan coba kembali.", "error");
        return;
      }

      captureButton.disabled = true;
      setStatus("Mengambil foto dan lokasi GPS terkini...");

      const width = Math.min(video.videoWidth, MAX_IMAGE_WIDTH);
      const height = Math.round(
        video.videoHeight * (width / video.videoWidth)
      );
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");

      if (facingMode === "user") {
        context.translate(width, 0);
        context.scale(-1, 1);
      }
      context.drawImage(video, 0, 0, width, height);

      try {
        const [position, blob] = await Promise.all([
          prepareLocation(),
          canvasToBlob(canvas),
        ]);
        if (!locationInput) {
          throw new Error(
            "Field lokasi tidak tersedia. Muat ulang halaman."
          );
        }

        const longitude = position.coords.longitude;
        const latitude = position.coords.latitude;
        locationInput.value = `SRID=4326;POINT (${longitude} ${latitude})`;
        locationInput.dispatchEvent(
          new Event("change", { bubbles: true })
        );
        if (accuracyInput) {
          accuracyInput.value = position.coords.accuracy || "";
        }

        const dataTransfer = new DataTransfer();
        const filename = `attendance-${input.name}-${Date.now()}.jpg`;
        dataTransfer.items.add(
          new File([blob], filename, { type: "image/jpeg" })
        );
        input.files = dataTransfer.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
        showCapturedState(URL.createObjectURL(blob));
        setStatus(
          `Foto dan GPS siap disimpan (akurasi ±${Math.round(
            position.coords.accuracy
          )} m).`,
          "success"
        );
      } catch (error) {
        setStatus(
          error.message || "Foto dan lokasi gagal diambil.",
          "error"
        );
      } finally {
        captureButton.disabled = false;
      }
    }

    openButton.addEventListener("click", startCamera);
    retakeButton.addEventListener("click", () => {
      input.value = "";
      if (locationInput) {
        locationInput.value = "";
      }
      if (accuracyInput) {
        accuracyInput.value = "";
      }
      startCamera();
    });
    captureButton.addEventListener("click", capturePhoto);
    cancelButton.addEventListener("click", () => {
      showIdleState();
      setStatus("Kamera ditutup. Foto belum diambil.");
    });
    switchButton.addEventListener("click", async () => {
      facingMode = facingMode === "user" ? "environment" : "user";
      await startCamera();
    });

    const form = input.closest("form");
    if (form) {
      form.addEventListener("submit", (event) => {
        if (input.required && input.files.length === 0) {
          event.preventDefault();
          setStatus(
            "Ambil foto langsung dari kamera sebelum menyimpan absensi.",
            "error"
          );
          camera.scrollIntoView({ behavior: "smooth", block: "center" });
          openButton.focus();
        } else if (!locationInput || !locationInput.value) {
          event.preventDefault();
          setStatus(
            "Lokasi GPS terkini belum tersedia. Ambil ulang foto.",
            "error"
          );
          camera.scrollIntoView({ behavior: "smooth", block: "center" });
          retakeButton.focus();
        }
        stopCamera();
      });
    }

    window.addEventListener("beforeunload", stopCamera);
  }

  function initializeAllCameras(root) {
    root.querySelectorAll(CAMERA_SELECTOR).forEach(initializeCamera);
  }

  document.addEventListener("DOMContentLoaded", () => {
    initializeAllCameras(document);
  });

  document.addEventListener("formset:added", (event) => {
    initializeAllCameras(event.target);
  });
})();
