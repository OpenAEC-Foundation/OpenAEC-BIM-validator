/**
 * Cloud slice — manages Nextcloud cloud storage state.
 *
 * Handles project listing, file browsing, upload/download/delete
 * operations against the backend cloud proxy endpoints.
 */

import type { StateCreator } from "zustand";
import type { CloudProject, CloudFile } from "../../api/cloudApi";
import {
  cloudStatus as apiCloudStatus,
  cloudListProjects as apiListProjects,
  cloudListFiles as apiListFiles,
  cloudUploadFile as apiUploadFile,
  cloudDownloadFile as apiDownloadFile,
  cloudDeleteFile as apiDeleteFile,
  cloudSaveManifest as apiSaveManifest,
} from "../../api/cloudApi";

type CloudPhase =
  | "idle"
  | "checking"
  | "loading"
  | "uploading"
  | "downloading"
  | "deleting"
  | "error";

export interface CloudSlice {
  // ── State ──────────────────────────────────────────────────
  cloudEnabled: boolean;
  cloudConnected: boolean;
  cloudPhase: CloudPhase;
  cloudError: string | null;
  cloudProjects: CloudProject[];
  cloudSelectedProject: string | null;
  cloudFiles: CloudFile[];

  // ── Actions ────────────────────────────────────────────────
  cloudCheckStatus: () => Promise<void>;
  cloudLoadProjects: () => Promise<void>;
  cloudSelectProject: (project: string | null) => void;
  cloudLoadFiles: (project?: string) => Promise<void>;
  cloudUpload: (project: string, filename: string, blob: Blob, category?: "bim" | "output") => Promise<boolean>;
  cloudDownload: (project: string, filename: string) => Promise<Blob | null>;
  cloudDelete: (project: string, filename: string) => Promise<boolean>;
  cloudSaveManifest: (project: string, manifest: Record<string, unknown>) => Promise<boolean>;
  cloudReset: () => void;
}

export const createCloudSlice: StateCreator<CloudSlice> = (set, get) => ({
  // ── Initial state ──────────────────────────────────────────
  cloudEnabled: false,
  cloudConnected: false,
  cloudPhase: "idle",
  cloudError: null,
  cloudProjects: [],
  cloudSelectedProject: null,
  cloudFiles: [],

  cloudCheckStatus: async () => {
    set({ cloudPhase: "checking", cloudError: null });
    try {
      const status = await apiCloudStatus();
      set({
        cloudEnabled: status.enabled,
        cloudConnected: status.connected,
        cloudPhase: "idle",
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Status check failed";
      set({ cloudPhase: "error", cloudError: message });
    }
  },

  cloudLoadProjects: async () => {
    set({ cloudPhase: "loading", cloudError: null });
    try {
      const projects = await apiListProjects();
      set({ cloudProjects: projects, cloudPhase: "idle" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load projects";
      set({ cloudPhase: "error", cloudError: message });
    }
  },

  cloudSelectProject: (project: string | null) => {
    set({ cloudSelectedProject: project, cloudFiles: [] });
  },

  cloudLoadFiles: async (project?: string) => {
    const targetProject = project ?? get().cloudSelectedProject;
    if (!targetProject) return;

    set({ cloudPhase: "loading", cloudError: null });
    try {
      const files = await apiListFiles(targetProject);
      set({ cloudFiles: files, cloudPhase: "idle" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load files";
      set({ cloudPhase: "error", cloudError: message });
    }
  },

  cloudUpload: async (project: string, filename: string, blob: Blob, category?: "bim" | "output") => {
    set({ cloudPhase: "uploading", cloudError: null });
    try {
      await apiUploadFile(project, filename, blob, category);
      // Refresh file list after upload
      const files = await apiListFiles(project);
      set({ cloudFiles: files, cloudPhase: "idle" });
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed";
      set({ cloudPhase: "error", cloudError: message });
      return false;
    }
  },

  cloudDownload: async (project: string, filename: string) => {
    set({ cloudPhase: "downloading", cloudError: null });
    try {
      const blob = await apiDownloadFile(project, filename);
      set({ cloudPhase: "idle" });
      return blob;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Download failed";
      set({ cloudPhase: "error", cloudError: message });
      return null;
    }
  },

  cloudDelete: async (project: string, filename: string) => {
    set({ cloudPhase: "deleting", cloudError: null });
    try {
      await apiDeleteFile(project, filename);
      // Refresh file list after delete
      const files = await apiListFiles(project);
      set({ cloudFiles: files, cloudPhase: "idle" });
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Delete failed";
      set({ cloudPhase: "error", cloudError: message });
      return false;
    }
  },

  cloudSaveManifest: async (project: string, manifest: Record<string, unknown>) => {
    try {
      await apiSaveManifest(project, manifest);
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Manifest save failed";
      set({ cloudError: message });
      return false;
    }
  },

  cloudReset: () => {
    set({
      cloudPhase: "idle",
      cloudError: null,
      cloudProjects: [],
      cloudSelectedProject: null,
      cloudFiles: [],
    });
  },
});
