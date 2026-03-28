/**
 * Viewer slice — manages 3D viewer interaction state.
 *
 * Tracks element selection, highlighting, and visibility state.
 * Acts as the bridge between UI interactions and the viewer engine.
 */

import type { StateCreator } from "zustand";

/** Highlight group for categorized highlighting */
export interface HighlightGroup {
  /** Group identifier (e.g., "validation-failures", "clash-elements") */
  id: string;
  /** CSS color for this highlight group */
  color: string;
  /** GlobalIds of highlighted elements */
  globalIds: string[];
}

export interface ViewerSlice {
  /** Currently selected element GlobalId (single selection) */
  selectedElementId: string | null;

  /** Whether selection should isolate (ghost other elements) */
  isolateOnSelect: boolean;

  /** Currently hovered element GlobalId */
  hoveredElementId: string | null;

  /** Active highlight groups */
  highlightGroups: HighlightGroup[];

  /** Hidden GlobalIds (manually hidden elements) */
  hiddenElementIds: Set<string>;

  /** Whether the viewer engine is initialized */
  viewerReady: boolean;

  /** Select an element by GlobalId. isolate=true ghosts all other elements. */
  selectElement: (globalId: string | null, isolate?: boolean) => void;

  /** Set hovered element */
  setHoveredElement: (globalId: string | null) => void;

  /** Add or update a highlight group */
  setHighlightGroup: (group: HighlightGroup) => void;

  /** Remove a highlight group */
  removeHighlightGroup: (groupId: string) => void;

  /** Clear all highlight groups */
  clearHighlights: () => void;

  /** Toggle element visibility */
  toggleElementVisibility: (globalId: string) => void;

  /** Show all elements */
  showAllElements: () => void;

  /** Mark viewer as ready */
  setViewerReady: (ready: boolean) => void;
}

export const createViewerSlice: StateCreator<ViewerSlice> = (set) => ({
  selectedElementId: null,
  isolateOnSelect: false,
  hoveredElementId: null,
  highlightGroups: [],
  hiddenElementIds: new Set<string>(),
  viewerReady: false,

  selectElement: (globalId: string | null, isolate?: boolean) => {
    set({ selectedElementId: globalId, isolateOnSelect: isolate ?? false });
  },

  setHoveredElement: (globalId: string | null) => {
    set({ hoveredElementId: globalId });
  },

  setHighlightGroup: (group: HighlightGroup) => {
    set((state) => ({
      highlightGroups: [
        ...state.highlightGroups.filter((g) => g.id !== group.id),
        group,
      ],
    }));
  },

  removeHighlightGroup: (groupId: string) => {
    set((state) => ({
      highlightGroups: state.highlightGroups.filter((g) => g.id !== groupId),
    }));
  },

  clearHighlights: () => {
    set({ highlightGroups: [] });
  },

  toggleElementVisibility: (globalId: string) => {
    set((state) => {
      const next = new Set(state.hiddenElementIds);
      if (next.has(globalId)) {
        next.delete(globalId);
      } else {
        next.add(globalId);
      }
      return { hiddenElementIds: next };
    });
  },

  showAllElements: () => {
    set({ hiddenElementIds: new Set<string>() });
  },

  setViewerReady: (ready: boolean) => {
    set({ viewerReady: ready });
  },
});
