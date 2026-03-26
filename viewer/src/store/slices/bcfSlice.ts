/**
 * BCF slice — manages the local BCF issue queue, authentication,
 * and BCF Platform integration (project management + push).
 *
 * Three concerns:
 * A. Issue Queue — local list of BCF issues
 * B. Auth — OIDC (Authentik) or API key
 * C. Platform — projects, push, ZIP download
 */

import type { StateCreator } from "zustand";
import type {
  BcfApiConfig,
  BcfProject,
  BcfAuthState,
  CreateProjectRequest,
  PushProgress,
  PushResult,
} from "../../types/bcfPlatform";
import type { BcfIssue } from "../../types/bcfIssue";
import { createBcfPlatformApi } from "../../api/bcfPlatformApi";
import { generateBcfZip, downloadBlob } from "../../lib/bcfZipGenerator";
import {
  isOidcConfigured,
  initOidc,
  signinRedirect,
  processOidcCallback,
  getSignedInUser,
  signout,
  onTokenRenewed,
} from "../../lib/oidcManager";

const STORAGE_KEY_URL = "bcf-platform-url";
const STORAGE_KEY_APIKEY = "bcf-platform-apikey";

type BcfPhase =
  | "disconnected"
  | "connecting"
  | "connected"
  | "pushing"
  | "done"
  | "error";

export interface BcfSlice {
  // ── Issue Queue ────────────────────────────────────────
  bcfIssues: BcfIssue[];
  bcfAddIssue: (issue: BcfIssue) => void;
  bcfAddIssues: (issues: BcfIssue[]) => void;
  bcfUpdateIssue: (id: string, partial: Partial<BcfIssue>) => void;
  bcfRemoveIssue: (id: string) => void;
  bcfClearIssues: () => void;

  // ── Auth ───────────────────────────────────────────────
  bcfAuth: BcfAuthState;
  bcfOidcAvailable: boolean;
  bcfLoginOidc: () => Promise<void>;
  bcfLogout: () => Promise<void>;
  bcfConnectApiKey: (url: string, apiKey: string) => Promise<void>;
  bcfInitAuth: () => Promise<void>;

  // ── Platform ───────────────────────────────────────────
  bcfPlatformUrl: string;
  bcfPhase: BcfPhase;
  bcfProjects: BcfProject[];
  bcfSelectedProjectId: string | null;
  bcfError: string | null;

  bcfSetPlatformUrl: (url: string) => void;
  bcfRefreshProjects: () => Promise<void>;
  bcfSelectProject: (projectId: string | null) => void;
  bcfCreateProject: (data: CreateProjectRequest) => Promise<BcfProject | null>;

  // ── Push ───────────────────────────────────────────────
  bcfPushProgress: PushProgress | null;
  bcfPushResult: PushResult | null;
  bcfPushIssues: (issueIds?: string[]) => Promise<void>;
  bcfResetPush: () => void;

  // ── Local export ───────────────────────────────────────
  bcfDownloadZip: (issueIds?: string[]) => Promise<void>;
}

// ── Helpers ────────────────────────────────────────────────

function loadUrl(): string {
  return localStorage.getItem(STORAGE_KEY_URL) ?? "";
}

function loadApiKey(): string {
  return localStorage.getItem(STORAGE_KEY_APIKEY) ?? "";
}

function getApiConfig(state: { bcfPlatformUrl: string; bcfAuth: BcfAuthState }): BcfApiConfig | null {
  const token = state.bcfAuth.accessToken;
  const url = state.bcfPlatformUrl;
  if (!token || !url) return null;
  return { url, token };
}

// ── Slice creator ──────────────────────────────────────────

export const createBcfSlice: StateCreator<BcfSlice> = (set, get) => ({
  // ── Issue Queue state ──────────────────────────────────
  bcfIssues: [],

  bcfAddIssue: (issue: BcfIssue) => {
    set((s) => ({ bcfIssues: [...s.bcfIssues, issue] }));
  },

  bcfAddIssues: (issues: BcfIssue[]) => {
    set((s) => ({ bcfIssues: [...s.bcfIssues, ...issues] }));
  },

  bcfUpdateIssue: (id: string, partial: Partial<BcfIssue>) => {
    set((s) => ({
      bcfIssues: s.bcfIssues.map((i) =>
        i.id === id ? { ...i, ...partial } : i,
      ),
    }));
  },

  bcfRemoveIssue: (id: string) => {
    set((s) => ({ bcfIssues: s.bcfIssues.filter((i) => i.id !== id) }));
  },

  bcfClearIssues: () => {
    set({ bcfIssues: [] });
  },

  // ── Auth state ─────────────────────────────────────────
  bcfAuth: { method: "none" },
  bcfOidcAvailable: isOidcConfigured(),

  bcfInitAuth: async () => {
    // Try to restore OIDC session
    if (isOidcConfigured()) {
      try {
        initOidc();

        // Check for callback
        const callbackUser = await processOidcCallback();
        if (callbackUser) {
          set({
            bcfAuth: {
              method: "oidc",
              user: { name: callbackUser.name, email: callbackUser.email, sub: callbackUser.sub },
              accessToken: callbackUser.accessToken,
              expiresAt: callbackUser.expiresAt,
            },
            bcfPhase: "connecting",
          });
          // Load projects
          await get().bcfRefreshProjects();
          set({ bcfPhase: "connected" });
          return;
        }

        // Check for existing session
        const existingUser = await getSignedInUser();
        if (existingUser) {
          set({
            bcfAuth: {
              method: "oidc",
              user: { name: existingUser.name, email: existingUser.email, sub: existingUser.sub },
              accessToken: existingUser.accessToken,
              expiresAt: existingUser.expiresAt,
            },
            bcfPhase: "connecting",
          });
          await get().bcfRefreshProjects();
          set({ bcfPhase: "connected" });

          // Listen for token renewal
          onTokenRenewed((renewed) => {
            set((s) => ({
              bcfAuth: {
                ...s.bcfAuth,
                accessToken: renewed.accessToken,
                expiresAt: renewed.expiresAt,
              },
            }));
          });
          return;
        }
      } catch (err) {
        console.warn("OIDC init failed:", err);
      }
    }

    // Try API key from localStorage
    const savedUrl = loadUrl();
    const savedKey = loadApiKey();
    if (savedUrl && savedKey) {
      set({
        bcfPlatformUrl: savedUrl,
        bcfAuth: { method: "apikey", accessToken: savedKey },
        bcfPhase: "connecting",
      });
      try {
        await get().bcfRefreshProjects();
        set({ bcfPhase: "connected" });
      } catch {
        set({ bcfPhase: "disconnected", bcfAuth: { method: "none" } });
      }
    }
  },

  bcfLoginOidc: async () => {
    if (!isOidcConfigured()) {
      set({ bcfError: "OIDC niet geconfigureerd (VITE_OIDC_AUTHORITY / VITE_OIDC_CLIENT_ID ontbreken)" });
      return;
    }
    try {
      if (!getSignedInUser) initOidc();
      await signinRedirect();
      // Browser redirects away — no code after this runs
    } catch (err) {
      const msg = err instanceof Error ? err.message : "OIDC login mislukt";
      set({ bcfError: msg, bcfPhase: "error" });
    }
  },

  bcfLogout: async () => {
    const { bcfAuth } = get();
    if (bcfAuth.method === "oidc") {
      try {
        await signout();
      } catch {
        // continue with local cleanup
      }
    }

    // Clear API key storage
    localStorage.removeItem(STORAGE_KEY_URL);
    localStorage.removeItem(STORAGE_KEY_APIKEY);

    set({
      bcfAuth: { method: "none" },
      bcfPhase: "disconnected",
      bcfProjects: [],
      bcfSelectedProjectId: null,
      bcfPushProgress: null,
      bcfPushResult: null,
      bcfError: null,
    });
  },

  bcfConnectApiKey: async (url: string, apiKey: string) => {
    set({
      bcfPlatformUrl: url,
      bcfAuth: { method: "apikey", accessToken: apiKey },
      bcfPhase: "connecting",
      bcfError: null,
    });

    const api = createBcfPlatformApi({ url, token: apiKey });

    const ok = await api.testConnection();
    if (!ok) {
      set({
        bcfPhase: "error",
        bcfError: "Kan geen verbinding maken met het BCF Platform. Controleer de URL.",
      });
      return;
    }

    try {
      const projects = await api.listProjects();
      localStorage.setItem(STORAGE_KEY_URL, url);
      localStorage.setItem(STORAGE_KEY_APIKEY, apiKey);
      set({
        bcfPhase: "connected",
        bcfProjects: projects,
        bcfError: null,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Onbekende fout";
      set({
        bcfPhase: "error",
        bcfError: `Verbinding mislukt: ${message}`,
      });
    }
  },

  // ── Platform state ─────────────────────────────────────
  bcfPlatformUrl: loadUrl(),
  bcfPhase: "disconnected",
  bcfProjects: [],
  bcfSelectedProjectId: null,
  bcfError: null,

  bcfSetPlatformUrl: (url: string) => {
    localStorage.setItem(STORAGE_KEY_URL, url);
    set({ bcfPlatformUrl: url });
  },

  bcfRefreshProjects: async () => {
    const apiConfig = getApiConfig(get());
    if (!apiConfig) return;

    try {
      const api = createBcfPlatformApi(apiConfig);
      const projects = await api.listProjects();
      set({ bcfProjects: projects, bcfError: null });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Onbekende fout";
      set({ bcfError: `Projecten laden mislukt: ${message}` });
    }
  },

  bcfSelectProject: (projectId: string | null) => {
    set({ bcfSelectedProjectId: projectId });
  },

  bcfCreateProject: async (data: CreateProjectRequest) => {
    const apiConfig = getApiConfig(get());
    if (!apiConfig) return null;

    try {
      const api = createBcfPlatformApi(apiConfig);
      const project = await api.createProject(data);
      // Add to list and select it
      set((s) => ({
        bcfProjects: [...s.bcfProjects, project],
        bcfSelectedProjectId: project.project_id,
        bcfError: null,
      }));
      return project;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Onbekende fout";
      set({ bcfError: `Project aanmaken mislukt: ${message}` });
      return null;
    }
  },

  // ── Push ───────────────────────────────────────────────
  bcfPushProgress: null,
  bcfPushResult: null,

  bcfPushIssues: async (issueIds?: string[]) => {
    const { bcfSelectedProjectId, bcfIssues } = get();
    const apiConfig = getApiConfig(get());
    if (!apiConfig || !bcfSelectedProjectId) return;

    const toPush = issueIds
      ? bcfIssues.filter((i) => issueIds.includes(i.id))
      : bcfIssues.filter((i) => i.pushState === "queued");

    if (toPush.length === 0) return;

    const api = createBcfPlatformApi(apiConfig);

    set({
      bcfPhase: "pushing",
      bcfPushProgress: {
        total: toPush.length,
        completed: 0,
        failed: 0,
        currentTopic: toPush[0]?.title ?? null,
      },
    });

    const errors: string[] = [];
    let completed = 0;
    let failed = 0;

    for (const issue of toPush) {
      // Mark individual issue as pushing
      set((s) => ({
        bcfIssues: s.bcfIssues.map((i) =>
          i.id === issue.id ? { ...i, pushState: "pushing" as const } : i,
        ),
        bcfPushProgress: {
          total: toPush.length,
          completed,
          failed,
          currentTopic: issue.title,
        },
      }));

      try {
        // 1. Create topic
        const topic = await api.createTopic(
          bcfSelectedProjectId,
          issue.mapping.topic,
        );

        // 2. Create viewpoint with component selection
        if (issue.mapping.viewpoint.components?.selection?.length) {
          await api.createViewpoint(
            bcfSelectedProjectId,
            topic.guid,
            issue.mapping.viewpoint,
          );
        }

        // 3. Create comment
        await api.createComment(
          bcfSelectedProjectId,
          topic.guid,
          issue.mapping.comment,
        );

        completed++;

        // Mark issue as pushed
        set((s) => ({
          bcfIssues: s.bcfIssues.map((i) =>
            i.id === issue.id
              ? { ...i, pushState: "pushed" as const, remoteTopicGuid: topic.guid }
              : i,
          ),
        }));
      } catch (err) {
        failed++;
        const message = err instanceof Error ? err.message : "Onbekende fout";
        errors.push(`"${issue.title}": ${message}`);

        // Mark issue as failed
        set((s) => ({
          bcfIssues: s.bcfIssues.map((i) =>
            i.id === issue.id
              ? { ...i, pushState: "failed" as const, pushError: message }
              : i,
          ),
        }));
      }
    }

    set({
      bcfPhase: "done",
      bcfPushProgress: {
        total: toPush.length,
        completed,
        failed,
        currentTopic: null,
      },
      bcfPushResult: {
        projectId: bcfSelectedProjectId,
        topicsCreated: completed,
        topicsFailed: failed,
        errors,
      },
    });
  },

  bcfResetPush: () => {
    set({
      bcfPhase: "connected",
      bcfPushProgress: null,
      bcfPushResult: null,
      bcfError: null,
    });
  },

  // ── Local export ───────────────────────────────────────
  bcfDownloadZip: async (issueIds?: string[]) => {
    const { bcfIssues } = get();
    const toExport = issueIds
      ? bcfIssues.filter((i) => issueIds.includes(i.id))
      : bcfIssues;

    if (toExport.length === 0) return;

    try {
      const blob = await generateBcfZip(toExport);
      const timestamp = new Date().toISOString().slice(0, 10);
      downloadBlob(blob, `bim-validator-${timestamp}.bcf`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Onbekende fout";
      set({ bcfError: `BCF export mislukt: ${message}` });
    }
  },
});
