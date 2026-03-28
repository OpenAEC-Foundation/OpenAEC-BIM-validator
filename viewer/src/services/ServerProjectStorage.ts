/**
 * Server-backed project storage.
 *
 * Communicates with the FastAPI backend for all project and file
 * operations. Files are stored on the server's disk.
 */

import type {
  FileType,
  IProjectStorage,
  ProjectDetail,
  ProjectFileInfo,
  ProjectSummary,
} from "./ProjectStorage";
import {
  listProjects as apiListProjects,
  getProject as apiGetProject,
  createProject as apiCreateProject,
  updateProject as apiUpdateProject,
  deleteProject as apiDeleteProject,
  uploadFile as apiUploadFile,
  deleteFile as apiDeleteFile,
  downloadFile as apiDownloadFile,
} from "../api/projectApi";

export class ServerProjectStorage implements IProjectStorage {
  readonly mode = "server" as const;

  async listProjects(): Promise<ProjectSummary[]> {
    return apiListProjects();
  }

  async getProject(id: string): Promise<ProjectDetail> {
    const resp = await apiGetProject(id);
    return {
      id: resp.id,
      name: resp.name,
      description: resp.description,
      createdAt: resp.createdAt,
      updatedAt: resp.updatedAt,
      files: resp.files.map((f) => ({
        id: f.id,
        projectId: f.projectId,
        fileType: f.fileType,
        fileName: f.fileName,
        fileSize: f.fileSize,
        uploadedAt: f.uploadedAt,
      })),
    };
  }

  async createProject(
    name: string,
    description?: string
  ): Promise<ProjectDetail> {
    const resp = await apiCreateProject(name, description);
    return {
      id: resp.id,
      name: resp.name,
      description: resp.description,
      createdAt: resp.createdAt,
      updatedAt: resp.updatedAt,
      files: resp.files.map((f) => ({
        id: f.id,
        projectId: f.projectId,
        fileType: f.fileType,
        fileName: f.fileName,
        fileSize: f.fileSize,
        uploadedAt: f.uploadedAt,
      })),
    };
  }

  async updateProject(
    id: string,
    data: { name?: string; description?: string }
  ): Promise<ProjectDetail> {
    const resp = await apiUpdateProject(id, data);
    return {
      id: resp.id,
      name: resp.name,
      description: resp.description,
      createdAt: resp.createdAt,
      updatedAt: resp.updatedAt,
      files: resp.files.map((f) => ({
        id: f.id,
        projectId: f.projectId,
        fileType: f.fileType,
        fileName: f.fileName,
        fileSize: f.fileSize,
        uploadedAt: f.uploadedAt,
      })),
    };
  }

  async deleteProject(id: string): Promise<void> {
    await apiDeleteProject(id);
  }

  async addFile(
    projectId: string,
    file: File,
    type: FileType
  ): Promise<ProjectFileInfo> {
    const resp = await apiUploadFile(projectId, file, type);
    return {
      id: resp.id,
      projectId: resp.projectId,
      fileType: resp.fileType,
      fileName: resp.fileName,
      fileSize: resp.fileSize,
      uploadedAt: resp.uploadedAt,
    };
  }

  async removeFile(projectId: string, fileId: string): Promise<void> {
    await apiDeleteFile(projectId, fileId);
  }

  async getFileBlob(projectId: string, fileId: string): Promise<Blob> {
    return apiDownloadFile(projectId, fileId);
  }
}
