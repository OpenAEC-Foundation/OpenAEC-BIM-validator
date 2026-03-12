/**
 * Project slice — manages projects and their models.
 *
 * Handles project creation, model upload tracking, and model metadata.
 * The actual file loading happens in the viewer engine; this slice
 * tracks the state and metadata.
 */

import type { StateCreator } from "zustand";
import type {
  ModelId,
  ModelInfo,
  ModelFormat,
  ModelLoadState,
  Project,
  SpatialNode,
} from "../../types/project";

/** Maximum number of models per project */
const MAX_MODELS_PER_PROJECT = 10;

export interface ProjectSlice {
  /** Current active project */
  project: Project | null;

  /** Create a new project */
  createProject: (name: string) => Project;

  /** Add a model to the current project */
  addModel: (file: File) => ModelInfo;

  /** Remove a model from the project */
  removeModel: (modelId: ModelId) => void;

  /** Update model load state */
  updateModelLoadState: (
    modelId: ModelId,
    state: ModelLoadState,
    error?: string
  ) => void;

  /** Set the spatial tree for a model */
  setModelSpatialTree: (modelId: ModelId, tree: SpatialNode) => void;

  /** Toggle model visibility */
  toggleModelVisibility: (modelId: ModelId) => void;

  /** Set engine model ID after loading */
  setEngineModelId: (modelId: ModelId, engineModelId: string) => void;

  /** Get a model by ID */
  getModel: (modelId: ModelId) => ModelInfo | undefined;
}

/** Detect file format from extension */
function detectFormat(fileName: string): ModelFormat {
  if (fileName.toLowerCase().endsWith(".ifcx")) return "ifcx";
  return "ifc";
}

export const createProjectSlice: StateCreator<ProjectSlice> = (set, get) => ({
  project: null,

  createProject: (name: string) => {
    const project: Project = {
      id: crypto.randomUUID(),
      name,
      createdAt: new Date().toISOString(),
      models: [],
    };
    set({ project });
    return project;
  },

  addModel: (file: File) => {
    const { project } = get();
    if (!project) {
      throw new Error("No active project. Create a project first.");
    }
    if (project.models.length >= MAX_MODELS_PER_PROJECT) {
      throw new Error(
        `Maximum ${MAX_MODELS_PER_PROJECT} models per project.`
      );
    }

    const model: ModelInfo = {
      id: crypto.randomUUID(),
      fileName: file.name,
      fileSize: file.size,
      format: detectFormat(file.name),
      loadState: "pending",
      visible: true,
    };

    set({
      project: {
        ...project,
        models: [...project.models, model],
      },
    });

    return model;
  },

  removeModel: (modelId: ModelId) => {
    const { project } = get();
    if (!project) return;

    set({
      project: {
        ...project,
        models: project.models.filter((m) => m.id !== modelId),
      },
    });
  },

  updateModelLoadState: (
    modelId: ModelId,
    state: ModelLoadState,
    error?: string
  ) => {
    const { project } = get();
    if (!project) return;

    set({
      project: {
        ...project,
        models: project.models.map((m) =>
          m.id === modelId ? { ...m, loadState: state, error } : m
        ),
      },
    });
  },

  setModelSpatialTree: (modelId: ModelId, tree: SpatialNode) => {
    const { project } = get();
    if (!project) return;

    set({
      project: {
        ...project,
        models: project.models.map((m) =>
          m.id === modelId ? { ...m, spatialTree: tree } : m
        ),
      },
    });
  },

  toggleModelVisibility: (modelId: ModelId) => {
    const { project } = get();
    if (!project) return;

    set({
      project: {
        ...project,
        models: project.models.map((m) =>
          m.id === modelId ? { ...m, visible: !m.visible } : m
        ),
      },
    });
  },

  setEngineModelId: (modelId: ModelId, engineModelId: string) => {
    const { project } = get();
    if (!project) return;

    set({
      project: {
        ...project,
        models: project.models.map((m) =>
          m.id === modelId ? { ...m, engineModelId } : m
        ),
      },
    });
  },

  getModel: (modelId: ModelId) => {
    const { project } = get();
    return project?.models.find((m) => m.id === modelId);
  },
});
