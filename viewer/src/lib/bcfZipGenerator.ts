/**
 * BCF 2.1 ZIP file generator.
 *
 * Creates a valid BCF ZIP from queued BcfIssue items.
 * Uses JSZip for archive creation and generates XML
 * conforming to the BCF 2.1 specification.
 */

import JSZip from "jszip";
import type { BcfIssue } from "../types/bcfIssue";

// ── XML helpers ────────────────────────────────────────────

function esc(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function uuid(): string {
  return crypto.randomUUID();
}

// ── BCF version XML ────────────────────────────────────────

function bcfVersionXml(): string {
  return [
    `<?xml version="1.0" encoding="UTF-8"?>`,
    `<Version VersionId="2.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"`,
    `  xsi:noNamespaceSchemaLocation="version.xsd">`,
    `  <DetailedVersion>2.1</DetailedVersion>`,
    `</Version>`,
  ].join("\n");
}

// ── Extensions XML ─────────────────────────────────────────

function extensionsXml(): string {
  return [
    `<?xml version="1.0" encoding="UTF-8"?>`,
    `<Extensions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"`,
    `  xsi:noNamespaceSchemaLocation="extensions.xsd">`,
    `  <TopicTypes>`,
    `    <TopicType>IDS Validation</TopicType>`,
    `    <TopicType>Clash</TopicType>`,
    `    <TopicType>Issue</TopicType>`,
    `    <TopicType>Request</TopicType>`,
    `    <TopicType>Comment</TopicType>`,
    `  </TopicTypes>`,
    `  <TopicStatuses>`,
    `    <TopicStatus>Open</TopicStatus>`,
    `    <TopicStatus>Closed</TopicStatus>`,
    `  </TopicStatuses>`,
    `  <Priorities>`,
    `    <Priority>High</Priority>`,
    `    <Priority>Normal</Priority>`,
    `    <Priority>Low</Priority>`,
    `  </Priorities>`,
    `</Extensions>`,
  ].join("\n");
}

// ── Markup XML (topic + comment + viewpoint ref) ───────────

function markupXml(
  topicGuid: string,
  viewpointGuid: string,
  commentGuid: string,
  issue: BcfIssue,
): string {
  const t = issue.mapping.topic;
  const c = issue.mapping.comment;
  const now = new Date().toISOString();
  const hasSnapshot = !!issue.screenshot;

  const labelsXml = (t.labels ?? [])
    .map((l) => `      <Label>${esc(l)}</Label>`)
    .join("\n");

  return [
    `<?xml version="1.0" encoding="UTF-8"?>`,
    `<Markup xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"`,
    `  xsi:noNamespaceSchemaLocation="markup.xsd">`,
    `  <Topic Guid="${topicGuid}" TopicType="${esc(t.topic_type ?? "IDS Validation")}" TopicStatus="${esc(t.topic_status ?? "Open")}">`,
    `    <Title>${esc(t.title)}</Title>`,
    `    <Description>${esc(t.description)}</Description>`,
    `    <Priority>${esc(t.priority ?? "Normal")}</Priority>`,
    `    <CreationDate>${now}</CreationDate>`,
    `    <CreationAuthor>OpenAEC BIM Validator</CreationAuthor>`,
    labelsXml ? `    <Labels>\n${labelsXml}\n    </Labels>` : "",
    t.index != null ? `    <Index>${t.index}</Index>` : "",
    t.assigned_to ? `    <AssignedTo>${esc(t.assigned_to)}</AssignedTo>` : "",
    t.due_date ? `    <DueDate>${esc(t.due_date)}</DueDate>` : "",
    t.stage ? `    <Stage>${esc(t.stage)}</Stage>` : "",
    `  </Topic>`,
    `  <Comment Guid="${commentGuid}">`,
    `    <Date>${now}</Date>`,
    `    <Author>OpenAEC BIM Validator</Author>`,
    `    <Comment>${esc(c.comment)}</Comment>`,
    `    <Viewpoint Guid="${viewpointGuid}" />`,
    `  </Comment>`,
    `  <Viewpoints>`,
    `    <ViewPoint Guid="${viewpointGuid}">`,
    `      <Viewpoint>viewpoint.bcfv</Viewpoint>`,
    hasSnapshot ? `      <Snapshot>snapshot.png</Snapshot>` : "",
    `    </ViewPoint>`,
    `  </Viewpoints>`,
    `</Markup>`,
  ]
    .filter(Boolean)
    .join("\n");
}

// ── Viewpoint XML ──────────────────────────────────────────

function viewpointXml(viewpointGuid: string, issue: BcfIssue): string {
  const comps = issue.mapping.viewpoint.components;
  const selection = comps?.selection ?? [];
  const coloring = comps?.coloring ?? [];

  const selectionXml =
    selection.length > 0
      ? [
          `    <Selection>`,
          ...selection.map(
            (c) => `      <Component IfcGuid="${esc(c.ifc_guid)}" />`,
          ),
          `    </Selection>`,
        ].join("\n")
      : "";

  const coloringXml =
    coloring.length > 0
      ? [
          `    <Coloring>`,
          ...coloring.map((group) =>
            [
              `      <Color Color="${esc(group.color)}">`,
              ...group.components.map(
                (c) => `        <Component IfcGuid="${esc(c.ifc_guid)}" />`,
              ),
              `      </Color>`,
            ].join("\n"),
          ),
          `    </Coloring>`,
        ].join("\n")
      : "";

  return [
    `<?xml version="1.0" encoding="UTF-8"?>`,
    `<VisualizationInfo Guid="${viewpointGuid}"`,
    `  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"`,
    `  xsi:noNamespaceSchemaLocation="visinfo.xsd">`,
    `  <Components>`,
    `    <Visibility DefaultVisibility="true">`,
    `      <Exceptions />`,
    `    </Visibility>`,
    selectionXml,
    coloringXml,
    `  </Components>`,
    `</VisualizationInfo>`,
  ]
    .filter(Boolean)
    .join("\n");
}

// ── Snapshot helpers ───────────────────────────────────────

/** Strip data URL prefix and decode base64 to binary */
function dataUrlToBytes(dataUrl: string): Uint8Array {
  const base64 = dataUrl.replace(/^data:[^;]+;base64,/, "");
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

// ── Public API ─────────────────────────────────────────────

/**
 * Generate a BCF 2.1 ZIP file from an array of BcfIssues.
 * Returns a Blob suitable for download.
 */
export async function generateBcfZip(issues: BcfIssue[]): Promise<Blob> {
  const zip = new JSZip();

  // Root files
  zip.file("bcf.version", bcfVersionXml());
  zip.file("extensions.xml", extensionsXml());

  // One folder per issue/topic
  for (const issue of issues) {
    const topicGuid = uuid();
    const viewpointGuid = uuid();
    const commentGuid = uuid();

    const folder = zip.folder(topicGuid);
    if (!folder) continue;

    folder.file(
      "markup.bcf",
      markupXml(topicGuid, viewpointGuid, commentGuid, issue),
    );
    folder.file("viewpoint.bcfv", viewpointXml(viewpointGuid, issue));

    // Add screenshot if available
    if (issue.screenshot) {
      folder.file("snapshot.png", dataUrlToBytes(issue.screenshot));
    }
  }

  return zip.generateAsync({ type: "blob", mimeType: "application/zip" });
}

/**
 * Trigger a browser download of a BCF ZIP file.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
