/**
 * BCF Platform API client.
 *
 * Communicates with the OpenAEC BCF Platform (bcf.open-aec.com)
 * using the BCF 2.1 REST API. No authentication required in Fase 1.
 *
 * All functions throw on network/server errors with descriptive messages.
 */

import type { BcfIssue, IssueType, IssuePriority } from "../types/bcf";

// ─── Configuration ────────────────────────────────────────────────

const BCF_PLATFORM_URL = "https://bcf.open-aec.com";

// ─── API Response Types ───────────────────────────────────────────

export interface PlatformProject {
  project_id: string;
  name: string;
  description?: string;
}

interface TopicResponse {
  guid: string;
  title: string;
  topic_status: string;
  topic_type: string;
  priority: string;
}

interface CommentResponse {
  guid: string;
  comment: string;
  author: string;
}

// ─── API Request Types ────────────────────────────────────────────

interface CreateProjectRequest {
  name: string;
  description?: string;
}

interface CreateTopicRequest {
  title: string;
  description?: string;
  topic_type?: string;
  topic_status?: string;
  priority?: string;
  labels?: string[];
  due_date?: string;
  index?: number;
}

interface CreateCommentRequest {
  comment: string;
  viewpoint_guid?: string;
}

// ─── Mapping helpers ──────────────────────────────────────────────

const ISSUE_TYPE_MAP: Record<IssueType, string> = {
  Error: "Error",
  Warning: "Warning",
  Info: "Information",
  Clash: "Clash",
  Comment: "Comment",
  Request: "Request",
};

const PRIORITY_MAP: Record<IssuePriority, string> = {
  Critical: "Critical",
  High: "Major",
  Normal: "Normal",
  Low: "Minor",
};

// ─── HTTP helpers ─────────────────────────────────────────────────

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BCF_PLATFORM_URL}${path}`, {
    method: "GET",
    headers: { "Accept": "application/json" },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`BCF API GET ${path} failed (${res.status}): ${text}`);
  }
  return res.json() as Promise<T>;
}

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BCF_PLATFORM_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`BCF API POST ${path} failed (${res.status}): ${text}`);
  }
  return res.json() as Promise<T>;
}

// ─── Public API ───────────────────────────────────────────────────

/** List all projects on the BCF platform. */
export async function listProjects(): Promise<PlatformProject[]> {
  return apiGet<PlatformProject[]>("/bcf/2.1/projects");
}

/** Create a new project on the BCF platform. */
export async function createProject(
  name: string,
  description?: string
): Promise<PlatformProject> {
  const body: CreateProjectRequest = { name, description };
  return apiPost<PlatformProject>("/bcf/2.1/projects", body);
}

/** Create a topic (issue) in a project. */
export async function createTopic(
  projectId: string,
  topic: CreateTopicRequest
): Promise<TopicResponse> {
  return apiPost<TopicResponse>(
    `/bcf/2.1/projects/${projectId}/topics`,
    topic
  );
}

/** Add a comment to a topic. */
export async function createComment(
  projectId: string,
  topicGuid: string,
  comment: string,
  viewpointGuid?: string
): Promise<CommentResponse> {
  const body: CreateCommentRequest = { comment, viewpoint_guid: viewpointGuid };
  return apiPost<CommentResponse>(
    `/bcf/2.1/projects/${projectId}/topics/${topicGuid}/comments`,
    body
  );
}

// ─── Bulk sync ────────────────────────────────────────────────────

export interface SyncProgress {
  current: number;
  total: number;
  title: string;
}

/**
 * Sync all BCF issues to the platform as topics + comments.
 *
 * Creates one topic per issue, with the issue description as
 * the first comment. Reports progress via callback.
 *
 * @returns Number of successfully synced issues.
 */
export async function syncIssuesToPlatform(
  projectId: string,
  issues: BcfIssue[],
  onProgress?: (progress: SyncProgress) => void
): Promise<number> {
  let synced = 0;

  for (const [i, issue] of issues.entries()) {
    onProgress?.({
      current: i + 1,
      total: issues.length,
      title: issue.title,
    });

    try {
      const topicReq: CreateTopicRequest = {
        title: issue.title,
        description: issue.description,
        topic_type: ISSUE_TYPE_MAP[issue.type] ?? "Error",
        topic_status: issue.status,
        priority: PRIORITY_MAP[issue.priority] ?? "Normal",
        labels: issue.labels,
        due_date: issue.dueDate,
        index: issue.index,
      };

      const topic = await createTopic(projectId, topicReq);

      // Add each comment
      for (const comment of issue.comments) {
        await createComment(
          projectId,
          topic.guid,
          comment.comment,
          comment.viewpointGuid
        );
      }

      synced++;
    } catch (err) {
      console.error(`Failed to sync issue "${issue.title}":`, err);
    }
  }

  return synced;
}
