/**
 * Tests for BcfExporter — XML generation and ZIP structure.
 */

import { describe, it, expect } from "vitest";
import JSZip from "jszip";

import {
  exportBcfZip,
  generateMarkupXml,
  generateViewpointXml,
} from "../BcfExporter";
import type { BcfIssue, BcfViewpoint } from "../../../types/bcf";

/** Create a minimal test viewpoint */
function createTestViewpoint(): BcfViewpoint {
  return {
    guid: "vp-001",
    camera: {
      position: { x: 10, y: 20, z: 30 },
      direction: { x: -0.5, y: -0.5, z: -0.707 },
      up: { x: 0, y: 1, z: 0 },
      type: "perspective",
      fieldOfView: 60,
    },
    screenshotDataUrl: "",
    components: {
      selection: [{ ifcGuid: "abc123" }],
      visibility: { defaultVisibility: true, exceptions: [] },
      coloring: [
        {
          color: "#FF4444",
          components: [{ ifcGuid: "abc123" }],
        },
      ],
    },
  };
}

/** Create a minimal test issue */
function createTestIssue(): BcfIssue {
  return {
    guid: "issue-001",
    title: "Test Issue",
    description: "A test description",
    type: "Error",
    status: "Open",
    priority: "High",
    assignedTo: "Jochem",
    creationDate: "2026-03-20T10:00:00.000Z",
    modifiedDate: "2026-03-20T10:00:00.000Z",
    creationAuthor: "Validator",
    labels: ["spec-1"],
    viewpoint: createTestViewpoint(),
    comments: [
      {
        guid: "comment-001",
        author: "Validator",
        date: "2026-03-20T10:00:00.000Z",
        comment: "Validation failed",
        viewpointGuid: "vp-001",
      },
    ],
    failedGlobalIds: ["abc123"],
    index: 0,
  };
}

describe("generateMarkupXml", () => {
  it("generates valid XML with topic data", () => {
    const issue = createTestIssue();
    const xml = generateMarkupXml(issue);

    expect(xml).toContain('<?xml version="1.0"');
    expect(xml).toContain("<Markup");
    expect(xml).toContain('Guid="issue-001"');
    expect(xml).toContain('TopicType="Error"');
    expect(xml).toContain('TopicStatus="Open"');
    expect(xml).toContain("<Title>Test Issue</Title>");
    expect(xml).toContain("<Priority>High</Priority>");
    expect(xml).toContain("<AssignedTo>Jochem</AssignedTo>");
    expect(xml).toContain("<Label>spec-1</Label>");
  });

  it("includes comments", () => {
    const issue = createTestIssue();
    const xml = generateMarkupXml(issue);

    expect(xml).toContain('Comment Guid="comment-001"');
    expect(xml).toContain("<Author>Validator</Author>");
    expect(xml).toContain("<Comment>Validation failed</Comment>");
  });

  it("includes viewpoint reference", () => {
    const issue = createTestIssue();
    const xml = generateMarkupXml(issue);

    expect(xml).toContain('ViewPoint Guid="vp-001"');
    expect(xml).toContain("<Viewpoint>viewpoint.bcfv</Viewpoint>");
    expect(xml).toContain("<Snapshot>snapshot.png</Snapshot>");
  });

  it("escapes XML special characters", () => {
    const issue = createTestIssue();
    issue.title = 'Test <"Issue"> & more';
    const xml = generateMarkupXml(issue);

    expect(xml).toContain("Test &lt;&quot;Issue&quot;&gt; &amp; more");
  });

  it("omits optional fields when empty", () => {
    const issue = createTestIssue();
    issue.assignedTo = "";
    issue.dueDate = undefined;
    const xml = generateMarkupXml(issue);

    expect(xml).not.toContain("<AssignedTo>");
    expect(xml).not.toContain("<DueDate>");
  });
});

describe("generateViewpointXml", () => {
  it("generates perspective camera XML", () => {
    const viewpoint = createTestViewpoint();
    const xml = generateViewpointXml(viewpoint);

    expect(xml).toContain('<?xml version="1.0"');
    expect(xml).toContain("<VisualizationInfo");
    expect(xml).toContain("<PerspectiveCamera>");
    expect(xml).toContain("<FieldOfView>60</FieldOfView>");
    expect(xml).toContain("<X>10</X>");
    expect(xml).toContain("<Y>20</Y>");
    expect(xml).toContain("<Z>30</Z>");
  });

  it("generates orthogonal camera XML", () => {
    const viewpoint = createTestViewpoint();
    viewpoint.camera.type = "orthogonal";
    const xml = generateViewpointXml(viewpoint);

    expect(xml).toContain("<OrthogonalCamera>");
    expect(xml).toContain("<ViewToWorldScale>1</ViewToWorldScale>");
    expect(xml).not.toContain("<PerspectiveCamera>");
  });

  it("includes component selection", () => {
    const viewpoint = createTestViewpoint();
    const xml = generateViewpointXml(viewpoint);

    expect(xml).toContain('<Component IfcGuid="abc123"');
    expect(xml).toContain("<Selection>");
  });

  it("includes coloring", () => {
    const viewpoint = createTestViewpoint();
    const xml = generateViewpointXml(viewpoint);

    expect(xml).toContain('<Color Color="#FF4444"');
  });
});

describe("exportBcfZip", () => {
  it("creates a valid ZIP with bcf.version", async () => {
    const issues = [createTestIssue()];
    const blob = await exportBcfZip(issues);

    expect(blob).toBeInstanceOf(Blob);
    expect(blob.size).toBeGreaterThan(0);

    const zip = await JSZip.loadAsync(blob);
    const versionFile = zip.file("bcf.version");
    expect(versionFile).not.toBeNull();

    const versionContent = await versionFile!.async("text");
    expect(versionContent).toContain('VersionId="2.1"');
  });

  it("creates topic folder with markup and viewpoint", async () => {
    const issues = [createTestIssue()];
    const blob = await exportBcfZip(issues);

    const zip = await JSZip.loadAsync(blob);
    const markup = zip.file("issue-001/markup.bcf");
    const viewpoint = zip.file("issue-001/viewpoint.bcfv");

    expect(markup).not.toBeNull();
    expect(viewpoint).not.toBeNull();

    const markupContent = await markup!.async("text");
    expect(markupContent).toContain("<Title>Test Issue</Title>");
  });

  it("handles multiple issues", async () => {
    const issue1 = createTestIssue();
    const issue2 = createTestIssue();
    issue2.guid = "issue-002";
    issue2.title = "Second Issue";

    const blob = await exportBcfZip([issue1, issue2]);
    const zip = await JSZip.loadAsync(blob);

    expect(zip.file("issue-001/markup.bcf")).not.toBeNull();
    expect(zip.file("issue-002/markup.bcf")).not.toBeNull();
  });

  it("includes snapshot when screenshot data is present", async () => {
    const issue = createTestIssue();
    // Minimal valid PNG data URL
    issue.viewpoint.screenshotDataUrl =
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";

    const blob = await exportBcfZip([issue]);
    const zip = await JSZip.loadAsync(blob);

    const snapshot = zip.file("issue-001/snapshot.png");
    expect(snapshot).not.toBeNull();
  });

  it("handles empty issue list", async () => {
    const blob = await exportBcfZip([]);
    const zip = await JSZip.loadAsync(blob);

    const versionFile = zip.file("bcf.version");
    expect(versionFile).not.toBeNull();
    // Only bcf.version, no topic folders
    const files = Object.keys(zip.files).filter((f) => !f.endsWith("/"));
    expect(files).toHaveLength(1);
  });
});
