/**
 * BCF generation settings — configurable metadata applied to
 * generated BCF topics before ZIP export or platform push.
 */

export interface BcfGenerationSettings {
  /** Prefix prepended to topic titles (e.g. "REV01") */
  titlePrefix: string;
  /** Include specification name in topic title */
  includeSpecName: boolean;
  /** Include requirement name in topic title (after spec) */
  includeReqName: boolean;
  /** Prefix prepended to topic descriptions */
  descriptionPrefix: string;
  /** Assigned person / responsible party */
  assignedTo: string;
  /** Milestone / phase label */
  milestone: string;
  /** Due date in ISO 8601 (YYYY-MM-DD) or empty */
  deadline: string;
  /** Extra label added to all generated topics */
  label: string;
  /** BCF topic type override */
  topicType: string;
  /** Priority override — empty string means auto from severity */
  priority: "" | "High" | "Normal" | "Low";
}

export const TOPIC_TYPE_OPTIONS = [
  "IDS Validation",
  "Clash",
  "Issue",
  "Request",
  "Comment",
] as const;

export const PRIORITY_OPTIONS = [
  { value: "" as const, label: "Auto (uit severity)" },
  { value: "High" as const, label: "High" },
  { value: "Normal" as const, label: "Normal" },
  { value: "Low" as const, label: "Low" },
] as const;

export const DEFAULT_BCF_SETTINGS: BcfGenerationSettings = {
  titlePrefix: "",
  includeSpecName: true,
  includeReqName: true,
  descriptionPrefix: "",
  assignedTo: "",
  milestone: "",
  deadline: "",
  label: "",
  topicType: "IDS Validation",
  priority: "",
};

const STORAGE_KEY = "bcf-generation-settings";

/** Load persisted settings from localStorage, with defaults fallback. */
export function loadBcfSettings(): BcfGenerationSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_BCF_SETTINGS };
    const parsed = JSON.parse(raw) as Partial<BcfGenerationSettings>;
    return { ...DEFAULT_BCF_SETTINGS, ...parsed };
  } catch {
    return { ...DEFAULT_BCF_SETTINGS };
  }
}

/** Persist settings to localStorage. */
export function saveBcfSettings(settings: BcfGenerationSettings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}
