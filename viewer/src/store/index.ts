/**
 * Combined Zustand store for the BIM platform.
 *
 * Merges all slices into a single store. Each slice manages
 * its own domain (project, viewer, validation, UI) but shares
 * the same store instance for cross-slice reactivity.
 *
 * The `persist` middleware saves the project state to localStorage
 * so that loaded models survive page refresh. The actual IFC bytes
 * are stored in IndexedDB (see modelCache.ts); on rehydration,
 * all model loadStates are reset to "pending" so the engine
 * can reload them from IndexedDB.
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

import {
  type ProjectSlice,
  createProjectSlice,
} from "./slices/projectSlice";
import {
  type ViewerSlice,
  createViewerSlice,
} from "./slices/viewerSlice";
import {
  type ValidationSlice,
  createValidationSlice,
} from "./slices/validationSlice";
import {
  type UiSlice,
  createUiSlice,
} from "./slices/uiSlice";
import type { Project } from "../types/project";

/** Combined store type */
export type AppStore = ProjectSlice & ViewerSlice & ValidationSlice & UiSlice;

/** Persisted subset of the store */
type PersistedState = {
  project: Project | null;
};

/** The single Zustand store instance */
export const useStore = create<AppStore>()(
  persist(
    (...args) => ({
      ...createProjectSlice(...args),
      ...createViewerSlice(...args),
      ...createValidationSlice(...args),
      ...createUiSlice(...args),
    }),
    {
      name: "bim-validator-store",
      storage: createJSONStorage(() => localStorage),
      partialize: (state): PersistedState => ({
        project: state.project,
      }),
      merge: (persistedState, currentState) => {
        const persisted = persistedState as Partial<PersistedState>;

        if (!persisted?.project) {
          return currentState;
        }

        // Reset runtime state on all models — engine must reload them
        const project: Project = {
          ...persisted.project,
          models: persisted.project.models.map((m) => ({
            ...m,
            loadState: "pending" as const,
            error: undefined,
            engineModelId: undefined,
            spatialTree: undefined,
          })),
        };

        return { ...currentState, project };
      },
    }
  )
);

/** Re-export slice types for convenience */
export type { ProjectSlice } from "./slices/projectSlice";
export type { ViewerSlice, HighlightGroup } from "./slices/viewerSlice";
export type { ValidationSlice, ValidationPhase } from "./slices/validationSlice";
export type { UiSlice } from "./slices/uiSlice";
