/**
 * TypeScript types for the OpenAEC BCF Platform API (BCF 2.1).
 * Maps to the Rust models in openaec-bcf-platform.
 */

// ── Projects ────────────────────────────────────────────────

export interface BcfProject {
  project_id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
}

// ── Topics (Issues) ─────────────────────────────────────────

export interface BcfTopic {
  guid: string;
  project_id: string;
  title: string;
  description: string;
  topic_type: string;
  topic_status: string;
  priority: string;
  assigned_to: string | null;
  stage: string;
  labels: string[];
  due_date: string | null;
  index: number | null;
  creation_author: string | null;
  modified_author: string | null;
  creation_date: string;
  modified_date: string;
}

export interface CreateTopicRequest {
  title: string;
  description: string;
  topic_type?: string;
  topic_status?: string;
  priority?: string;
  labels?: string[];
  stage?: string;
  due_date?: string | null;
  index?: number;
}

export interface UpdateTopicRequest {
  title?: string;
  description?: string;
  topic_type?: string;
  topic_status?: string;
  priority?: string;
  labels?: string[];
  stage?: string;
  assigned_to?: string | null;
  due_date?: string | null;
}

// ── Comments ────────────────────────────────────────────────

export interface BcfComment {
  guid: string;
  topic_id: string;
  author_id: string | null;
  comment: string;
  viewpoint_guid: string | null;
  date: string;
  modified_date: string;
}

export interface CreateCommentRequest {
  comment: string;
  viewpoint_guid?: string;
}

// ── Viewpoints ──────────────────────────────────────────────

export interface Point3D {
  x: number;
  y: number;
  z: number;
}

export interface BcfCamera {
  camera_type: "perspective" | "orthogonal";
  position: Point3D;
  direction: Point3D;
  up: Point3D;
  field_of_view?: number;
  aspect_ratio?: number;
}

export interface ComponentRef {
  ifc_guid: string;
}

export interface BcfComponents {
  visibility?: {
    default_visibility: boolean;
    exceptions: ComponentRef[];
  };
  selection?: ComponentRef[];
  coloring?: Array<{
    color: string;
    components: ComponentRef[];
  }>;
}

export interface BcfViewpoint {
  guid: string;
  topic_id: string;
  camera: BcfCamera | null;
  components: BcfComponents | null;
  has_snapshot: boolean;
  creation_date: string;
}

export interface CreateViewpointRequest {
  camera?: BcfCamera;
  components?: BcfComponents;
}

// ── API Keys ────────────────────────────────────────────────

export interface BcfApiKey {
  id: string;
  project_id: string;
  name: string;
  prefix: string;
  created_by: string | null;
  expires_at: string | null;
  created_at: string;
}

// ── Platform config ─────────────────────────────────────────

/** Legacy config with API key */
export interface BcfPlatformConfig {
  url: string;
  apiKey: string;
}

/** Generic API config — works for both API keys and OIDC tokens */
export interface BcfApiConfig {
  url: string;
  token: string;
}

// ── OIDC / SSO ─────────────────────────────────────────────

export interface OidcConfig {
  /** Authentik issuer URL (e.g. https://auth.openaec.com/application/o/bim-validator/) */
  authority: string;
  /** OIDC client ID registered in Authentik */
  clientId: string;
  /** Redirect URI after login (e.g. window.location.origin) */
  redirectUri: string;
  /** OIDC scopes */
  scope: string;
}

export type BcfAuthMethod = "none" | "oidc" | "apikey";

export interface BcfAuthState {
  method: BcfAuthMethod;
  /** User info from OIDC */
  user?: { name: string; email: string; sub: string };
  /** Access token (OIDC JWT or API key) */
  accessToken?: string;
  /** Token expiry (epoch ms) */
  expiresAt?: number;
}

// ── Push result ─────────────────────────────────────────────

export interface PushProgress {
  total: number;
  completed: number;
  failed: number;
  currentTopic: string | null;
}

export interface PushResult {
  projectId: string;
  topicsCreated: number;
  topicsFailed: number;
  errors: string[];
}
