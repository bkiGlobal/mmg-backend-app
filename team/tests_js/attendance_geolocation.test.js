"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

require("../static/admin/js/attendance_geolocation.js");

const { getCurrentLocation } = globalThis.MMGAttendanceGeolocation;

function fakeNavigator(responses, calls) {
  return {
    geolocation: {
      getCurrentPosition(success, failure, options) {
        calls.push(options);
        const response = responses.shift();
        if (response.position) {
          success(response.position);
        } else {
          failure(response.error);
        }
      },
    },
  };
}

test("falls back to laptop-compatible location after precise lookup fails", async () => {
  const calls = [];
  const expectedPosition = {
    coords: { latitude: -8.65, longitude: 115.21, accuracy: 80 },
    timestamp: Date.now(),
  };
  const navigator = fakeNavigator(
    [
      { error: { code: 2 } },
      { position: expectedPosition },
    ],
    calls
  );

  const position = await getCurrentLocation({
    navigator,
    isSecureContext: true,
  });

  assert.equal(position, expectedPosition);
  assert.equal(calls.length, 2);
  assert.equal(calls[0].enableHighAccuracy, true);
  assert.equal(calls[1].enableHighAccuracy, false);
  assert.equal(calls[1].maximumAge, 60000);
});

test("does not retry after location permission is denied", async () => {
  const calls = [];
  const navigator = fakeNavigator(
    [{ error: { code: 1 } }, { position: {} }],
    calls
  );

  await assert.rejects(
    getCurrentLocation({ navigator, isSecureContext: true }),
    /Izin lokasi ditolak/
  );
  assert.equal(calls.length, 1);
});

test("explains operating-system location failures on laptops", async () => {
  const calls = [];
  const navigator = fakeNavigator(
    [
      { error: { code: 2 } },
      { error: { code: 2 } },
    ],
    calls
  );

  await assert.rejects(
    getCurrentLocation({ navigator, isSecureContext: true }),
    /Location Services pada Windows\/macOS/
  );
  assert.equal(calls.length, 2);
});

test("rejects an insecure page before asking the browser for location", async () => {
  const calls = [];
  const navigator = fakeNavigator([{ position: {} }], calls);

  await assert.rejects(
    getCurrentLocation({ navigator, isSecureContext: false }),
    /HTTPS yang aman/
  );
  assert.equal(calls.length, 0);
});
