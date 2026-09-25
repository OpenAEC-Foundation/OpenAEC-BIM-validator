/**
 * Combined Zustand store for the BIM platform.
 *
 * Merges all slices into a single store. Each slice manages
 * its own domain (project, viewer, validation, UI) but shares
 * the same store instance for cross-slice reactivity.
 */

import { create } from "zustand";

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
import {
  type BcfSlice,
  createBcfSlice,
} from "./slices/bcfSlice";
import {
  type CloudSlice,
  createCloudSlice,
} from "./slices/cloudSlice";
import {
  type ProjectIoSlice,
  createProjectIoSlice,
} from "./slices/projectIoSlice";
import {
  type AccountsSlice,
  createAccountsSlice,
} from "./slices/accountsSlice";

/** Combined store type */
export type AppStore = ProjectSlice & ViewerSlice & ValidationSlice & UiSlice & BcfSlice & CloudSlice & ProjectIoSlice & AccountsSlice;

/** The single Zustand store instance */
export const useStore = create<AppStore>()((...args) => ({
  ...createProjectSlice(...args),
  ...createViewerSlice(...args),
  ...createValidationSlice(...args),
  ...createUiSlice(...args),
  ...createBcfSlice(...args),
  ...createCloudSlice(...args),
  ...createProjectIoSlice(...args),
  ...createAccountsSlice(...args),
}));

/** Re-export slice types for convenience */
export type { ProjectSlice } from "./slices/projectSlice";
export type { ViewerSlice, HighlightGroup } from "./slices/viewerSlice";
export type { ValidationSlice, ValidationPhase } from "./slices/validationSlice";
export type { UiSlice } from "./slices/uiSlice";
export type { BcfSlice } from "./slices/bcfSlice";
export type { CloudSlice } from "./slices/cloudSlice";
export type { ProjectIoSlice, ProjectSource, ProjectIoPhase } from "./slices/projectIoSlice";
export type { AccountsSlice, AccountsUser } from "./slices/accountsSlice";
