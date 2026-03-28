/**
 * Project storage adapter interface.
 *
 * Abstracts project management operations so the app can work with
 * both a remote server (ServerProjectStorage) and local files
 * (LocalProjectStorage) using the same interface.
 */

export type FileType = "ifc" | "bcf" | "ids";

export interface ProjectSummary {
  id: string;
  name: string;
  description: string | null;
  createdAt: string;
  updatedAt: string;
  fileCount: number;
}

export interface ProjectFileInfo {
  id: string;
  projectId: string;
  fileType: FileType;
  fileName: string;
  fileSize: number;
  uploadedAt: string;
}

export interface ProjectDetail {
  id: string;
  name: string;
  description: string | null;
  createdAt: string;
  updatedAt: string;
  files: ProjectFileInfo[];
}

/**
 * Storage adapter interface for project operations.
 *
 * Implementations:
 * - ServerProjectStorage: Communicates with the FastAPI backend
 * - LocalProjectStorage: Uses File System Access API + .bvp files
 */
export interface IProjectStorage {
  /** Unique identifier for this storage backend */
  readonly mode: "server" | "local";

  /** List all available projects */
  listProjects(): Promise<ProjectSummary[]>;

  /** Get full project details including file list */
  getProject(id: string): Promise<ProjectDetail>;

  /** Create a new project */
  createProject(
    name: string,
    description?: string
  ): Promise<ProjectDetail>;

  /** Update project metadata */
  updateProject(
    id: string,
    data: { name?: string; description?: string }
  ): Promise<ProjectDetail>;

  /** Delete a project and all its files */
  deleteProject(id: string): Promise<void>;

  /** Add a file to a project */
  addFile(
    projectId: string,
    file: File,
    type: FileType
  ): Promise<ProjectFileInfo>;

  /** Remove a file from a project */
  removeFile(projectId: string, fileId: string): Promise<void>;

  /** Get file content as a Blob (for loading into viewer) */
  getFileBlob(projectId: string, fileId: string): Promise<Blob>;
}
