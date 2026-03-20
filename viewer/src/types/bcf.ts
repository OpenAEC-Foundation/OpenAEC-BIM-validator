/**
 * BCF 2.1 compatible types for client-side issue management.
 *
 * These types mirror the bcf-core Rust crate (openaec-bcf-platform)
 * for future interop, but are self-contained for client-side use.
 * Designed for Zustand store + IndexedDB screenshot caching.
 */

// ─── Camera & Viewpoint ───────────────────────────────────────────

/** 3D point used in camera definitions (matches BCF 2.1 XSD) */
export interface Point3D {
  x: number;
  y: number;
  z: number;
}

/** Camera state compatible with BCF 2.1 perspective_camera / orthogonal_camera */
export interface BcfCameraState {
  /** Camera eye position */
  position: Point3D;
  /** View direction vector (target - position, normalized) */
  direction: Point3D;
  /** Camera up vector */
  up: Point3D;
  /** Field of view in degrees (perspective only) */
  fieldOfView?: number;
  /** Aspect ratio (width/height) */
  aspectRatio?: number;
  /** Camera type */
  type: "perspective" | "orthogonal";
}

/** Component reference by IFC GlobalId (BCF 2.1 Component) */
export interface BcfComponentRef {
  /** IFC GlobalId */
  ifcGuid: string;
  /** Originating system identifier */
  originatingSystem?: string;
  /** Authoring tool element ID */
  authoringToolId?: string;
}

/** Component visibility state (BCF 2.1 ComponentVisibility) */
export interface BcfComponentVisibility {
  /** If true, all components visible except exceptions. If false, all hidden except exceptions. */
  defaultVisibility: boolean;
  /** Components that are exceptions to the default */
  exceptions: BcfComponentRef[];
}

/** Colored component group (BCF 2.1 ColoredComponent) */
export interface BcfColoredComponents {
  /** Hex color string (e.g., "#FF4444") */
  color: string;
  /** Components with this color */
  components: BcfComponentRef[];
}

/** Component selection and visibility state for a viewpoint */
export interface BcfComponents {
  /** Selected components (highlighted in viewer) */
  selection: BcfComponentRef[];
  /** Visibility settings */
  visibility: BcfComponentVisibility;
  /** Color overrides */
  coloring: BcfColoredComponents[];
}

/** BCF Viewpoint — camera + snapshot + component state */
export interface BcfViewpoint {
  /** Unique viewpoint GUID */
  guid: string;
  /** Camera state */
  camera: BcfCameraState;
  /** PNG screenshot as data URL (stored in IndexedDB, referenced by guid) */
  screenshotDataUrl: string;
  /** Component selection/visibility/coloring */
  components: BcfComponents;
}

// ─── Issue / Topic ────────────────────────────────────────────────

/** Issue priority levels (BCF 2.1 Priority extension) */
export type IssuePriority = "Critical" | "High" | "Normal" | "Low";

/** Issue status (BCF 2.1 TopicStatus extension) */
export type IssueStatus = "Open" | "In Progress" | "Closed";

/** Issue type / topic type (BCF 2.1 TopicType extension) */
export type IssueType = "Error" | "Warning" | "Info" | "Clash" | "Comment" | "Request";

/** BCF Comment on a topic */
export interface BcfComment {
  /** Unique comment GUID */
  guid: string;
  /** Comment author */
  author: string;
  /** ISO 8601 creation date */
  date: string;
  /** Comment text */
  comment: string;
  /** Optional reference to a viewpoint */
  viewpointGuid?: string;
  /** ISO 8601 modified date */
  modifiedDate?: string;
  /** Modified by author */
  modifiedAuthor?: string;
}

/** BCF Issue (Topic) — the core unit of the BCF panel */
export interface BcfIssue {
  /** Unique topic GUID */
  guid: string;
  /** Issue title (used as topic title in BCF export) */
  title: string;
  /** Detailed description */
  description: string;
  /** Issue type classification */
  type: IssueType;
  /** Current status */
  status: IssueStatus;
  /** Priority level */
  priority: IssuePriority;
  /** Assigned person (free text in fase 1, later Authentik user) */
  assignedTo: string;
  /** ISO 8601 creation timestamp */
  creationDate: string;
  /** ISO 8601 last modified timestamp */
  modifiedDate: string;
  /** Author who created the issue */
  creationAuthor: string;
  /** Optional due date (ISO 8601 date string) */
  dueDate?: string;
  /** Labels / tags */
  labels: string[];
  /** Stage (optional, for workflow tracking) */
  stage?: string;

  // ─── Linked data ──────────────────────────────────────────────

  /** Primary viewpoint for this issue */
  viewpoint: BcfViewpoint;
  /** Comments / discussion thread */
  comments: BcfComment[];

  // ─── Source tracking (validator integration) ──────────────────

  /** Source IDS specification name (if generated from validation) */
  sourceSpecification?: string;
  /** Source requirement description */
  sourceRequirement?: string;
  /** GlobalIds of failed/affected elements */
  failedGlobalIds: string[];
  /** Display index for ordering */
  index: number;
}

// ─── Filter & Sort ────────────────────────────────────────────────

/** Filter options for issue list */
export type IssueFilter = IssueStatus | "all";

/** Sort options for issue list */
export type IssueSortBy = "date" | "priority" | "status" | "type";

/** Sort direction */
export type SortDirection = "asc" | "desc";

// ─── Issue creation helpers ───────────────────────────────────────

/** Metadata for creating an issue from validation results */
export interface IssueCreationMetadata {
  /** Issue title */
  title: string;
  /** Issue description (validation failure messages) */
  description: string;
  /** Issue type (mapped from validation severity) */
  type: IssueType;
  /** Priority (mapped from severity) */
  priority: IssuePriority;
  /** Source IDS specification name */
  specificationName?: string;
  /** Source requirement description */
  requirementDescription?: string;
  /** GlobalIds of failed elements */
  globalIds: string[];
}

/** Stats summary for the BCF panel header */
export interface IssueStats {
  open: number;
  inProgress: number;
  closed: number;
  total: number;
}

// ─── Project extensions (BCF 2.1) ─────────────────────────────────

/** Default values matching openaec-bcf-platform bcf-core */
export const DEFAULT_STATUSES: IssueStatus[] = ["Open", "In Progress", "Closed"];
export const DEFAULT_PRIORITIES: IssuePriority[] = ["Critical", "High", "Normal", "Low"];
export const DEFAULT_TYPES: IssueType[] = ["Error", "Warning", "Info", "Clash", "Comment", "Request"];

/** Map validation severity to issue type */
export function severityToIssueType(severity: string): IssueType {
  switch (severity) {
    case "error":
      return "Error";
    case "warning":
      return "Warning";
    case "info":
      return "Info";
    default:
      return "Error";
  }
}

/** Map validation severity to priority */
export function severityToPriority(severity: string): IssuePriority {
  switch (severity) {
    case "error":
      return "High";
    case "warning":
      return "Normal";
    case "info":
      return "Low";
    default:
      return "Normal";
  }
}
