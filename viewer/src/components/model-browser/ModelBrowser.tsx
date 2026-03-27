/**
 * ModelBrowser — list of loaded models with expandable spatial trees.
 *
 * Shows each model in the current project with:
 * - Expand chevron (loaded models only) → inline spatial tree
 * - File name and load state indicator
 * - Visibility toggle (eye icon)
 * - File size
 *
 * On first expand: dispatches "spatial-tree-request" to extract the
 * spatial hierarchy via CenterPanel → ViewerEngine → PropertyExtractor.
 * The tree is stored in the Zustand store (model.spatialTree).
 */

import { useState, useCallback } from "react";

import { useStore } from "../../store";
import type { ModelInfo } from "../../types/project";
import { SpatialSubTree } from "./SpatialSubTree";

import "./ModelBrowser.css";

/** Format bytes to human-readable string */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Load state indicator */
function LoadStateIndicator({ model }: { model: ModelInfo }) {
  switch (model.loadState) {
    case "pending":
      return (
        <span
          className="model-item__state model-item__state--pending"
          title="Wachten op laden"
        />
      );
    case "loading":
      return (
        <span
          className="model-item__state model-item__state--loading"
          title="Laden..."
        />
      );
    case "loaded":
      return (
        <span
          className="model-item__state model-item__state--loaded"
          title="Geladen"
        />
      );
    case "error":
      return (
        <span
          className="model-item__state model-item__state--error"
          title={model.error ?? "Fout"}
        />
      );
  }
}

/** A single model row with expand/collapse for spatial tree */
function ModelItem({ model }: { model: ModelInfo }) {
  const toggleVisibility = useStore((s) => s.toggleModelVisibility);
  const setModelSpatialTree = useStore((s) => s.setModelSpatialTree);

  const [expanded, setExpanded] = useState(false);
  const [loadingTree, setLoadingTree] = useState(false);

  const canExpand = model.loadState === "loaded" && !!model.engineModelId;

  const handleExpand = useCallback(() => {
    if (!canExpand) return;

    setExpanded((prev) => {
      const willExpand = !prev;

      // Lazy-load spatial tree on first expand
      if (willExpand && !model.spatialTree && !loadingTree) {
        setLoadingTree(true);
        const requestId = `tree-${model.id}-${Date.now()}`;

        const handleResponse = (e: Event) => {
          const detail = (
            e as CustomEvent<{
              requestId: string;
              tree: unknown;
              error: string | null;
            }>
          ).detail;
          if (detail.requestId !== requestId) return;

          window.removeEventListener(
            "spatial-tree-response",
            handleResponse
          );

          if (detail.tree) {
            setModelSpatialTree(
              model.id,
              detail.tree as import("../../types/project").SpatialNode
            );
          }
          setLoadingTree(false);
        };

        window.addEventListener("spatial-tree-response", handleResponse);
        window.dispatchEvent(
          new CustomEvent("spatial-tree-request", {
            detail: {
              engineModelId: model.engineModelId,
              requestId,
            },
          })
        );
      }

      return willExpand;
    });
  }, [
    canExpand,
    model.spatialTree,
    model.id,
    model.engineModelId,
    loadingTree,
    setModelSpatialTree,
  ]);

  return (
    <div className="model-item-wrapper">
      <div className="model-item">
        {/* Expand/collapse chevron */}
        <button
          type="button"
          className="model-item__expand"
          onClick={handleExpand}
          style={{ visibility: canExpand ? "visible" : "hidden" }}
          aria-label={expanded ? "Inklappen" : "Uitklappen"}
        >
          {expanded ? "\u25BE" : "\u25B8"}
        </button>

        <LoadStateIndicator model={model} />

        <div className="model-item__info">
          <span className="model-item__name" title={model.fileName}>
            {model.fileName}
          </span>
          <span className="model-item__size">
            {formatFileSize(model.fileSize)}
          </span>
        </div>

        <button
          type="button"
          className={`model-item__visibility ${
            !model.visible ? "model-item__visibility--hidden" : ""
          }`}
          onClick={() => toggleVisibility(model.id)}
          title={model.visible ? "Verberg model" : "Toon model"}
          aria-label={
            model.visible
              ? `Verberg ${model.fileName}`
              : `Toon ${model.fileName}`
          }
        >
          {model.visible ? "V" : "-"}
        </button>
      </div>

      {/* Expanded spatial tree */}
      {expanded && loadingTree && (
        <div className="model-item__tree-loading">
          <span className="spatial-node__spinner" />
          <span className="spatial-node__loading-text">
            Structuur laden...
          </span>
        </div>
      )}

      {expanded && model.spatialTree && model.engineModelId && (
        <SpatialSubTree
          tree={model.spatialTree}
          engineModelId={model.engineModelId}
        />
      )}
    </div>
  );
}

export function ModelBrowser() {
  const project = useStore((s) => s.project);

  if (!project || project.models.length === 0) {
    return (
      <div className="empty-state">
        <p className="empty-state__text">Geen modellen geladen</p>
      </div>
    );
  }

  return (
    <div className="model-browser">
      {project.models.map((model) => (
        <ModelItem key={model.id} model={model} />
      ))}
    </div>
  );
}
