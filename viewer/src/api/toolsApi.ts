/**
 * API client for the model tools: optimizer, clash detection and
 * data-quality checks. All three follow the backend job/report patterns
 * introduced alongside /api/v1/validate.
 */

import { API_ORIGIN } from "./apiBase";

const BASE = `${API_ORIGIN}/api/v1`;

// -- Shared -----------------------------------------------------------------

/** Poll a job endpoint until it completes or fails. */
async function pollJob<T>(
  url: string,
  intervalMs = 1000,
  timeoutMs = 10 * 60 * 1000
): Promise<T> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const resp = await fetch(url);
    if (!resp.ok) {
      throw new Error(`Job poll failed: ${resp.status}`);
    }
    const body = await resp.json();
    if (body.status === "completed") return body as T;
    if (body.status === "failed") {
      throw new Error(body.error || "Job failed");
    }
    if (Date.now() > deadline) throw new Error("Job timed out");
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

async function startJob(url: string, form: FormData): Promise<string> {
  const resp = await fetch(url, { method: "POST", body: form });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => null);
    throw new Error(detail?.detail || `Request failed: ${resp.status}`);
  }
  const body = await resp.json();
  return body.job_id as string;
}

type ByteSource = ArrayBuffer | Uint8Array;

function toFile(bytes: ByteSource, fileName: string): File {
  // Copy into a fresh ArrayBuffer so SharedArrayBuffer-backed views are
  // also accepted by the File constructor
  const copy = bytes instanceof Uint8Array ? new Uint8Array(bytes) : new Uint8Array(bytes.slice(0));
  return new File([copy], fileName, { type: "application/octet-stream" });
}

// -- Optimizer ----------------------------------------------------------------

export interface OptimizePassInfo {
  name: string;
  title: string;
  description: string;
}

export interface OptimizePassResult {
  name: string;
  changed: number;
  details: Record<string, unknown>[];
  details_omitted: number;
}

export interface OptimizeReport {
  input_file: string;
  output_file: string;
  ifc_schema: string;
  size_before: number;
  size_after: number;
  passes: OptimizePassResult[];
}

export async function listOptimizePasses(): Promise<OptimizePassInfo[]> {
  const resp = await fetch(`${BASE}/optimize/passes`);
  if (!resp.ok) throw new Error(`Failed to list passes: ${resp.status}`);
  return (await resp.json()).passes as OptimizePassInfo[];
}

export interface OptimizeJobResult {
  jobId: string;
  report: OptimizeReport;
  downloadUrl: string;
}

export async function runOptimize(
  bytes: ByteSource,
  fileName: string,
  passes: string[]
): Promise<OptimizeJobResult> {
  const form = new FormData();
  form.append("ifc_file", toFile(bytes, fileName));
  form.append("passes", passes.join(","));
  const jobId = await startJob(`${BASE}/optimize`, form);
  const body = await pollJob<{
    report: OptimizeReport;
    download_url: string;
  }>(`${BASE}/optimize/jobs/${jobId}`);
  return {
    jobId,
    report: body.report,
    downloadUrl: `${API_ORIGIN}${body.download_url}`,
  };
}

// -- Clash detection ----------------------------------------------------------

export interface ClashItem {
  a_global_id: string;
  b_global_id: string;
  a_ifc_class: string;
  b_ifc_class: string;
  a_name: string;
  b_name: string;
  type: string;
  position: number[];
  distance: number | null;
}

export interface ClashResultBody {
  mode: string;
  clash_count: number;
  clashes: ClashItem[];
  results_omitted: number;
}

export async function runClash(
  modelA: { bytes: ByteSource; fileName: string },
  modelB: { bytes: ByteSource; fileName: string } | null,
  mode: "intersection" | "clearance" = "intersection"
): Promise<ClashResultBody> {
  const form = new FormData();
  form.append("ifc_a", toFile(modelA.bytes, modelA.fileName));
  if (modelB) {
    form.append("ifc_b", toFile(modelB.bytes, modelB.fileName));
  }
  form.append("mode", mode);
  const jobId = await startJob(`${BASE}/clash`, form);
  const body = await pollJob<{ result: ClashResultBody }>(
    `${BASE}/clash/jobs/${jobId}`
  );
  return body.result;
}

// -- Data-quality checks --------------------------------------------------------

export interface QualityFinding {
  entity_type: string;
  entity_name: string | null;
  global_id: string | null;
  message: string;
}

export interface QualityCheckResult {
  id: string;
  title: string;
  severity: "error" | "warning" | "info";
  passed: boolean;
  finding_count: number;
  findings: QualityFinding[];
  findings_omitted: number;
}

export interface QualityReport {
  ifc_file: string;
  ifc_schema: string;
  checks: QualityCheckResult[];
  error_count: number;
  warning_count: number;
}

export async function runQualityChecks(
  bytes: ByteSource,
  fileName: string
): Promise<QualityReport> {
  const form = new FormData();
  form.append("ifc_file", toFile(bytes, fileName));
  const resp = await fetch(`${BASE}/quality`, { method: "POST", body: form });
  if (!resp.ok) {
    const detail = await resp.json().catch(() => null);
    throw new Error(detail?.detail || `Quality check failed: ${resp.status}`);
  }
  return (await resp.json()) as QualityReport;
}
