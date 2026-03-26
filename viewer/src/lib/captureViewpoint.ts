/**
 * Promise wrapper around the capture-viewpoint / capture-viewpoint-response
 * custom event pattern (handled by CenterPanel.tsx).
 *
 * Returns the screenshot data URL + camera state, or null on timeout/failure.
 */

import type { BcfCameraState } from "../types/bcf";

/** Timeout in ms before giving up on viewpoint capture */
const CAPTURE_TIMEOUT_MS = 5_000;

export interface CaptureViewpointResult {
  screenshot: string;
  camera: BcfCameraState;
}

/**
 * Request a viewpoint capture from the 3D engine for the given GlobalIds.
 * Dispatches a `capture-viewpoint` event and waits for the response.
 */
export function captureViewpoint(
  globalIds: string[],
): Promise<CaptureViewpointResult | null> {
  return new Promise((resolve) => {
    const requestId = crypto.randomUUID();

    const timer = setTimeout(() => {
      window.removeEventListener(
        "capture-viewpoint-response",
        handleResponse,
      );
      resolve(null);
    }, CAPTURE_TIMEOUT_MS);

    const handleResponse = (e: Event) => {
      const detail = (
        e as CustomEvent<{
          requestId: string;
          result: CaptureViewpointResult | null;
        }>
      ).detail;

      if (detail.requestId !== requestId) return;

      clearTimeout(timer);
      window.removeEventListener(
        "capture-viewpoint-response",
        handleResponse,
      );
      resolve(detail.result);
    };

    window.addEventListener("capture-viewpoint-response", handleResponse);

    window.dispatchEvent(
      new CustomEvent("capture-viewpoint", {
        detail: { globalIds, requestId },
      }),
    );
  });
}
