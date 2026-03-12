/**
 * useViewer — React hook for ViewerEngine lifecycle.
 *
 * Manages engine initialization, cleanup, and provides
 * a stable reference to the engine instance.
 *
 * Handles React StrictMode double-mount gracefully:
 * - First mount creates engine, starts init
 * - StrictMode cleanup disposes engine (sets disposed flag)
 * - Engine init detects disposed flag and bails out
 * - Second mount creates a fresh engine that initializes normally
 */

import { useEffect, useRef, useState, useCallback } from "react";

import { ViewerEngine } from "./ViewerEngine";
import { useStore } from "../store";

interface UseViewerResult {
  /** The engine instance (null until initialized) */
  engine: ViewerEngine | null;
  /** Whether the engine is ready for use */
  isReady: boolean;
  /** Initialization error, if any */
  error: string | null;
  /** Status message from the engine */
  statusMessage: string | null;
}

/**
 * Hook that creates and manages a ViewerEngine instance.
 *
 * @param containerRef - Ref to the HTML element where the 3D canvas should mount
 */
export function useViewer(
  containerRef: React.RefObject<HTMLDivElement | null>
): UseViewerResult {
  const engineRef = useRef<ViewerEngine | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const setViewerReady = useStore((s) => s.setViewerReady);
  const setStoreStatus = useStore((s) => s.setStatusMessage);

  const handleProgress = useCallback(
    (message: string) => {
      setStatusMessage(message);
      setStoreStatus(message);
    },
    [setStoreStatus]
  );

  const handleError = useCallback((message: string) => {
    setError(message);
  }, []);

  const selectElement = useStore((s) => s.selectElement);
  const setHoveredElement = useStore((s) => s.setHoveredElement);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Track whether this effect instance has been cleaned up
    let cancelled = false;

    const engine = new ViewerEngine(container, {
      onProgress: handleProgress,
      onError: handleError,
      onElementSelected: selectElement,
      onElementHovered: setHoveredElement,
    });

    engineRef.current = engine;

    engine
      .init()
      .then(() => {
        // Ignore if this effect was already cleaned up (StrictMode)
        if (cancelled || engine.isDisposed) return;
        setIsReady(true);
        setViewerReady(true);
      })
      .catch((err: Error) => {
        // Ignore errors from a disposed engine (StrictMode)
        if (cancelled || engine.isDisposed) return;
        setError(err.message);
        setViewerReady(false);
      });

    return () => {
      cancelled = true;
      engine.dispose();
      engineRef.current = null;
      setIsReady(false);
      setViewerReady(false);
      setError(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    engine: engineRef.current,
    isReady,
    error,
    statusMessage,
  };
}
