/**
 * BcfImporter — Parses BCF 2.1 .bcfzip files into BcfIssue objects.
 *
 * Reads the ZIP structure and maps BCF XML back to our internal types:
 *   bcf.version → version check
 *   <topic-guid>/markup.bcf → BcfIssue (topic, comments)
 *   <topic-guid>/viewpoint.bcfv → BcfViewpoint (camera, components)
 *   <topic-guid>/snapshot.png → screenshotDataUrl
 */

import JSZip from "jszip";

import type {
  BcfIssue,
  BcfViewpoint,
  BcfCameraState,
  BcfComment,
  BcfComponentRef,
  BcfComponents,
  IssueType,
  IssueStatus,
  IssuePriority,
} from "../../types/bcf";

/**
 * Import a .bcfzip file and return parsed BCF issues.
 */
export async function importBcfZip(file: File): Promise<BcfIssue[]> {
  const zip = await JSZip.loadAsync(file);
  const issues: BcfIssue[] = [];

  // Find all topic folders (folders containing markup.bcf)
  const topicGuids = new Set<string>();

  zip.forEach((relativePath) => {
    const match = relativePath.match(/^([^/]+)\/markup\.bcf$/);
    if (match?.[1]) {
      topicGuids.add(match[1]);
    }
  });

  let index = 0;
  for (const guid of topicGuids) {
    const markupFile = zip.file(`${guid}/markup.bcf`);
    if (!markupFile) continue;

    const markupXml = await markupFile.async("text");
    const issue = parseMarkupXml(markupXml, guid);

    // Parse viewpoint if available
    const viewpointFile = zip.file(`${guid}/viewpoint.bcfv`);
    if (viewpointFile) {
      const viewpointXml = await viewpointFile.async("text");
      issue.viewpoint = parseViewpointXml(viewpointXml, issue.viewpoint);
    }

    // Load snapshot if available
    const snapshotFile = zip.file(`${guid}/snapshot.png`);
    if (snapshotFile) {
      const base64 = await snapshotFile.async("base64");
      issue.viewpoint.screenshotDataUrl = `data:image/png;base64,${base64}`;
    }

    issue.index = index++;
    issues.push(issue);
  }

  return issues;
}

/**
 * Parse markup.bcf XML into a BcfIssue.
 */
function parseMarkupXml(xml: string, fallbackGuid: string): BcfIssue {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xml, "text/xml");

  const topic = doc.querySelector("Topic");
  const guid = topic?.getAttribute("Guid") ?? fallbackGuid;

  const now = new Date().toISOString();

  // Parse comments
  const comments: BcfComment[] = [];
  doc.querySelectorAll("Comment[Guid]").forEach((commentEl) => {
    comments.push({
      guid: commentEl.getAttribute("Guid") ?? crypto.randomUUID(),
      author: getTextContent(commentEl, "Author") ?? "Unknown",
      date: getTextContent(commentEl, "Date") ?? now,
      comment: getTextContent(commentEl, "Comment") ?? "",
      viewpointGuid:
        commentEl.querySelector("Viewpoint")?.getAttribute("Guid") ??
        undefined,
    });
  });

  // Parse labels
  const labels: string[] = [];
  doc.querySelectorAll("Label").forEach((labelEl) => {
    if (labelEl.textContent) {
      labels.push(labelEl.textContent);
    }
  });

  return {
    guid,
    title: getTextContent(topic, "Title") ?? "Untitled",
    description: getTextContent(topic, "Description") ?? "",
    type: (topic?.getAttribute("TopicType") as IssueType) ?? "Error",
    status: (topic?.getAttribute("TopicStatus") as IssueStatus) ?? "Open",
    priority:
      (getTextContent(topic, "Priority") as IssuePriority) ?? "Normal",
    assignedTo: getTextContent(topic, "AssignedTo") ?? "",
    creationDate: getTextContent(topic, "CreationDate") ?? now,
    modifiedDate: getTextContent(topic, "ModifiedDate") ?? now,
    creationAuthor: getTextContent(topic, "CreationAuthor") ?? "Unknown",
    dueDate: getTextContent(topic, "DueDate") ?? undefined,
    labels,
    viewpoint: createEmptyViewpoint(),
    comments,
    failedGlobalIds: [],
    index: 0,
  };
}

/**
 * Parse viewpoint.bcfv XML and merge into an existing viewpoint.
 */
function parseViewpointXml(
  xml: string,
  baseViewpoint: BcfViewpoint
): BcfViewpoint {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xml, "text/xml");

  const root = doc.querySelector("VisualizationInfo");
  const guid = root?.getAttribute("Guid") ?? baseViewpoint.guid;

  // Parse camera
  const camera = parseCameraFromDoc(doc) ?? baseViewpoint.camera;

  // Parse components
  const components = parseComponentsFromDoc(doc);

  return {
    ...baseViewpoint,
    guid,
    camera,
    components,
  };
}

/**
 * Parse PerspectiveCamera or OrthogonalCamera from a viewpoint XML document.
 */
function parseCameraFromDoc(doc: Document): BcfCameraState | null {
  const perspective = doc.querySelector("PerspectiveCamera");
  if (perspective) {
    return {
      type: "perspective",
      position: parsePoint3D(perspective, "CameraViewPoint"),
      direction: parsePoint3D(perspective, "CameraDirection"),
      up: parsePoint3D(perspective, "CameraUpVector"),
      fieldOfView: parseFloat(
        getTextContent(perspective, "FieldOfView") ?? "60"
      ),
    };
  }

  const orthogonal = doc.querySelector("OrthogonalCamera");
  if (orthogonal) {
    return {
      type: "orthogonal",
      position: parsePoint3D(orthogonal, "CameraViewPoint"),
      direction: parsePoint3D(orthogonal, "CameraDirection"),
      up: parsePoint3D(orthogonal, "CameraUpVector"),
    };
  }

  return null;
}

/**
 * Parse Components section from a viewpoint XML document.
 */
function parseComponentsFromDoc(doc: Document): BcfComponents {
  const selection: BcfComponentRef[] = [];
  doc.querySelectorAll("Selection > Component").forEach((el) => {
    const ifcGuid = el.getAttribute("IfcGuid");
    if (ifcGuid) {
      selection.push({
        ifcGuid,
        originatingSystem:
          el.getAttribute("OriginatingSystem") ?? undefined,
      });
    }
  });

  const visibilityEl = doc.querySelector("Visibility");
  const defaultVisibility =
    visibilityEl?.getAttribute("DefaultVisibility") !== "false";

  const exceptions: BcfComponentRef[] = [];
  doc.querySelectorAll("Exceptions > Component").forEach((el) => {
    const ifcGuid = el.getAttribute("IfcGuid");
    if (ifcGuid) {
      exceptions.push({ ifcGuid });
    }
  });

  return {
    selection,
    visibility: { defaultVisibility, exceptions },
    coloring: [],
  };
}

/**
 * Parse a Point3D (X, Y, Z) from a parent element.
 */
function parsePoint3D(
  parent: Element,
  containerTag: string
): { x: number; y: number; z: number } {
  const container = parent.querySelector(containerTag);
  return {
    x: parseFloat(getTextContent(container, "X") ?? "0"),
    y: parseFloat(getTextContent(container, "Y") ?? "0"),
    z: parseFloat(getTextContent(container, "Z") ?? "0"),
  };
}

/**
 * Get text content of a child element by tag name.
 */
function getTextContent(
  parent: Element | null,
  tag: string
): string | null {
  return parent?.querySelector(tag)?.textContent ?? null;
}

/**
 * Create an empty viewpoint as a fallback.
 */
function createEmptyViewpoint(): BcfViewpoint {
  return {
    guid: crypto.randomUUID(),
    camera: {
      type: "perspective",
      position: { x: 15, y: 15, z: 15 },
      direction: { x: -0.577, y: -0.577, z: -0.577 },
      up: { x: 0, y: 1, z: 0 },
      fieldOfView: 60,
    },
    screenshotDataUrl: "",
    components: {
      selection: [],
      visibility: { defaultVisibility: true, exceptions: [] },
      coloring: [],
    },
  };
}
