/**
 * BcfExporter — Generates BCF 2.1 compatible .bcfzip files.
 *
 * Creates a ZIP archive with the BCF 2.1 folder structure:
 *   bcf.version
 *   <topic-guid>/
 *     markup.bcf
 *     viewpoint.bcfv
 *     snapshot.png
 *
 * Compatible with BIMcollab, Solibri, Navisworks, etc.
 */

import JSZip from "jszip";

import type { BcfIssue, BcfViewpoint, BcfCameraState } from "../../types/bcf";

/** BCF version identifier */
const BCF_VERSION = "2.1";

/** XML declaration header */
const XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>';

/**
 * Export an array of BCF issues as a .bcfzip file.
 * Returns a Blob ready for download.
 */
export async function exportBcfZip(issues: BcfIssue[]): Promise<Blob> {
  const zip = new JSZip();

  // bcf.version file
  zip.file(
    "bcf.version",
    `${XML_HEADER}
<Version VersionId="${BCF_VERSION}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="version.xsd">
  <DetailedVersion>${BCF_VERSION}</DetailedVersion>
</Version>`
  );

  for (const issue of issues) {
    const folder = zip.folder(issue.guid);
    if (!folder) continue;

    // markup.bcf
    folder.file("markup.bcf", generateMarkupXml(issue));

    // viewpoint.bcfv
    folder.file("viewpoint.bcfv", generateViewpointXml(issue.viewpoint));

    // snapshot.png (from data URL)
    if (issue.viewpoint.screenshotDataUrl) {
      const pngData = dataUrlToBase64(issue.viewpoint.screenshotDataUrl);
      if (pngData) {
        folder.file("snapshot.png", pngData, { base64: true });
      }
    }
  }

  return zip.generateAsync({ type: "blob", mimeType: "application/zip" });
}

/**
 * Generate BCF 2.1 markup.bcf XML for a topic.
 */
export function generateMarkupXml(issue: BcfIssue): string {
  const comments = issue.comments
    .map(
      (c) =>
        `    <Comment Guid="${escapeXml(c.guid)}">
      <Date>${escapeXml(c.date)}</Date>
      <Author>${escapeXml(c.author)}</Author>
      <Comment>${escapeXml(c.comment)}</Comment>${
        c.viewpointGuid
          ? `\n      <Viewpoint Guid="${escapeXml(c.viewpointGuid)}" />`
          : ""
      }
    </Comment>`
    )
    .join("\n");

  const labels = issue.labels
    .map((l) => `      <Label>${escapeXml(l)}</Label>`)
    .join("\n");

  return `${XML_HEADER}
<Markup xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="markup.xsd">
  <Header />
  <Topic Guid="${escapeXml(issue.guid)}" TopicType="${escapeXml(issue.type)}" TopicStatus="${escapeXml(issue.status)}">
    <Title>${escapeXml(issue.title)}</Title>
    <Description>${escapeXml(issue.description)}</Description>
    <Priority>${escapeXml(issue.priority)}</Priority>
    <Index>${issue.index}</Index>
    <CreationDate>${escapeXml(issue.creationDate)}</CreationDate>
    <CreationAuthor>${escapeXml(issue.creationAuthor)}</CreationAuthor>
    <ModifiedDate>${escapeXml(issue.modifiedDate)}</ModifiedDate>${
      issue.assignedTo
        ? `\n    <AssignedTo>${escapeXml(issue.assignedTo)}</AssignedTo>`
        : ""
    }${
      issue.dueDate
        ? `\n    <DueDate>${escapeXml(issue.dueDate)}</DueDate>`
        : ""
    }${labels ? `\n    <Labels>\n${labels}\n    </Labels>` : ""}
  </Topic>
${comments ? `  <Comment>\n${comments}\n  </Comment>` : ""}
  <Viewpoints>
    <ViewPoint Guid="${escapeXml(issue.viewpoint.guid)}">
      <Viewpoint>viewpoint.bcfv</Viewpoint>
      <Snapshot>snapshot.png</Snapshot>
    </ViewPoint>
  </Viewpoints>
</Markup>`;
}

/**
 * Generate BCF 2.1 viewpoint (visinfo.bcfv) XML.
 */
export function generateViewpointXml(viewpoint: BcfViewpoint): string {
  const camera = viewpoint.camera;
  const cameraXml = generateCameraXml(camera);

  const selection = viewpoint.components.selection
    .map(
      (c) =>
        `      <Component IfcGuid="${escapeXml(c.ifcGuid)}"${
          c.originatingSystem
            ? ` OriginatingSystem="${escapeXml(c.originatingSystem)}"`
            : ""
        } />`
    )
    .join("\n");

  const visibility = viewpoint.components.visibility;
  const exceptions = visibility.exceptions
    .map(
      (c) =>
        `        <Component IfcGuid="${escapeXml(c.ifcGuid)}" />`
    )
    .join("\n");

  const coloring = viewpoint.components.coloring
    .map(
      (group) =>
        `      <Color Color="${escapeXml(group.color)}">\n${group.components
          .map(
            (c) =>
              `        <Component IfcGuid="${escapeXml(c.ifcGuid)}" />`
          )
          .join("\n")}\n      </Color>`
    )
    .join("\n");

  return `${XML_HEADER}
<VisualizationInfo Guid="${escapeXml(viewpoint.guid)}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="visinfo.xsd">
  <Components>
${selection ? `    <Selection>\n${selection}\n    </Selection>` : "    <Selection />"}
    <Visibility DefaultVisibility="${visibility.defaultVisibility}">
${exceptions ? `      <Exceptions>\n${exceptions}\n      </Exceptions>` : "      <Exceptions />"}
    </Visibility>
${coloring ? `    <Coloring>\n${coloring}\n    </Coloring>` : ""}
  </Components>
${cameraXml}
</VisualizationInfo>`;
}

/**
 * Generate camera XML block based on camera type.
 */
function generateCameraXml(camera: BcfCameraState): string {
  if (camera.type === "orthogonal") {
    return `  <OrthogonalCamera>
    <CameraViewPoint>
      <X>${camera.position.x}</X>
      <Y>${camera.position.y}</Y>
      <Z>${camera.position.z}</Z>
    </CameraViewPoint>
    <CameraDirection>
      <X>${camera.direction.x}</X>
      <Y>${camera.direction.y}</Y>
      <Z>${camera.direction.z}</Z>
    </CameraDirection>
    <CameraUpVector>
      <X>${camera.up.x}</X>
      <Y>${camera.up.y}</Y>
      <Z>${camera.up.z}</Z>
    </CameraUpVector>
    <ViewToWorldScale>1</ViewToWorldScale>
  </OrthogonalCamera>`;
  }

  return `  <PerspectiveCamera>
    <CameraViewPoint>
      <X>${camera.position.x}</X>
      <Y>${camera.position.y}</Y>
      <Z>${camera.position.z}</Z>
    </CameraViewPoint>
    <CameraDirection>
      <X>${camera.direction.x}</X>
      <Y>${camera.direction.y}</Y>
      <Z>${camera.direction.z}</Z>
    </CameraDirection>
    <CameraUpVector>
      <X>${camera.up.x}</X>
      <Y>${camera.up.y}</Y>
      <Z>${camera.up.z}</Z>
    </CameraUpVector>
    <FieldOfView>${camera.fieldOfView ?? 60}</FieldOfView>
  </PerspectiveCamera>`;
}

/**
 * Extract base64 data from a data URL.
 */
function dataUrlToBase64(dataUrl: string): string | null {
  const match = dataUrl.match(/^data:[^;]+;base64,(.+)$/);
  return match?.[1] ?? null;
}

/**
 * Escape special XML characters.
 */
function escapeXml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
