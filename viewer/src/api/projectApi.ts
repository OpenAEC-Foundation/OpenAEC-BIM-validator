/**
 * Project API client — v2 endpoints for multi-model BIM platform.
 *
 * Provides functions for project management, model upload,
 * spatial tree retrieval, and element property queries.
 */

import type { SpatialNode, ElementProperties } from "../types/project";

/** Base URL for v2 API endpoints */
const API_V2 = "/api/v2";

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

/** Project response from API */
export interface ProjectResponse {
  id: string;
  name: string;
  createdAt: string;
  models: ModelResponse[];
}

/** Model response from API */
export interface ModelResponse {
  id: string;
  fileName: string;
  fileSize: number;
  format: string;
  loadedAt?: string;
  hasSpatialTree: boolean;
}

/**
 * Create a new project.
 */
export async function createProject(name: string): Promise<ProjectResponse> {
  const formData = new FormData();
  formData.append("name", name);

  const response = await fetch(`${API_V2}/projects`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<ProjectResponse>(response);
}

/**
 * Upload an IFC model to a project.
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
 * List all models in a project.
 */
export async function listModels(
  projectId: string
): Promise<{ projectId: string; models: ModelResponse[] }> {
  const response = await fetch(`${API_V2}/projects/${projectId}/models`);
  return handleResponse(response);
}

/**
 * Remove a model from a project.
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
export async function getSpatialTree(
  modelId: string
): Promise<SpatialNode> {
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
