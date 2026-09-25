/**
 * API client for the Nextcloud cloud storage endpoints.
 *
 * All calls proxy through the FastAPI backend — the browser
 * never talks to Nextcloud directly.
 */

import { ApiError } from "./client";

const CLOUD_BASE = "/api/cloud";

/** Parse error detail from a JSON error response. */
async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return data.detail || data.message || `Request failed (${response.status})`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

// ── Types ──────────────────────────────────────────────────────

export interface CloudStatus {
  enabled: boolean;
  connected: boolean;
}

export interface CloudProject {
  name: string;
  last_modified: string;
}

export interface CloudFile {
  name: string;
  size: number;
  last_modified: string;
}

// ── API functions ──────────────────────────────────────────────

/** Check if cloud storage is enabled and reachable. */
export async function cloudStatus(): Promise<CloudStatus> {
  let response: Response;
  try {
    response = await fetch(`${CLOUD_BASE}/status`);
  } catch (error) {
    throw new ApiError(
      "Network error: unable to check cloud status.",
      undefined,
      error instanceof Error ? error.message : "Unknown network error",
    );
  }

  if (!response.ok) {
    const msg = await parseError(response);
    throw new ApiError(msg, response.status, msg);
  }

  return response.json();
}

/** List project folders in Nextcloud. */
export async function cloudListProjects(): Promise<CloudProject[]> {
  let response: Response;
  try {
    response = await fetch(`${CLOUD_BASE}/projects`);
  } catch (error) {
    throw new ApiError(
      "Network error: unable to list cloud projects.",
      undefined,
      error instanceof Error ? error.message : "Unknown network error",
    );
  }

  if (!response.ok) {
    const msg = await parseError(response);
    throw new ApiError(msg, response.status, msg);
  }

  const data = await response.json();
  return data.projects;
}

/** List files in a project's tool subdirectory. */
export async function cloudListFiles(
  project: string,
  category: "bim" | "output" = "bim",
): Promise<CloudFile[]> {
  let response: Response;
  try {
    response = await fetch(
      `${CLOUD_BASE}/projects/${encodeURIComponent(project)}/files?category=${category}`,
    );
  } catch (error) {
    throw new ApiError(
      "Network error: unable to list cloud files.",
      undefined,
      error instanceof Error ? error.message : "Unknown network error",
    );
  }

  if (!response.ok) {
    const msg = await parseError(response);
    throw new ApiError(msg, response.status, msg);
  }

  const data = await response.json();
  return data.files;
}

/** Download a file from the cloud. Returns raw bytes as a Blob. */
export async function cloudDownloadFile(
  project: string,
  filename: string,
  category: "bim" | "output" = "bim",
): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(
      `${CLOUD_BASE}/projects/${encodeURIComponent(project)}/files/${encodeURIComponent(filename)}?category=${category}`,
    );
  } catch (error) {
    throw new ApiError(
      "Network error: unable to download cloud file.",
      undefined,
      error instanceof Error ? error.message : "Unknown network error",
    );
  }

  if (!response.ok) {
    const msg = await parseError(response);
    throw new ApiError(msg, response.status, msg);
  }

  return response.blob();
}

/** Upload a file to the cloud. */
export async function cloudUploadFile(
  project: string,
  filename: string,
  blob: Blob,
  category: "bim" | "output" = "output",
): Promise<void> {
  const formData = new FormData();
  formData.append("file", blob, filename);

  let response: Response;
  try {
    response = await fetch(
      `${CLOUD_BASE}/projects/${encodeURIComponent(project)}/files/${encodeURIComponent(filename)}?category=${category}`,
      { method: "PUT", body: formData },
    );
  } catch (error) {
    throw new ApiError(
      "Network error: unable to upload cloud file.",
      undefined,
      error instanceof Error ? error.message : "Unknown network error",
    );
  }

  if (!response.ok) {
    const msg = await parseError(response);
    throw new ApiError(msg, response.status, msg);
  }
}

/** Read a specific .wefc manifest from the cloud. */
export async function cloudReadManifest(
  project: string,
  name: string = "project.wefc",
): Promise<Record<string, unknown>> {
  let response: Response;
  try {
    response = await fetch(
      `${CLOUD_BASE}/projects/${encodeURIComponent(project)}/manifests/${encodeURIComponent(name)}`,
    );
  } catch (error) {
    throw new ApiError(
      "Network error: unable to read manifest.",
      undefined,
      error instanceof Error ? error.message : "Unknown network error",
    );
  }

  if (!response.ok) {
    const msg = await parseError(response);
    throw new ApiError(msg, response.status, msg);
  }

  return response.json();
}

/** Save a project.wefc manifest to the cloud. */
export async function cloudSaveManifest(
  project: string,
  manifest: Record<string, unknown>,
  name: string = "project.wefc",
): Promise<void> {
  // Use the backward-compat endpoint for default name,
  // or the new multi-manifest endpoint for custom names
  const url =
    name === "project.wefc"
      ? `${CLOUD_BASE}/projects/${encodeURIComponent(project)}/manifest`
      : `${CLOUD_BASE}/projects/${encodeURIComponent(project)}/manifests/${encodeURIComponent(name)}`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(manifest),
    });
  } catch (error) {
    throw new ApiError(
      "Network error: unable to save manifest.",
      undefined,
      error instanceof Error ? error.message : "Unknown network error",
    );
  }

  if (!response.ok) {
    const msg = await parseError(response);
    throw new ApiError(msg, response.status, msg);
  }
}

/** Delete a file from the cloud. */
export async function cloudDeleteFile(
  project: string,
  filename: string,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(
      `${CLOUD_BASE}/projects/${encodeURIComponent(project)}/files/${encodeURIComponent(filename)}`,
      { method: "DELETE" },
    );
  } catch (error) {
    throw new ApiError(
      "Network error: unable to delete cloud file.",
      undefined,
      error instanceof Error ? error.message : "Unknown network error",
    );
  }

  if (!response.ok) {
    const msg = await parseError(response);
    throw new ApiError(msg, response.status, msg);
  }
}
