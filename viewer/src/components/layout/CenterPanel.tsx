/**
 * CenterPanel — 3D viewer canvas.
 *
 * Mounts the ViewerEngine and handles:
 * - Model file loading when files are added via the toolbar
 * - Store→Engine bridge for highlight synchronization
 * - Zoom-to-element events from the validation panel
 * - Property requests from the PropertiesPanel
 */

import { useRef, useEffect } from "react";

import { useViewer } from "../../engine/useViewer";
import { useStore } from "../../store";
import type { HighlightGroup } from "../../store";
import type { BcfCameraState } from "../../types/bcf";
import { getModelBytes, setCachedFile } from "../../engine/modelCache";

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

  // Store→Engine bridge: sync model visibility to the 3D engine
  useEffect(() => {
    let prevModels: Array<{ engineModelId?: string; visible: boolean }> = [];

    const unsubscribe = useStore.subscribe((state) => {
      const models = state.project?.models ?? [];
      const currentEngine = engineRef.current;
      if (!currentEngine || !isReadyRef.current) return;

      for (const model of models) {
        if (!model.engineModelId) continue;
        const prev = prevModels.find(
          (p) => p.engineModelId === model.engineModelId
        );
        if (!prev || prev.visible !== model.visible) {
          currentEngine.setModelVisibility(
            model.engineModelId,
            model.visible
          );
        }
      }

      prevModels = models.map((m) => ({
        engineModelId: m.engineModelId,
        visible: m.visible,
      }));
    });

    return () => unsubscribe();
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

  // Capture-viewpoint event handler: BCF panel requests a viewpoint capture
  // for specific globalIds. Handler zooms, highlights, screenshots, and responds.
  useEffect(() => {
    const handleCaptureViewpoint = async (e: Event) => {
      const { globalIds, requestId } = (
        e as CustomEvent<{ globalIds: string[]; requestId: string }>
      ).detail;
      const currentEngine = engineRef.current;

      if (!currentEngine || !isReadyRef.current || !globalIds?.length) {
        window.dispatchEvent(
          new CustomEvent("capture-viewpoint-response", {
            detail: { requestId, result: null },
          })
        );
        return;
      }

      try {
        const result = await currentEngine.captureViewpoint(globalIds);
        window.dispatchEvent(
          new CustomEvent("capture-viewpoint-response", {
            detail: { requestId, result },
          })
        );
      } catch {
        window.dispatchEvent(
          new CustomEvent("capture-viewpoint-response", {
            detail: { requestId, result: null },
          })
        );
      }
    };

    window.addEventListener("capture-viewpoint", handleCaptureViewpoint);
    return () => {
      window.removeEventListener("capture-viewpoint", handleCaptureViewpoint);
    };
  }, []);

  // Restore-camera event handler: BCF panel requests camera state restore
  useEffect(() => {
    const handleRestoreCamera = (e: Event) => {
      const { camera } = (
        e as CustomEvent<{ camera: BcfCameraState }>
      ).detail;
      const currentEngine = engineRef.current;
      if (!currentEngine || !isReadyRef.current || !camera) return;
      currentEngine.restoreCameraState(camera);
    };

    window.addEventListener("restore-camera", handleRestoreCamera);
    return () => {
      window.removeEventListener("restore-camera", handleRestoreCamera);
    };
  }, []);

  // Property request handler: PropertiesPanel dispatches this event,
  // CenterPanel (which owns the engine) resolves it and responds.
  useEffect(() => {
    const handlePropertyRequest = async (e: Event) => {
      const { globalId, requestId } = (
        e as CustomEvent<{ globalId: string; requestId: string }>
      ).detail;
      const currentEngine = engineRef.current;

      if (!currentEngine || !isReadyRef.current || !globalId) {
        window.dispatchEvent(
          new CustomEvent("property-response", {
            detail: { requestId, properties: null, error: "Engine niet gereed" },
          })
        );
        return;
      }

      try {
        const properties =
          await currentEngine.getElementProperties(globalId);
        window.dispatchEvent(
          new CustomEvent("property-response", {
            detail: { requestId, properties, error: null },
          })
        );
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Ophalen mislukt";
        window.dispatchEvent(
          new CustomEvent("property-response", {
            detail: { requestId, properties: null, error: msg },
          })
        );
      }
    };

    window.addEventListener("property-request", handlePropertyRequest);
    return () => {
      window.removeEventListener("property-request", handlePropertyRequest);
    };
  }, []);

  // Spatial tree request handler: ModelBrowser dispatches this to extract
  // the spatial hierarchy from a loaded model via the engine.
  useEffect(() => {
    const handleSpatialTreeRequest = async (e: Event) => {
      const { engineModelId, requestId } = (
        e as CustomEvent<{ engineModelId: string; requestId: string }>
      ).detail;
      const currentEngine = engineRef.current;

      if (!currentEngine || !isReadyRef.current || !engineModelId) {
        window.dispatchEvent(
          new CustomEvent("spatial-tree-response", {
            detail: { requestId, tree: null, error: "Engine niet gereed" },
          })
        );
        return;
      }

      try {
        const tree = await currentEngine.extractSpatialTree(engineModelId);
        window.dispatchEvent(
          new CustomEvent("spatial-tree-response", {
            detail: { requestId, tree, error: null },
          })
        );
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Extractie mislukt";
        window.dispatchEvent(
          new CustomEvent("spatial-tree-response", {
            detail: { requestId, tree: null, error: msg },
          })
        );
      }
    };

    window.addEventListener("spatial-tree-request", handleSpatialTreeRequest);
    return () => {
      window.removeEventListener(
        "spatial-tree-request",
        handleSpatialTreeRequest
      );
    };
  }, []);

  // Contained elements request handler: SpatialSubTree dispatches this to
  // get elements grouped by type for a spatial node.
  useEffect(() => {
    const handleContainedElementsRequest = async (e: Event) => {
      const { engineModelId, spatialGlobalId, requestId } = (
        e as CustomEvent<{
          engineModelId: string;
          spatialGlobalId: string;
          requestId: string;
        }>
      ).detail;
      const currentEngine = engineRef.current;

      if (
        !currentEngine ||
        !isReadyRef.current ||
        !engineModelId ||
        !spatialGlobalId
      ) {
        window.dispatchEvent(
          new CustomEvent("contained-elements-response", {
            detail: { requestId, groups: [], error: "Engine niet gereed" },
          })
        );
        return;
      }

      try {
        const groups = await currentEngine.getContainedElements(
          engineModelId,
          spatialGlobalId
        );
        window.dispatchEvent(
          new CustomEvent("contained-elements-response", {
            detail: { requestId, groups, error: null },
          })
        );
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Ophalen mislukt";
        window.dispatchEvent(
          new CustomEvent("contained-elements-response", {
            detail: { requestId, groups: [], error: msg },
          })
        );
      }
    };

    window.addEventListener(
      "contained-elements-request",
      handleContainedElementsRequest
    );
    return () => {
      window.removeEventListener(
        "contained-elements-request",
        handleContainedElementsRequest
      );
    };
  }, []);

  // Reload persisted models from IndexedDB when engine becomes ready.
  // On page refresh, the Zustand persist middleware restores the project
  // with all models in "pending" state. This effect picks them up and
  // reloads the IFC bytes from IndexedDB into the engine.
  useEffect(() => {
    if (!isReady || !engine) return;

    let cancelled = false;

    const pendingModels =
      useStore.getState().project?.models.filter(
        (m) => m.loadState === "pending"
      ) ?? [];

    if (pendingModels.length === 0) return;

    const reloadFromCache = async () => {
      for (const model of pendingModels) {
        if (cancelled) return;

        try {
          const bytes = await getModelBytes(model.fileName);
          if (cancelled) return;

          if (!bytes) {
            // No cached bytes — model can't be restored
            useStore.getState().removeModel(model.id);
            continue;
          }

          useStore.getState().updateModelLoadState(model.id, "loading");

          const file = new File([bytes], model.fileName, {
            type: "application/octet-stream",
          });

          // Restore in-memory file cache (needed for validation)
          setCachedFile(model.fileName, file);

          if (cancelled) {
            useStore.getState().updateModelLoadState(model.id, "pending");
            return;
          }

          const result = await engine.loadModel(file);
          if (cancelled) {
            useStore.getState().updateModelLoadState(model.id, "pending");
            return;
          }

          useStore.getState().setEngineModelId(model.id, result.modelId);
          useStore.getState().updateModelLoadState(model.id, "loaded");
        } catch (err) {
          if (cancelled) return;
          const msg = err instanceof Error ? err.message : "Herladen mislukt";
          useStore.getState().updateModelLoadState(model.id, "error", msg);
        }
      }
    };

    reloadFromCache();

    return () => {
      cancelled = true;
    };
  }, [isReady, engine]);

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
