/**
 * CenterPanel — 3D viewer canvas.
 *
 * Mounts the ViewerEngine and handles:
 * - Model file loading when files are added via the toolbar
 * - Store→Engine bridge for highlight synchronization
 * - Zoom-to-element events from the validation panel
 */

import { useRef, useEffect } from "react";

import { useViewer } from "../../engine/useViewer";
import { useStore } from "../../store";
import type { HighlightGroup } from "../../store";

export function CenterPanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { engine, isReady, error, statusMessage } = useViewer(containerRef);

  // Store engine/isReady in refs so event handlers always have current values
  const engineRef = useRef(engine);
  const isReadyRef = useRef(isReady);
  engineRef.current = engine;
  isReadyRef.current = isReady;

  // Model file loading handler
  useEffect(() => {
    const handleModelFileAdded = async (e: Event) => {
      const detail = (e as CustomEvent<{ file: File }>).detail;
      const currentEngine = engineRef.current;
      if (!currentEngine || !isReadyRef.current || !detail.file) return;

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

  // Store→Engine bridge: sync highlightGroups to the 3D engine
  useEffect(() => {
    let prevGroups: HighlightGroup[] = [];

    const unsubscribe = useStore.subscribe((state) => {
      const groups = state.highlightGroups;
      if (groups === prevGroups) return;

      const currentEngine = engineRef.current;
      if (!currentEngine || !isReadyRef.current) {
        prevGroups = groups;
        return;
      }

      // Groups cleared → reset all highlights
      if (groups.length === 0 && prevGroups.length > 0) {
        prevGroups = groups;
        currentEngine.clearHighlights();
        return;
      }

      // Apply all highlight groups (clear first, then apply each)
      if (groups.length > 0) {
        prevGroups = groups;
        (async () => {
          await currentEngine.clearHighlights();
          for (const group of groups) {
            if (group.globalIds.length > 0) {
              await currentEngine.highlightByGlobalIds(
                group.globalIds,
                group.color
              );
            }
          }
        })();
        return;
      }

      prevGroups = groups;
    });

    return () => unsubscribe();
  }, []);

  // Zoom-to-element event handler
  useEffect(() => {
    const handleZoomToElement = (e: Event) => {
      const { globalId } = (
        e as CustomEvent<{ globalId: string }>
      ).detail;
      const currentEngine = engineRef.current;
      if (!currentEngine || !isReadyRef.current || !globalId) return;
      currentEngine.zoomToElement(globalId);
    };

    window.addEventListener("zoom-to-element", handleZoomToElement);
    return () => {
      window.removeEventListener("zoom-to-element", handleZoomToElement);
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
