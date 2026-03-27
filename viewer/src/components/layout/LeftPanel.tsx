/**
 * LeftPanel — Model browser (top) + Properties (bottom).
 *
 * Vertically split using react-resizable-panels.
 * Models section stays compact, Properties takes remaining space.
 */

import { Panel, Group, Separator } from "react-resizable-panels";

import { useStore } from "../../store";
import { ModelBrowser } from "../model-browser/ModelBrowser";
import { PropertiesPanel } from "../properties/PropertiesPanel";

export function LeftPanel() {
  const project = useStore((s) => s.project);

  return (
    <div className="panel">
      <Group orientation="vertical" id="left-panels" style={{ height: "100%" }}>
        {/* Models section (top) */}
        <Panel id="left-models" defaultSize="35%" minSize="15%">
          <div className="panel__section">
            <div className="panel__header panel__header--compact">
              <h2>Models</h2>
            </div>
            <div className="panel__content">
              {project ? (
                <ModelBrowser />
              ) : (
                <div className="empty-state empty-state--compact">
                  <p className="empty-state__text">
                    Upload een IFC bestand
                  </p>
                </div>
              )}
            </div>
          </div>
        </Panel>

        <Separator className="resize-handle resize-handle--vertical" />

        {/* Properties section (bottom) */}
        <Panel id="left-properties" minSize="20%">
          <div className="panel__section">
            <div className="panel__header panel__header--compact">
              <h2>Properties</h2>
            </div>
            <div className="panel__content">
              <PropertiesPanel />
            </div>
          </div>
        </Panel>
      </Group>
    </div>
  );
}
