/**
 * Project I/O slice — manages save/open state and actions.
 *
 * Tracks the current project's save location (local vs cloud),
 * handles save/saveAs/open flows, and keyboard shortcut integration.
 */

import type { StateCreator } from "zustand";

/** Where the project was last saved/opened from */
export type ProjectSource = "local" | "cloud" | null;

/** Phase of a save/open operation */
export type ProjectIoPhase =
  | "idle"
  | "saving"
  | "opening"
  | "error";

/** Tracks the current project's save origin */
export interface ProjectSaveInfo {
  /** Source type: local file or cloud project */
  source: ProjectSource;
  /** Cloud project name (when source = 'cloud') */
  cloudProject?: string;
  /** Local filename (when source = 'local') */
  localFilename?: string;
  /** Whether the project has unsaved changes */
  dirty: boolean;
}

export interface ProjectIoSlice {
  // -- State --
  /** Current save info for the active project */
  projectSaveInfo: ProjectSaveInfo;
  /** Phase of the current I/O operation */
  projectIoPhase: ProjectIoPhase;
  /** Error from last I/O operation */
  projectIoError: string | null;

  // -- Actions --
  /** Mark project as dirty (has unsaved changes) */
  markDirty: () => void;
  /** Mark project as clean (just saved) */
  markClean: () => void;
  /** Update the save info after a successful save */
  setSaveInfo: (info: Partial<ProjectSaveInfo>) => void;
  /** Set the I/O phase */
  setProjectIoPhase: (phase: ProjectIoPhase) => void;
  /** Set the I/O error */
  setProjectIoError: (error: string | null) => void;
  /** Reset I/O state */
  resetProjectIo: () => void;
}

const INITIAL_SAVE_INFO: ProjectSaveInfo = {
  source: null,
  dirty: false,
};

export const createProjectIoSlice: StateCreator<ProjectIoSlice> = (set) => ({
  projectSaveInfo: { ...INITIAL_SAVE_INFO },
  projectIoPhase: "idle",
  projectIoError: null,

  markDirty: () => {
    set((state) => ({
      projectSaveInfo: { ...state.projectSaveInfo, dirty: true },
    }));
  },

  markClean: () => {
    set((state) => ({
      projectSaveInfo: { ...state.projectSaveInfo, dirty: false },
    }));
  },

  setSaveInfo: (info: Partial<ProjectSaveInfo>) => {
    set((state) => ({
      projectSaveInfo: { ...state.projectSaveInfo, ...info },
    }));
  },

  setProjectIoPhase: (phase: ProjectIoPhase) => {
    set({ projectIoPhase: phase });
  },

  setProjectIoError: (error: string | null) => {
    set({ projectIoError: error });
  },

  resetProjectIo: () => {
    set({
      projectSaveInfo: { ...INITIAL_SAVE_INFO },
      projectIoPhase: "idle",
      projectIoError: null,
    });
  },
});
