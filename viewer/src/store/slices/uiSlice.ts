/**
 * UI slice — manages panel state and UI preferences.
 *
 * Controls which panels are visible, active tabs, and layout state.
 */

import type { StateCreator } from "zustand";
import type { RightPanelTab } from "../../types/project";

export interface UiSlice {
  /** Whether the left panel is collapsed */
  leftPanelCollapsed: boolean;

  /** Whether the right panel is collapsed */
  rightPanelCollapsed: boolean;

  /** Active tab in the right panel */
  activeRightTab: RightPanelTab;

  /** Status message shown in the toolbar */
  statusMessage: string | null;

  /** Toggle left panel */
  toggleLeftPanel: () => void;

  /** Toggle right panel */
  toggleRightPanel: () => void;

  /** Set active right panel tab */
  setActiveRightTab: (tab: RightPanelTab) => void;

  /** Set status message */
  setStatusMessage: (message: string | null) => void;
}

export const createUiSlice: StateCreator<UiSlice> = (set) => ({
  leftPanelCollapsed: false,
  rightPanelCollapsed: false,
  activeRightTab: "validation",
  statusMessage: null,

  toggleLeftPanel: () => {
    set((state) => ({ leftPanelCollapsed: !state.leftPanelCollapsed }));
  },

  toggleRightPanel: () => {
    set((state) => ({ rightPanelCollapsed: !state.rightPanelCollapsed }));
  },

  setActiveRightTab: (tab: RightPanelTab) => {
    set({ activeRightTab: tab, rightPanelCollapsed: false });
  },

  setStatusMessage: (message: string | null) => {
    set({ statusMessage: message });
  },
});
