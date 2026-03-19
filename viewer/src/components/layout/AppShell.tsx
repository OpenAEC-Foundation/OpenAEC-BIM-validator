/**
 * AppShell — 3-panel layout for the BIM platform.
 *
 * Uses react-resizable-panels for drag-to-resize panels:
 * - Left: Model browser + spatial tree
 * - Center: 3D viewer
 * - Right: Properties / Validation / Clashes / BCF tabs
 */

import {
  Panel,
  Group,
  Separator,
} from "react-resizable-panels";

import { useStore } from "../../store";
import { useDemoMode } from "../../demo/useDemoMode";
import { Toolbar } from "./Toolbar";
import { LeftPanel } from "./LeftPanel";
import { CenterPanel } from "./CenterPanel";
import { RightPanel } from "./RightPanel";

import "./AppShell.css";

/** Default panel sizes (percentages) */
const LEFT_PANEL_DEFAULT = "25%";
const LEFT_PANEL_MIN = "15%";
const RIGHT_PANEL_DEFAULT = "25%";
const RIGHT_PANEL_MIN = "15%";
const CENTER_PANEL_MIN = "30%";

export function AppShell() {
  useDemoMode();

  const leftCollapsed = useStore((s) => s.leftPanelCollapsed);
  const rightCollapsed = useStore((s) => s.rightPanelCollapsed);

  return (
    <div className="app-shell">
      <Toolbar />

      <div className="app-shell__panels">
        <Group orientation="horizontal" id="bim-panels" style={{ height: "100%" }}>
          {/* Left Panel */}
          {!leftCollapsed && (
            <>
              <Panel
                id="left"
                defaultSize={LEFT_PANEL_DEFAULT}
                minSize={LEFT_PANEL_MIN}
              >
                <LeftPanel />
              </Panel>
              <Separator className="resize-handle resize-handle--horizontal" />
            </>
          )}

          {/* Center Panel (3D Viewer) */}
          <Panel
            id="center"
            minSize={CENTER_PANEL_MIN}
          >
            <CenterPanel />
          </Panel>

          {/* Right Panel */}
          {!rightCollapsed && (
            <>
              <Separator className="resize-handle resize-handle--horizontal" />
              <Panel
                id="right"
                defaultSize={RIGHT_PANEL_DEFAULT}
                minSize={RIGHT_PANEL_MIN}
              >
                <RightPanel />
              </Panel>
            </>
          )}
        </Group>
      </div>
    </div>
  );
}
