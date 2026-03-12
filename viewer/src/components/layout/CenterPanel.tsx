/**
 * CenterPanel — 3D viewer canvas.
 *
 * Mounts the ViewerEngine and handles model file loading
 * when files are added via the toolbar.
 */

import { useRef, useEffect } from "react";

import { useViewer } from "../../engine/useViewer";
import { useStore } from "../../store";

export function CenterPanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { engine, isReady, error, statusMessage } = useViewer(containerRef);

  // Store engine/isReady in refs so the event handler always has current values
  const engineRef = useRef(engine);
  const isReadyRef = useRef(isReady);
  engineRef.current = engine;
  isReadyRef.current = isReady;

  useEffect(() => {
    const handleModelFileAdded = async (e: Event) => {
      const detail = (e as CustomEvent<{ file: File }>).detail;
      const currentEngine = engineRef.current;
      if (!currentEngine || !isReadyRef.current || !detail.file) return;

      // Read current state directly from Zustand (avoids stale closure)
      const state = useStore.getState();
      const pendingModel = state.project?.models.find(
        (m) => m.fileName === detail.file.name && m.loadState === "pending"
      );
      if (!pendingModel) return;

      try {
        state.updateModelLoadState(pendingModel.id, "loading");
        const result = await currentEngine.loadModel(detail.file);
        useStore.getState().setEngineModelId(pendingModel.id, result.modelId);
        useStore.getState().updateModelLoadState(pendingModel.id, "loaded");
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Load failed";
        useStore.getState().updateModelLoadState(pendingModel.id, "error", msg);
      }
    };

    window.addEventListener("model-file-added", handleModelFileAdded);
    return () => {
      window.removeEventListener("model-file-added", handleModelFileAdded);
    };
  }, []);

  return (
    <div className="viewer-container">
      <div ref={containerRef} className="viewer-container__canvas" />

      {error && (
        <div
          className="viewer-container__status"
          style={{ color: "#ff6b6b" }}
        >
          {error}
        </div>
      )}

      {!error && statusMessage && (
        <div className="viewer-container__status">{statusMessage}</div>
      )}

      {!isReady && !error && (
        <div className="empty-state" style={{ color: "#ffffff" }}>
          <p className="empty-state__text">3D Viewer laden...</p>
        </div>
      )}
    </div>
  );
}
