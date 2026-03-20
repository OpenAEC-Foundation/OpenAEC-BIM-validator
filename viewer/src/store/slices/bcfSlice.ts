/**
 * BCF slice — manages BCF issue state in the Zustand store.
 *
 * Handles issue CRUD, filtering, sorting, viewpoint generation
 * from validation results, and BCF export preparation.
 *
 * Screenshots are stored as data URLs in the issue objects.
 * For production use with 100+ issues, migrate to IndexedDB
 * via a screenshotCache (same pattern as modelCache.ts).
 */

import type { StateCreator } from "zustand";
import type {
  BcfIssue,
  BcfComment,
  BcfViewpoint,
  BcfCameraState,
  IssueFilter,
  IssueSortBy,
  SortDirection,
  IssueStats,
  IssueCreationMetadata,
  IssueStatus,
  IssuePriority,
} from "../../types/bcf";
import {
  severityToIssueType,
  severityToPriority,
} from "../../types/bcf";
import type {
  ValidationResult,
  SpecificationResult,
  ElementResult,
} from "../../types/validation";

/** Callback to capture a viewpoint from the viewer engine */
export type ViewpointCaptureCallback = (
  globalIds: string[]
) => Promise<{ screenshot: string; camera: BcfCameraState } | null>;

/** BCF sync status */
export type BcfSyncStatus = "idle" | "syncing" | "done" | "error";

export interface BcfSlice {
  // ─── State ──────────────────────────────────────────────────────

  /** All BCF issues */
  bcfIssues: BcfIssue[];

  /** Currently active/selected issue GUID (detail view) */
  activeBcfIssueId: string | null;

  /** Filter for issue list */
  bcfFilter: IssueFilter;

  /** Sort field */
  bcfSortBy: IssueSortBy;

  /** Sort direction */
  bcfSortDirection: SortDirection;

  /** Whether bulk issue generation is in progress */
  bcfGenerating: boolean;

  /** Progress message during generation */
  bcfGenerationProgress: string | null;

  /** BCF Platform project ID (persisted) */
  bcfPlatformProjectId: string | null;

  /** Current sync status */
  bcfSyncStatus: BcfSyncStatus;

  /** Sync progress message */
  bcfSyncProgress: string | null;

  // ─── CRUD Actions ───────────────────────────────────────────────

  /** Add a new issue to the store */
  addBcfIssue: (issue: BcfIssue) => void;

  /** Update an existing issue by GUID */
  updateBcfIssue: (guid: string, updates: Partial<BcfIssue>) => void;

  /** Delete an issue by GUID */
  deleteBcfIssue: (guid: string) => void;

  /** Set the active issue (opens detail view) */
  setActiveBcfIssue: (guid: string | null) => void;

  /** Add a comment to an issue */
  addBcfComment: (issueGuid: string, comment: BcfComment) => void;

  // ─── Filter & Sort ──────────────────────────────────────────────

  /** Set the issue list filter */
  setBcfFilter: (filter: IssueFilter) => void;

  /** Set sort field */
  setBcfSortBy: (sortBy: IssueSortBy) => void;

  /** Toggle sort direction */
  toggleBcfSortDirection: () => void;

  // ─── Validation Integration ─────────────────────────────────────

  /**
   * Generate BCF issues from validation results (bulk).
   * Creates one issue per failed specification.
   */
  generateBcfFromValidation: (
    validationResult: ValidationResult,
    captureViewpoint: ViewpointCaptureCallback
  ) => Promise<void>;

  /**
   * Create a single BCF issue from a specification.
   */
  createBcfFromSpecification: (
    spec: SpecificationResult,
    captureViewpoint: ViewpointCaptureCallback
  ) => Promise<void>;

  /**
   * Create a single BCF issue from one element.
   */
  createBcfFromElement: (
    element: ElementResult,
    specName: string,
    captureViewpoint: ViewpointCaptureCallback
  ) => Promise<void>;

  // ─── Computed helpers ───────────────────────────────────────────

  /** Get filtered + sorted issues */
  getFilteredBcfIssues: () => BcfIssue[];

  /** Get issue statistics */
  getBcfStats: () => IssueStats;

  /** Clear all BCF issues */
  clearAllBcfIssues: () => void;

  // ─── Platform Sync ──────────────────────────────────────────────

  /** Set the BCF platform project ID */
  setBcfPlatformProjectId: (id: string | null) => void;

  /** Set the sync status */
  setBcfSyncStatus: (status: BcfSyncStatus) => void;

  /** Set sync progress message */
  setBcfSyncProgress: (progress: string | null) => void;
}

// ─── Helper: create a placeholder viewpoint ─────────────────────

function createPlaceholderViewpoint(): BcfViewpoint {
  return {
    guid: crypto.randomUUID(),
    camera: {
      position: { x: 15, y: 15, z: 15 },
      direction: { x: -0.577, y: -0.577, z: -0.577 },
      up: { x: 0, y: 1, z: 0 },
      type: "perspective",
      fieldOfView: 60,
    },
    screenshotDataUrl: "",
    components: {
      selection: [],
      visibility: { defaultVisibility: true, exceptions: [] },
      coloring: [],
    },
  };
}

// ─── Helper: build a BcfIssue object ────────────────────────────

function buildIssue(
  meta: IssueCreationMetadata,
  viewpoint: BcfViewpoint,
  index: number
): BcfIssue {
  const now = new Date().toISOString();
  const guid = crypto.randomUUID();

  // Build first comment from validation failure description
  const initialComment: BcfComment = {
    guid: crypto.randomUUID(),
    author: "Validator",
    date: now,
    comment: meta.description,
    viewpointGuid: viewpoint.guid,
  };

  return {
    guid,
    title: meta.title,
    description: meta.description,
    type: meta.type,
    status: "Open",
    priority: meta.priority,
    assignedTo: "",
    creationDate: now,
    modifiedDate: now,
    creationAuthor: "Validator",
    labels: meta.specificationName ? [meta.specificationName] : [],
    viewpoint,
    comments: [initialComment],
    sourceSpecification: meta.specificationName,
    sourceRequirement: meta.requirementDescription,
    failedGlobalIds: meta.globalIds,
    index,
  };
}

// ─── Helper: extract failed GlobalIds from a specification ──────

function extractFailedGlobalIds(spec: SpecificationResult): string[] {
  const ids: string[] = [];
  for (const req of spec.requirements) {
    for (const el of req.elements) {
      if (el.status === "fail" && el.global_id) {
        ids.push(el.global_id);
      }
    }
  }
  // Deduplicate
  return [...new Set(ids)];
}

// ─── Helper: build description from spec failures ───────────────

function buildSpecDescription(spec: SpecificationResult): string {
  const failedReqs = spec.requirements.filter((r) => r.status === "fail");
  const lines = failedReqs.map(
    (r) => `- ${r.requirement_description} (${r.failed_elements} gefaald)`
  );
  return `Validatie gefaald voor specificatie "${spec.specification_name}":\n${lines.join("\n")}`;
}

// ─── Helper: build viewpoint with captured data ─────────────────

function buildViewpoint(
  globalIds: string[],
  capture: { screenshot: string; camera: BcfCameraState } | null
): BcfViewpoint {
  const viewpoint: BcfViewpoint = {
    guid: crypto.randomUUID(),
    camera: capture?.camera ?? createPlaceholderViewpoint().camera,
    screenshotDataUrl: capture?.screenshot ?? "",
    components: {
      selection: globalIds.map((id) => ({ ifcGuid: id })),
      visibility: { defaultVisibility: true, exceptions: [] },
      coloring: [
        {
          color: "#FF4444",
          components: globalIds.map((id) => ({ ifcGuid: id })),
        },
      ],
    },
  };
  return viewpoint;
}

// ─── Sorting helpers ────────────────────────────────────────────

const PRIORITY_ORDER: Record<IssuePriority, number> = {
  Critical: 0,
  High: 1,
  Normal: 2,
  Low: 3,
};

const STATUS_ORDER: Record<IssueStatus, number> = {
  Open: 0,
  "In Progress": 1,
  Closed: 2,
};

function sortIssues(
  issues: BcfIssue[],
  sortBy: IssueSortBy,
  direction: SortDirection
): BcfIssue[] {
  const sorted = [...issues].sort((a, b) => {
    let cmp = 0;
    switch (sortBy) {
      case "date":
        cmp =
          new Date(b.modifiedDate).getTime() -
          new Date(a.modifiedDate).getTime();
        break;
      case "priority":
        cmp = PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority];
        break;
      case "status":
        cmp = STATUS_ORDER[a.status] - STATUS_ORDER[b.status];
        break;
      case "type":
        cmp = a.type.localeCompare(b.type);
        break;
    }
    return direction === "asc" ? cmp : -cmp;
  });
  return sorted;
}

// ─── Slice creator ──────────────────────────────────────────────

export const createBcfSlice: StateCreator<BcfSlice> = (set, get) => ({
  // State
  bcfIssues: [],
  activeBcfIssueId: null,
  bcfFilter: "all",
  bcfSortBy: "date",
  bcfSortDirection: "desc",
  bcfGenerating: false,
  bcfGenerationProgress: null,
  bcfPlatformProjectId: null,
  bcfSyncStatus: "idle",
  bcfSyncProgress: null,

  // ─── CRUD ───────────────────────────────────────────────────────

  addBcfIssue: (issue: BcfIssue) => {
    set((state) => ({
      bcfIssues: [...state.bcfIssues, issue],
    }));
  },

  updateBcfIssue: (guid: string, updates: Partial<BcfIssue>) => {
    set((state) => ({
      bcfIssues: state.bcfIssues.map((issue) =>
        issue.guid === guid
          ? { ...issue, ...updates, modifiedDate: new Date().toISOString() }
          : issue
      ),
    }));
  },

  deleteBcfIssue: (guid: string) => {
    set((state) => ({
      bcfIssues: state.bcfIssues.filter((i) => i.guid !== guid),
      activeBcfIssueId:
        state.activeBcfIssueId === guid ? null : state.activeBcfIssueId,
    }));
  },

  setActiveBcfIssue: (guid: string | null) => {
    set({ activeBcfIssueId: guid });
  },

  addBcfComment: (issueGuid: string, comment: BcfComment) => {
    set((state) => ({
      bcfIssues: state.bcfIssues.map((issue) =>
        issue.guid === issueGuid
          ? {
              ...issue,
              comments: [...issue.comments, comment],
              modifiedDate: new Date().toISOString(),
            }
          : issue
      ),
    }));
  },

  // ─── Filter & Sort ──────────────────────────────────────────────

  setBcfFilter: (filter: IssueFilter) => {
    set({ bcfFilter: filter });
  },

  setBcfSortBy: (sortBy: IssueSortBy) => {
    set({ bcfSortBy: sortBy });
  },

  toggleBcfSortDirection: () => {
    set((state) => ({
      bcfSortDirection: state.bcfSortDirection === "asc" ? "desc" : "asc",
    }));
  },

  // ─── Validation Integration ─────────────────────────────────────

  generateBcfFromValidation: async (
    validationResult: ValidationResult,
    captureViewpoint: ViewpointCaptureCallback
  ) => {
    const failedSpecs = validationResult.specifications.filter(
      (s) => s.status === "fail"
    );

    if (failedSpecs.length === 0) return;

    set({ bcfGenerating: true, bcfGenerationProgress: "Issues genereren..." });

    const newIssues: BcfIssue[] = [];
    const existingCount = get().bcfIssues.length;

    for (const [i, spec] of failedSpecs.entries()) {
      set({
        bcfGenerationProgress: `Issue ${i + 1}/${failedSpecs.length}: ${spec.specification_name}`,
      });

      const globalIds = extractFailedGlobalIds(spec);
      if (globalIds.length === 0) continue;

      // Capture viewpoint (zoom + screenshot)
      const capture = await captureViewpoint(globalIds);

      const viewpoint = buildViewpoint(globalIds, capture);

      const meta: IssueCreationMetadata = {
        title: spec.specification_name,
        description: buildSpecDescription(spec),
        type: severityToIssueType(spec.severity),
        priority: severityToPriority(spec.severity),
        specificationName: spec.specification_name,
        globalIds,
      };

      const issue = buildIssue(meta, viewpoint, existingCount + i);
      newIssues.push(issue);
    }

    set((state) => ({
      bcfIssues: [...state.bcfIssues, ...newIssues],
      bcfGenerating: false,
      bcfGenerationProgress: null,
    }));
  },

  createBcfFromSpecification: async (
    spec: SpecificationResult,
    captureViewpoint: ViewpointCaptureCallback
  ) => {
    const globalIds = extractFailedGlobalIds(spec);
    if (globalIds.length === 0) return;

    const capture = await captureViewpoint(globalIds);
    const viewpoint = buildViewpoint(globalIds, capture);

    const meta: IssueCreationMetadata = {
      title: spec.specification_name,
      description: buildSpecDescription(spec),
      type: severityToIssueType(spec.severity),
      priority: severityToPriority(spec.severity),
      specificationName: spec.specification_name,
      globalIds,
    };

    const issue = buildIssue(meta, viewpoint, get().bcfIssues.length);

    set((state) => ({
      bcfIssues: [...state.bcfIssues, issue],
    }));
  },

  createBcfFromElement: async (
    element: ElementResult,
    specName: string,
    captureViewpoint: ViewpointCaptureCallback
  ) => {
    if (!element.global_id) return;

    const globalIds = [element.global_id];
    const capture = await captureViewpoint(globalIds);
    const viewpoint = buildViewpoint(globalIds, capture);

    const elementName = element.element_name
      ? `${element.element_type}: ${element.element_name}`
      : element.element_type;

    const meta: IssueCreationMetadata = {
      title: `${elementName} — ${specName}`,
      description: element.messages.join("\n"),
      type: "Error",
      priority: "Normal",
      specificationName: specName,
      requirementDescription: specName,
      globalIds,
    };

    const issue = buildIssue(meta, viewpoint, get().bcfIssues.length);

    set((state) => ({
      bcfIssues: [...state.bcfIssues, issue],
    }));
  },

  // ─── Computed ───────────────────────────────────────────────────

  getFilteredBcfIssues: (): BcfIssue[] => {
    const { bcfIssues, bcfFilter, bcfSortBy, bcfSortDirection } = get();

    let filtered = bcfIssues;
    if (bcfFilter !== "all") {
      filtered = bcfIssues.filter((i) => i.status === bcfFilter);
    }

    return sortIssues(filtered, bcfSortBy, bcfSortDirection);
  },

  getBcfStats: (): IssueStats => {
    const { bcfIssues } = get();
    return {
      open: bcfIssues.filter((i) => i.status === "Open").length,
      inProgress: bcfIssues.filter((i) => i.status === "In Progress").length,
      closed: bcfIssues.filter((i) => i.status === "Closed").length,
      total: bcfIssues.length,
    };
  },

  clearAllBcfIssues: () => {
    set({ bcfIssues: [], activeBcfIssueId: null });
  },

  // ─── Platform Sync ──────────────────────────────────────────────

  setBcfPlatformProjectId: (id: string | null) => {
    set({ bcfPlatformProjectId: id });
  },

  setBcfSyncStatus: (status: BcfSyncStatus) => {
    set({ bcfSyncStatus: status });
  },

  setBcfSyncProgress: (progress: string | null) => {
    set({ bcfSyncProgress: progress });
  },
});
