/**
 * Lightweight fetch-based client for the OpenAEC BCF Platform API.
 * Talks to /bcf/2.1/ endpoints with Bearer token authentication.
 *
 * Works with both API keys (bcfk_...) and OIDC access tokens.
 */

import type {
  BcfApiConfig,
  BcfProject,
  BcfTopic,
  CreateProjectRequest,
  CreateTopicRequest,
  BcfComment,
  CreateCommentRequest,
  BcfViewpoint,
  CreateViewpointRequest,
} from "../types/bcfPlatform";

export class BcfPlatformError extends Error {
  constructor(
    public statusCode: number,
    public detail: string,
  ) {
    super(`BCF Platform error ${statusCode}: ${detail}`);
    this.name = "BcfPlatformError";
  }
}

function normalizeUrl(url: string): string {
  return url.replace(/\/+$/, "");
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { error?: string };
      if (body.error) detail = body.error;
    } catch {
      // keep statusText
    }
    throw new BcfPlatformError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export function createBcfPlatformApi(config: BcfApiConfig) {
  const base = normalizeUrl(config.url);

  function headers(): HeadersInit {
    return {
      Authorization: `Bearer ${config.token}`,
      "Content-Type": "application/json",
    };
  }

  function bcfUrl(path: string): string {
    return `${base}/bcf/2.1${path}`;
  }

  return {
    // ── Connection test ───────────────────────────────────

    async testConnection(): Promise<boolean> {
      try {
        const res = await fetch(`${base}/health`, {
          headers: { Authorization: `Bearer ${config.token}` },
        });
        return res.ok;
      } catch {
        return false;
      }
    },

    // ── Projects ──────────────────────────────────────────

    async listProjects(): Promise<BcfProject[]> {
      const res = await fetch(bcfUrl("/projects"), { headers: headers() });
      return handleResponse<BcfProject[]>(res);
    },

    async getProject(projectId: string): Promise<BcfProject> {
      const res = await fetch(bcfUrl(`/projects/${projectId}`), {
        headers: headers(),
      });
      return handleResponse<BcfProject>(res);
    },

    async createProject(data: CreateProjectRequest): Promise<BcfProject> {
      const res = await fetch(bcfUrl("/projects"), {
        method: "POST",
        headers: headers(),
        body: JSON.stringify(data),
      });
      return handleResponse<BcfProject>(res);
    },

    // ── Topics ────────────────────────────────────────────

    async listTopics(projectId: string): Promise<BcfTopic[]> {
      const res = await fetch(bcfUrl(`/projects/${projectId}/topics`), {
        headers: headers(),
      });
      return handleResponse<BcfTopic[]>(res);
    },

    async createTopic(
      projectId: string,
      data: CreateTopicRequest,
    ): Promise<BcfTopic> {
      const res = await fetch(bcfUrl(`/projects/${projectId}/topics`), {
        method: "POST",
        headers: headers(),
        body: JSON.stringify(data),
      });
      return handleResponse<BcfTopic>(res);
    },

    // ── Comments ──────────────────────────────────────────

    async createComment(
      projectId: string,
      topicId: string,
      data: CreateCommentRequest,
    ): Promise<BcfComment> {
      const res = await fetch(
        bcfUrl(`/projects/${projectId}/topics/${topicId}/comments`),
        {
          method: "POST",
          headers: headers(),
          body: JSON.stringify(data),
        },
      );
      return handleResponse<BcfComment>(res);
    },

    // ── Viewpoints ────────────────────────────────────────

    async createViewpoint(
      projectId: string,
      topicId: string,
      data: CreateViewpointRequest,
    ): Promise<BcfViewpoint> {
      const res = await fetch(
        bcfUrl(`/projects/${projectId}/topics/${topicId}/viewpoints`),
        {
          method: "POST",
          headers: headers(),
          body: JSON.stringify(data),
        },
      );
      return handleResponse<BcfViewpoint>(res);
    },
  };
}

export type BcfPlatformApi = ReturnType<typeof createBcfPlatformApi>;
