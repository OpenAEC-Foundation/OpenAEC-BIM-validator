/**
 * Project and model types for the BIM platform.
 *
 * These types represent the core domain model:
 * - Projects contain multiple IFC models
 * - Models have spatial trees and element data
 * - SpatialNodes represent the IFC hierarchy
 */

/** Unique identifier for projects and models */
export type ProjectId = string;
export type ModelId = string;

/** Supported model file formats */
export type ModelFormat = "ifc" | "ifcx";

/** Model loading state */
export type ModelLoadState = "pending" | "loading" | "loaded" | "error";

/** A spatial tree node representing an IFC spatial element */
export interface SpatialNode {
  /** IFC GlobalId */
  globalId: string;
  /** Display name (IfcBuilding "Kantoor", etc.) */
  name: string;
  /** IFC entity type (IfcProject, IfcSite, IfcBuilding, IfcBuildingStorey) */
  type: string;
  /** Child nodes */
  children: SpatialNode[];
  /** Number of elements contained (direct + nested) */
  elementCount: number;
}

/** A loaded IFC model */
export interface ModelInfo {
  /** Unique model ID (server-assigned) */
  id: ModelId;
  /** Original filename */
  fileName: string;
  /** File size in bytes */
  fileSize: number;
  /** Detected format */
  format: ModelFormat;
  /** Loading state */
  loadState: ModelLoadState;
  /** Error message if loadState is 'error' */
  error?: string;
  /** Whether the model is visible in the 3D viewer */
  visible: boolean;
  /** Spatial hierarchy tree (populated after loading) */
  spatialTree?: SpatialNode;
  /** Internal engine model ID for fragment management */
  engineModelId?: string;
  /** Backend model ID (only set when uploaded via v2 project API) */
  backendModelId?: string;
}

/** A project containing one or more models */
export interface Project {
  /** Unique project ID */
  id: ProjectId;
  /** Project name */
  name: string;
  /** Creation timestamp */
  createdAt: string;
  /** Loaded models */
  models: ModelInfo[];
}

/** Element property set */
export interface PropertySet {
  /** Property set name (e.g., "Pset_WallCommon") */
  name: string;
  /** Key-value properties */
  properties: Record<string, string | number | boolean | null>;
}

/** Full element properties response */
export interface ElementProperties {
  /** IFC GlobalId */
  globalId: string;
  /** IFC entity type */
  entityType: string;
  /** Element name */
  name: string | null;
  /** Model ID this element belongs to */
  modelId: ModelId;
  /** Property sets */
  propertySets: PropertySet[];
  /** Type properties (from the type object) */
  typeProperties?: Record<string, string | number | boolean | null>;
  /** Material info */
  material?: string;
}

/** Right panel tab options */
export type RightPanelTab =
  | "properties"
  | "validation"
  | "clashes"
  | "bcf";
