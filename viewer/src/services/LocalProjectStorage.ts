/**
 * Local project storage using File System Access API.
 *
 * Projects are stored as .bvp JSON files on the user's filesystem.
 * IFC/BCF/IDS files are referenced by relative paths from the .bvp
 * file location.
 *
 * Falls back to file input/download for browsers without FSAA support.
 */

import type {
  FileType,
  IProjectStorage,
  ProjectDetail,
  ProjectFileInfo,
  ProjectSummary,
} from "./ProjectStorage";
import {
  type BvpProject,
  createEmptyBvp,
  parseBvp,
  serializeBvp,
} from "./bvpFormat";

/** Check if File System Access API is available */
export function hasFileSystemAccess(): boolean {
  return "showDirectoryPicker" in window;
}

/**
 * In-memory registry of opened local projects.
 * Maps project ID to its directory handle and parsed .bvp data.
 */
interface LocalProjectEntry {
  id: string;
  dirHandle: FileSystemDirectoryHandle;
  bvp: BvpProject;
  bvpFileName: string;
}

const openProjects = new Map<string, LocalProjectEntry>();

/** Find the .bvp file in a directory */
async function findBvpFile(
  dirHandle: FileSystemDirectoryHandle
): Promise<{ handle: FileSystemFileHandle; name: string } | null> {
  // Use values() iterator which is more widely typed
  for await (const entry of (dirHandle as any).values()) {
    const name = entry.name as string;
    if (entry.kind === "file" && name.endsWith(".bvp")) {
      return { handle: entry as FileSystemFileHandle, name };
    }
  }
  return null;
}

/** Read and parse a .bvp file from a file handle */
async function readBvpFile(
  fileHandle: FileSystemFileHandle
): Promise<BvpProject> {
  const file = await fileHandle.getFile();
  const text = await file.text();
  return parseBvp(text);
}

/** Write .bvp file back to disk */
async function writeBvpFile(
  dirHandle: FileSystemDirectoryHandle,
  fileName: string,
  bvp: BvpProject
): Promise<void> {
  const fileHandle = await dirHandle.getFileHandle(fileName, { create: true });
  const writable = await fileHandle.createWritable();
  await writable.write(serializeBvp(bvp));
  await writable.close();
}

/** Resolve a relative file path to a Blob via directory handle */
async function resolveFile(
  dirHandle: FileSystemDirectoryHandle,
  relativePath: string
): Promise<File> {
  // Normalize path: remove leading ./ and split on /
  const parts = relativePath
    .replace(/^\.\//, "")
    .split("/")
    .filter(Boolean);

  if (parts.length === 0) {
    throw new Error(`Invalid path: ${relativePath}`);
  }

  let current: FileSystemDirectoryHandle = dirHandle;

  // Navigate subdirectories
  for (let i = 0; i < parts.length - 1; i++) {
    current = await current.getDirectoryHandle(parts[i]!);
  }

  const fileHandle = await current.getFileHandle(parts[parts.length - 1]!);
  return fileHandle.getFile();
}

function entryToDetail(entry: LocalProjectEntry): ProjectDetail {
  return {
    id: entry.id,
    name: entry.bvp.name,
    description: entry.bvp.description,
    createdAt: entry.bvp.created,
    updatedAt: entry.bvp.updated,
    files: entry.bvp.files.map((f) => ({
      id: f.id,
      projectId: entry.id,
      fileType: f.type,
      fileName: f.name,
      fileSize: f.size,
      uploadedAt: entry.bvp.updated,
    })),
  };
}

export class LocalProjectStorage implements IProjectStorage {
  readonly mode = "local" as const;

  async listProjects(): Promise<ProjectSummary[]> {
    return Array.from(openProjects.values()).map((entry) => ({
      id: entry.id,
      name: entry.bvp.name,
      description: entry.bvp.description,
      createdAt: entry.bvp.created,
      updatedAt: entry.bvp.updated,
      fileCount: entry.bvp.files.length,
    }));
  }

  async getProject(id: string): Promise<ProjectDetail> {
    const entry = openProjects.get(id);
    if (!entry) throw new Error(`Local project not found: ${id}`);
    return entryToDetail(entry);
  }

  /**
   * Create a new local project.
   * Opens a directory picker, creates a .bvp file in it.
   */
  async createProject(
    name: string,
    description?: string
  ): Promise<ProjectDetail> {
    if (!hasFileSystemAccess()) {
      throw new Error(
        "File System Access API not available. Use Chrome or Edge."
      );
    }

    const dirHandle = await (window as any).showDirectoryPicker({
      mode: "readwrite",
    });

    const bvp = createEmptyBvp(name, description);
    const bvpFileName = `${name.replace(/[^a-zA-Z0-9_-]/g, "_")}.bvp`;

    await writeBvpFile(dirHandle, bvpFileName, bvp);

    const id = crypto.randomUUID();
    const entry: LocalProjectEntry = { id, dirHandle, bvp, bvpFileName };
    openProjects.set(id, entry);

    return entryToDetail(entry);
  }

  async updateProject(
    id: string,
    data: { name?: string; description?: string }
  ): Promise<ProjectDetail> {
    const entry = openProjects.get(id);
    if (!entry) throw new Error(`Local project not found: ${id}`);

    if (data.name !== undefined) entry.bvp.name = data.name;
    if (data.description !== undefined)
      entry.bvp.description = data.description;

    await writeBvpFile(entry.dirHandle, entry.bvpFileName, entry.bvp);
    return entryToDetail(entry);
  }

  async deleteProject(id: string): Promise<void> {
    openProjects.delete(id);
  }

  /**
   * Add a file to the project.
   * The file is expected to already be in the project directory.
   * We just register it in the .bvp file.
   */
  async addFile(
    projectId: string,
    file: File,
    type: FileType
  ): Promise<ProjectFileInfo> {
    const entry = openProjects.get(projectId);
    if (!entry) throw new Error(`Local project not found: ${projectId}`);

    const fileId = crypto.randomUUID();
    const relativePath = `./${file.name}`;

    entry.bvp.files.push({
      id: fileId,
      type,
      path: relativePath,
      name: file.name,
      size: file.size,
    });

    await writeBvpFile(entry.dirHandle, entry.bvpFileName, entry.bvp);

    return {
      id: fileId,
      projectId,
      fileType: type,
      fileName: file.name,
      fileSize: file.size,
      uploadedAt: new Date().toISOString(),
    };
  }

  async removeFile(projectId: string, fileId: string): Promise<void> {
    const entry = openProjects.get(projectId);
    if (!entry) throw new Error(`Local project not found: ${projectId}`);

    entry.bvp.files = entry.bvp.files.filter((f) => f.id !== fileId);
    await writeBvpFile(entry.dirHandle, entry.bvpFileName, entry.bvp);
  }

  async getFileBlob(projectId: string, fileId: string): Promise<Blob> {
    const entry = openProjects.get(projectId);
    if (!entry) throw new Error(`Local project not found: ${projectId}`);

    const fileEntry = entry.bvp.files.find((f) => f.id === fileId);
    if (!fileEntry) throw new Error(`File not found: ${fileId}`);

    return resolveFile(entry.dirHandle, fileEntry.path);
  }

  /**
   * Open an existing local project folder.
   * Looks for a .bvp file in the selected directory.
   */
  async openProjectFolder(): Promise<ProjectDetail> {
    if (!hasFileSystemAccess()) {
      throw new Error(
        "File System Access API not available. Use Chrome or Edge."
      );
    }

    const dirHandle = await (window as any).showDirectoryPicker({
      mode: "readwrite",
    });

    const bvpResult = await findBvpFile(dirHandle);
    if (!bvpResult) {
      throw new Error(
        "No .bvp project file found in this directory."
      );
    }

    const bvp = await readBvpFile(bvpResult.handle);
    const id = crypto.randomUUID();
    const entry: LocalProjectEntry = {
      id,
      dirHandle,
      bvp,
      bvpFileName: bvpResult.name,
    };
    openProjects.set(id, entry);

    return entryToDetail(entry);
  }
}
