/**
 * ModelBrowser — list of loaded models with visibility toggles.
 *
 * Shows each model in the current project with:
 * - File name and load state indicator
 * - Visibility toggle (eye icon)
 * - File size
 */

import { useStore } from "../../store";
import type { ModelInfo } from "../../types/project";

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
      return <span className="model-item__state model-item__state--pending" title="Wachten op laden" />;
    case "loading":
      return <span className="model-item__state model-item__state--loading" title="Laden..." />;
    case "loaded":
      return <span className="model-item__state model-item__state--loaded" title="Geladen" />;
    case "error":
      return <span className="model-item__state model-item__state--error" title={model.error ?? "Fout"} />;
  }
}

export function ModelBrowser() {
  const project = useStore((s) => s.project);
  const toggleVisibility = useStore((s) => s.toggleModelVisibility);

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
        <div key={model.id} className="model-item">
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
      ))}
    </div>
  );
}
