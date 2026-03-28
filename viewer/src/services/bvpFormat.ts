/**
 * BVP (BIM Validator Project) file format — .bvp
 *
 * A JSON file that references local IFC, BCF, and IDS files
 * relative to its own location. Used for local project management
 * without a server.
 */

export interface BvpFileEntry {
  id: string;
  type: "ifc" | "bcf" | "ids";
  /** Relative path from .bvp file location */
  path: string;
  name: string;
  size: number;
}

export interface BvpProject {
  version: "1.0";
  name: string;
  description: string | null;
  created: string;
  updated: string;
  files: BvpFileEntry[];
  settings?: {
    idsFile?: string;
  };
}

/** Parse a .bvp JSON string into a BvpProject */
export function parseBvp(json: string): BvpProject {
  const data = JSON.parse(json);

  if (!data.version || !data.name) {
    throw new Error("Invalid .bvp file: missing version or name");
  }

  return {
    version: data.version ?? "1.0",
    name: data.name,
    description: data.description ?? null,
    created: data.created ?? new Date().toISOString(),
    updated: data.updated ?? new Date().toISOString(),
    files: (data.files ?? []).map((f: BvpFileEntry) => ({
      id: f.id ?? crypto.randomUUID(),
      type: f.type,
      path: f.path,
      name: f.name,
      size: f.size ?? 0,
    })),
    settings: data.settings,
  };
}

/** Serialize a BvpProject to a formatted JSON string */
export function serializeBvp(project: BvpProject): string {
  return JSON.stringify(
    { ...project, updated: new Date().toISOString() },
    null,
    2
  );
}

/** Create a new empty BvpProject */
export function createEmptyBvp(name: string, description?: string): BvpProject {
  const now = new Date().toISOString();
  return {
    version: "1.0",
    name,
    description: description ?? null,
    created: now,
    updated: now,
    files: [],
  };
}
