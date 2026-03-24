/**
 * Maps ValidationResult to BCF topic creation requests.
 *
 * Three granularities:
 * - mapSpecToTopic: one topic per failed specification
 * - mapRequirementToTopic: one topic per failed requirement
 * - mapElementToTopic: one topic per failed element
 *
 * mapValidationToTopics: bulk — one topic per failed spec (backward-compatible).
 */

import type {
  ValidationResult,
  SpecificationResult,
  RequirementResult,
  ElementResult,
  Severity,
} from "../types/validation";
import type {
  CreateTopicRequest,
  CreateViewpointRequest,
  CreateCommentRequest,
} from "../types/bcfPlatform";

export interface TopicMapping {
  topic: CreateTopicRequest;
  viewpoint: CreateViewpointRequest;
  comment: CreateCommentRequest;
}

// ── Helpers ────────────────────────────────────────────────

function severityToPriority(severity: Severity): string {
  switch (severity) {
    case "error":
      return "High";
    case "warning":
      return "Normal";
    case "info":
      return "Low";
  }
}

function xmlSafeText(text: string, maxLen = 200): string {
  return text.slice(0, maxLen);
}

function buildViewpoint(globalIds: string[]): CreateViewpointRequest {
  return {
    components: {
      selection: globalIds.map((ifc_guid) => ({ ifc_guid })),
      visibility: {
        default_visibility: true,
        exceptions: [],
      },
      coloring:
        globalIds.length > 0
          ? [
              {
                color: "FF0000",
                components: globalIds.map((ifc_guid) => ({ ifc_guid })),
              },
            ]
          : [],
    },
  };
}

function collectFailedGlobalIds(spec: SpecificationResult): string[] {
  const ids = new Set<string>();
  for (const req of spec.requirements) {
    if (req.status !== "fail") continue;
    for (const el of req.elements) {
      if (el.status === "fail" && el.global_id) {
        ids.add(el.global_id);
      }
    }
  }
  return [...ids];
}

function collectRequirementFailedGlobalIds(req: RequirementResult): string[] {
  const ids = new Set<string>();
  for (const el of req.elements) {
    if (el.status === "fail" && el.global_id) {
      ids.add(el.global_id);
    }
  }
  return [...ids];
}

function buildLabelsFromSpec(spec: SpecificationResult): string[] {
  const labels = new Set<string>(["IDS"]);
  for (const req of spec.requirements) {
    if (req.status !== "fail") continue;
    for (const el of req.elements) {
      if (el.status === "fail") {
        labels.add(el.element_type);
      }
    }
  }
  return [...labels].slice(0, 10);
}

function buildLabelsFromRequirement(req: RequirementResult): string[] {
  const labels = new Set<string>(["IDS"]);
  for (const el of req.elements) {
    if (el.status === "fail") {
      labels.add(el.element_type);
    }
  }
  return [...labels].slice(0, 10);
}

// ── Spec-level description ─────────────────────────────────

function buildSpecDescription(
  spec: SpecificationResult,
  ifcFileName: string,
  idsFileName: string,
): string {
  const lines: string[] = [];
  lines.push(`IDS Specification: ${spec.specification_name}`);
  lines.push(`Status: ${spec.status.toUpperCase()}`);
  lines.push(`Severity: ${spec.severity}`);
  lines.push("");

  for (const req of spec.requirements) {
    if (req.status !== "fail") continue;

    lines.push(`Requirement: ${req.requirement_description}`);
    lines.push(`Failed: ${req.failed_elements} / ${req.total_elements} elements`);
    lines.push("");

    const failedElements = req.elements.filter((e) => e.status === "fail");
    const shown = failedElements.slice(0, 20);

    for (const el of shown) {
      const name = el.element_name ?? "unnamed";
      const gid = el.global_id ?? "no-guid";
      const msgs = el.messages.length > 0 ? ` — ${el.messages[0]}` : "";
      lines.push(`  - ${gid} ${el.element_type} "${name}"${msgs}`);
    }

    if (failedElements.length > 20) {
      lines.push(`  ... and ${failedElements.length - 20} more elements`);
    }
    lines.push("");
  }

  lines.push(`Source IFC: ${ifcFileName}`);
  lines.push(`Source IDS: ${idsFileName}`);

  return lines.join("\n");
}

// ── Requirement-level description ──────────────────────────

function buildRequirementDescription(
  spec: SpecificationResult,
  req: RequirementResult,
  ifcFileName: string,
  idsFileName: string,
): string {
  const lines: string[] = [];
  lines.push(`IDS Specification: ${spec.specification_name}`);
  lines.push(`Requirement: ${req.requirement_description}`);
  lines.push(`Severity: ${spec.severity}`);
  lines.push(`Failed: ${req.failed_elements} / ${req.total_elements} elements`);
  lines.push("");

  const failedElements = req.elements.filter((e) => e.status === "fail");
  const shown = failedElements.slice(0, 20);

  for (const el of shown) {
    const name = el.element_name ?? "unnamed";
    const gid = el.global_id ?? "no-guid";
    const msgs = el.messages.length > 0 ? ` — ${el.messages[0]}` : "";
    lines.push(`  - ${gid} ${el.element_type} "${name}"${msgs}`);
  }

  if (failedElements.length > 20) {
    lines.push(`  ... and ${failedElements.length - 20} more elements`);
  }
  lines.push("");
  lines.push(`Source IFC: ${ifcFileName}`);
  lines.push(`Source IDS: ${idsFileName}`);

  return lines.join("\n");
}

// ── Element-level description ──────────────────────────────

function buildElementDescription(
  spec: SpecificationResult,
  req: RequirementResult,
  element: ElementResult,
  ifcFileName: string,
  idsFileName: string,
): string {
  const lines: string[] = [];
  lines.push(`IDS Specification: ${spec.specification_name}`);
  lines.push(`Requirement: ${req.requirement_description}`);
  lines.push(`Severity: ${spec.severity}`);
  lines.push("");
  lines.push(`Element: ${element.element_type} "${element.element_name ?? "unnamed"}"`);
  lines.push(`GlobalId: ${element.global_id ?? "no-guid"}`);

  if (element.messages.length > 0) {
    lines.push("");
    lines.push("Messages:");
    for (const msg of element.messages) {
      lines.push(`  - ${msg}`);
    }
  }

  lines.push("");
  lines.push(`Source IFC: ${ifcFileName}`);
  lines.push(`Source IDS: ${idsFileName}`);

  return lines.join("\n");
}

// ── Public mappers ─────────────────────────────────────────

/**
 * Map a single failed specification to a BCF topic.
 */
export function mapSpecToTopic(
  spec: SpecificationResult,
  ifcFileName: string,
  idsFileName: string,
  index = 1,
): TopicMapping {
  const globalIds = collectFailedGlobalIds(spec);
  const failedReqs = spec.requirements.filter((r) => r.status === "fail");
  const totalFailed = failedReqs.reduce((sum, r) => sum + r.failed_elements, 0);

  const topic: CreateTopicRequest = {
    title: xmlSafeText(spec.specification_name),
    description: buildSpecDescription(spec, ifcFileName, idsFileName),
    topic_type: "IDS Validation",
    topic_status: "Open",
    priority: severityToPriority(spec.severity),
    labels: buildLabelsFromSpec(spec),
    index,
  };

  const comment: CreateCommentRequest = {
    comment:
      `Automatisch gegenereerd door OpenAEC BIM Validator.\n\n` +
      `${failedReqs.length} gefaalde requirement(s), ${totalFailed} element(en) totaal.`,
  };

  return { topic, viewpoint: buildViewpoint(globalIds), comment };
}

/**
 * Map a single failed requirement to a BCF topic.
 */
export function mapRequirementToTopic(
  spec: SpecificationResult,
  req: RequirementResult,
  ifcFileName: string,
  idsFileName: string,
  index = 1,
): TopicMapping {
  const globalIds = collectRequirementFailedGlobalIds(req);

  const topic: CreateTopicRequest = {
    title: xmlSafeText(`${spec.specification_name} — ${req.requirement_description}`),
    description: buildRequirementDescription(spec, req, ifcFileName, idsFileName),
    topic_type: "IDS Validation",
    topic_status: "Open",
    priority: severityToPriority(spec.severity),
    labels: buildLabelsFromRequirement(req),
    index,
  };

  const comment: CreateCommentRequest = {
    comment:
      `Automatisch gegenereerd door OpenAEC BIM Validator.\n\n` +
      `Requirement: ${req.requirement_description}\n` +
      `${req.failed_elements} gefaald(e) element(en) van ${req.total_elements} totaal.`,
  };

  return { topic, viewpoint: buildViewpoint(globalIds), comment };
}

/**
 * Map a single failed element to a BCF topic.
 */
export function mapElementToTopic(
  spec: SpecificationResult,
  req: RequirementResult,
  element: ElementResult,
  ifcFileName: string,
  idsFileName: string,
  index = 1,
): TopicMapping {
  const globalIds = element.global_id ? [element.global_id] : [];
  const elementName = element.element_name ?? "unnamed";

  const topic: CreateTopicRequest = {
    title: xmlSafeText(
      `${element.element_type} "${elementName}" — ${req.requirement_description}`,
    ),
    description: buildElementDescription(spec, req, element, ifcFileName, idsFileName),
    topic_type: "IDS Validation",
    topic_status: "Open",
    priority: severityToPriority(spec.severity),
    labels: ["IDS", element.element_type],
    index,
  };

  const comment: CreateCommentRequest = {
    comment:
      `Automatisch gegenereerd door OpenAEC BIM Validator.\n\n` +
      `Element: ${element.element_type} "${elementName}"\n` +
      `GlobalId: ${element.global_id ?? "N/A"}\n` +
      (element.messages.length > 0 ? `Fout: ${element.messages[0]}` : ""),
  };

  return { topic, viewpoint: buildViewpoint(globalIds), comment };
}

/**
 * Bulk: map all failed specifications to BCF topics (backward-compatible).
 */
export function mapValidationToTopics(result: ValidationResult): TopicMapping[] {
  const failedSpecs = result.specifications.filter((s) => s.status === "fail");

  return failedSpecs.map((spec, index) =>
    mapSpecToTopic(spec, result.ifc_file_name, result.ids_file_name, index + 1),
  );
}
