/**
 * Project API client — v2 endpoints for multi-model BIM platform.
 *
 * Provides functions for project management, file upload/download,
 * spatial tree retrieval, and element property queries.
 */

import type { SpatialNode, ElementProperties } from "../types/project";
import { API_ORIGIN } from "./apiBase";

/** Base URL for v2 API endpoints */
const API_V2 = `${API_ORIGIN}/api/v2`;

/** API error class */
export class ProjectApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number
  ) {
    super(message);
    this.name = "ProjectApiError";
  }
}

/** Parse error response */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const data = await response.json();
      detail = data.detail ?? detail;
    } catch {
      // ignore parse errors
    }
    throw new ProjectApiError(detail, response.status);
  }
  return response.json();
}

// ── Types ──────────────────────────────────────────────────────

/** Project summary from list endpoint */
export interface ProjectSummary {
  id: string;
  name: string;
  description: string | null;
  createdAt: string;
  updatedAt: string;
  fileCount: number;
}

/** File record from API */
export interface ProjectFileResponse {
  id: string;
  projectId: string;
  fileType: "ifc" | "bcf" | "ids";
  fileName: string;
  fileSize: number;
  uploadedAt: string;
  metadata: Record<string, unknown> | null;
}

/** Full project detail from API */
export interface ProjectDetailResponse {
  id: string;
  name: string;
  description: string | null;
  createdAt: string;
  updatedAt: string;
  files: ProjectFileResponse[];
}

/** Model response from API (legacy compatibility) */
export interface ModelResponse {
  id: string;
  fileName: string;
  fileSize: number;
  format: string;
  loadedAt?: string;
  hasSpatialTree: boolean;
}

// ── Project CRUD ──────────────────────────────────────────────

/**
 * List all projects.
 */
export async function listProjects(): Promise<ProjectSummary[]> {
  const response = await fetch(`${API_V2}/projects`);
  const data = await handleResponse<{ projects: ProjectSummary[] }>(response);
  return data.projects;
}

/**
 * Create a new project.
 */
export async function createProject(
  name: string,
  description?: string
): Promise<ProjectDetailResponse> {
  const formData = new FormData();
  formData.append("name", name);
  if (description) {
    formData.append("description", description);
  }

  const response = await fetch(`${API_V2}/projects`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<ProjectDetailResponse>(response);
}

/**
 * Get project details including files.
 */
export async function getProject(
  projectId: string
): Promise<ProjectDetailResponse> {
  const response = await fetch(`${API_V2}/projects/${projectId}`);
  return handleResponse<ProjectDetailResponse>(response);
}

/**
 * Update project name and/or description.
 */
export async function updateProject(
  projectId: string,
  data: { name?: string; description?: string }
): Promise<ProjectDetailResponse> {
  const formData = new FormData();
  if (data.name !== undefined) formData.append("name", data.name);
  if (data.description !== undefined)
    formData.append("description", data.description);

  const response = await fetch(`${API_V2}/projects/${projectId}`, {
    method: "PUT",
    body: formData,
  });
  return handleResponse<ProjectDetailResponse>(response);
}

/**
 * Delete a project and all its files.
 */
export async function deleteProject(projectId: string): Promise<void> {
  const response = await fetch(`${API_V2}/projects/${projectId}`, {
    method: "DELETE",
  });
  await handleResponse(response);
}

// ── File Management ───────────────────────────────────────────

/**
 * Upload a file to a project.
 */
export async function uploadFile(
  projectId: string,
  file: File,
  fileType: "ifc" | "bcf" | "ids"
): Promise<ProjectFileResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("file_type", fileType);

  const response = await fetch(`${API_V2}/projects/${projectId}/files`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<ProjectFileResponse>(response);
}

/**
 * List files in a project.
 */
export async function listFiles(
  projectId: string,
  fileType?: "ifc" | "bcf" | "ids"
): Promise<ProjectFileResponse[]> {
  const params = fileType ? `?file_type=${fileType}` : "";
  const response = await fetch(
    `${API_V2}/projects/${projectId}/files${params}`
  );
  const data = await handleResponse<{ files: ProjectFileResponse[] }>(
    response
  );
  return data.files;
}

/**
 * Download a file from a project. Returns raw bytes as a Blob.
 */
export async function downloadFile(
  projectId: string,
  fileId: string
): Promise<Blob> {
  const response = await fetch(
    `${API_V2}/projects/${projectId}/files/${fileId}`
  );
  if (!response.ok) {
    throw new ProjectApiError(
      `Download failed: ${response.status}`,
      response.status
    );
  }
  return response.blob();
}

/**
 * Delete a file from a project.
 */
export async function deleteFile(
  projectId: string,
  fileId: string
): Promise<void> {
  const response = await fetch(
    `${API_V2}/projects/${projectId}/files/${fileId}`,
    { method: "DELETE" }
  );
  await handleResponse(response);
}

// ── Legacy v2 endpoints (model-based, still used for spatial tree) ──

/**
 * Upload an IFC model to a project (legacy).
 */
export async function uploadModel(
  projectId: string,
  file: File
): Promise<ModelResponse> {
  const formData = new FormData();
  formData.append("ifc_file", file);

  const response = await fetch(`${API_V2}/projects/${projectId}/models`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<ModelResponse>(response);
}

/**
 * List all models in a project (legacy).
 */
export async function listModels(
  projectId: string
): Promise<{ projectId: string; models: ModelResponse[] }> {
  const response = await fetch(`${API_V2}/projects/${projectId}/models`);
  return handleResponse(response);
}

/**
 * Remove a model from a project (legacy).
 */
export async function removeModel(
  projectId: string,
  modelId: string
): Promise<void> {
  const response = await fetch(
    `${API_V2}/projects/${projectId}/models/${modelId}`,
    { method: "DELETE" }
  );
  await handleResponse(response);
}

/**
 * Get the spatial tree for a model.
 */
export async function getSpatialTree(modelId: string): Promise<SpatialNode> {
  const response = await fetch(`${API_V2}/models/${modelId}/spatial-tree`);
  return handleResponse<SpatialNode>(response);
}

/**
 * Get element properties by GlobalId.
 */
export async function getElementProperties(
  modelId: string,
  globalId: string
): Promise<ElementProperties> {
  const response = await fetch(
    `${API_V2}/models/${modelId}/elements/${encodeURIComponent(globalId)}/properties`
  );
  return handleResponse<ElementProperties>(response);
}

// ── .wefc envelope (cloud-bridge) ─────────────────────────────

/**
 * Read the .wefc envelope for a persistent project from the tenant
 * Nextcloud folder. Returns ``null`` when no envelope exists yet.
 */
export async function readProjectWefc(
  projectId: string
): Promise<Record<string, unknown> | null> {
  const response = await fetch(`${API_V2}/projects/${projectId}/wefc`);
  if (response.status === 404) {
    return null;
  }
  return handleResponse<Record<string, unknown>>(response);
}

/**
 * Write the .wefc envelope for a persistent project. The backend
 * persists the manifest in the tenant Nextcloud folder via WebDAV
 * and refreshes the project's ``updated_at`` timestamp.
 */
export async function saveProjectWefc(
  projectId: string,
  manifest: Record<string, unknown>
): Promise<void> {
  const response = await fetch(`${API_V2}/projects/${projectId}/wefc`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(manifest),
  });
  await handleResponse(response);
}
