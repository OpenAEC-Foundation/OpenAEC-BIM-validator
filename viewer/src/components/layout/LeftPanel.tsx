/**
 * LeftPanel — Model browser and spatial tree.
 *
 * Shows loaded models and their spatial hierarchy.
 */

import { useStore } from "../../store";
import { ModelBrowser } from "../model-browser/ModelBrowser";
import { SpatialTree } from "../model-browser/SpatialTree";

export function LeftPanel() {
  const project = useStore((s) => s.project);

  return (
    <div className="panel">
      <div className="panel__header">
        <h2>Models</h2>
      </div>
      <div className="panel__content">
        {project ? (
          <>
            <ModelBrowser />
            <SpatialTree />
          </>
        ) : (
          <div className="empty-state">
            <p className="empty-state__text">
              Upload een IFC bestand om te beginnen
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
