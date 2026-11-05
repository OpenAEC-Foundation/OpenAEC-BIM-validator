import { describe, it, expect } from "vitest";
import JSZip from "jszip";
import { importBcfArchive } from "./bcfArchive";
import { generateBcfZip } from "./bcfZipGenerator";
import { createBcfIssue } from "../types/bcfIssue";

async function bytes(blob: Blob): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result as ArrayBuffer); reader.onerror = reject; reader.readAsArrayBuffer(blob); });
}
async function archive(markup?: string) {
  const zip = new JSZip();
  zip.file("bcf.version", '<Version VersionId="2.1"/>');
  zip.file("topic-1/markup.bcf", markup ?? `<Markup><Topic Guid="topic-1" TopicType="Issue" TopicStatus="Open"><Title>Wall &amp; door</Title><CreationDate>2026-01-02T03:04:05Z</CreationDate><CreationAuthor>reviewer@example.org</CreationAuthor><Description>Check clearance</Description><Labels>Review</Labels></Topic><Comment Guid="comment-1"><Author>reviewer@example.org</Author><Date>2026-02-01T00:00:00Z</Date><Comment>First review</Comment><Viewpoint Guid="view-1"/></Comment><Comment Guid="comment-2"><Author>second@example.org</Author><Date>2026-02-02T00:00:00Z</Date><Comment>Second review</Comment></Comment><Viewpoints Guid="view-1"><Viewpoint>camera.bcfv</Viewpoint><Snapshot>image.png</Snapshot></Viewpoints></Markup>`);
  zip.file("topic-1/camera.bcfv", `<VisualizationInfo Guid="view-1"><Components><Selection><Component IfcGuid="wall-1"/></Selection><Visibility DefaultVisibility="false"><Exceptions><Component IfcGuid="wall-1"/></Exceptions></Visibility><Coloring><Color Color="FF0000"><Component IfcGuid="wall-1"/></Color></Coloring></Components><PerspectiveCamera><CameraViewPoint><X>1</X><Y>2</Y><Z>3</Z></CameraViewPoint><CameraDirection><X>0</X><Y>1</Y><Z>0</Z></CameraDirection><CameraUpVector><X>0</X><Y>0</Y><Z>1</Z></CameraUpVector><FieldOfView>60</FieldOfView></PerspectiveCamera><ClippingPlanes><ClippingPlane><Location><X>0</X><Y>0</Y><Z>0</Z></Location><Direction><X>1</X><Y>0</Y><Z>0</Z></Direction></ClippingPlane></ClippingPlanes></VisualizationInfo>`);
  zip.file("topic-1/image.png", new Uint8Array([137,80,78,71]));
  return zip;
}
describe("BCF archive round trip", () => {
  it("reads the referenced camera, selection, coloring, image and topic identity", async () => {
    const [issue] = await importBcfArchive(await (await archive()).generateAsync({ type: "uint8array" }));
    expect(issue?.id).toBe("topic-1");
    expect(issue?.title).toBe("Wall & door");
    expect(issue?.mapping.topic.labels).toEqual(["Review"]);
    expect(issue?.createdAt).toBe("2026-01-02T03:04:05Z");
    expect(issue?.mapping.viewpoint.camera?.position).toEqual({ x: 1, y: 2, z: 3 });
    expect(issue?.mapping.viewpoint.components?.selection).toEqual([{ ifc_guid: "wall-1" }]);
    expect(issue?.mapping.viewpoint.components?.visibility?.default_visibility).toBe(false);
    expect(issue?.mapping.viewpoint.components?.coloring?.[0]?.color).toBe("FF0000");
    expect(issue?.screenshot).toBe("data:image/png;base64,iVBORw==");
  });
  it("preserves topic GUIDs, authors, all comments and original viewpoint bytes on export", async () => {
    const original = await archive();
    const imported = await importBcfArchive(await original.generateAsync({ type: "uint8array" }));
    imported[0]!.mapping.topic.topic_status = "Closed";
    const roundtrip = await JSZip.loadAsync(await bytes(await generateBcfZip(imported)));
    const markup = new DOMParser().parseFromString(await roundtrip.file("topic-1/markup.bcf")!.async("text"), "text/xml");
    expect(markup.querySelector("Topic")?.getAttribute("TopicStatus")).toBe("Closed");
    expect(markup.querySelectorAll("Comment[Guid]")).toHaveLength(2);
    expect(markup.querySelector("CreationAuthor")?.textContent).toBe("reviewer@example.org");
    expect(await roundtrip.file("topic-1/camera.bcfv")!.async("text")).toBe(await original.file("topic-1/camera.bcfv")!.async("text"));
    expect(await roundtrip.file("topic-1/image.png")!.async("base64")).toBe("iVBORw==");
  });
  it("keeps locally created topic IDs and creation dates stable across exports", async () => {
    const issue = createBcfIssue("Local", { specificationName: "Walls" }, { topic: { title: "Local", description: "Check" }, viewpoint: { components: { selection: [{ ifc_guid: "wall-1" }] } }, comment: { comment: "Review" } });
    const imported = await importBcfArchive(await bytes(await generateBcfZip([issue])));
    expect(imported[0]?.id).toBe(issue.id);
    expect(imported[0]?.createdAt).toBe(issue.createdAt);
  });
  it("rejects malformed markup atomically", async () => {
    await expect(importBcfArchive(await (await archive("<Markup><Topic>")).generateAsync({ type: "uint8array" }))).rejects.toThrow(/XML/);
  });
  it("rejects unsupported versions and archives without topics", async () => {
    const zip = await archive(); zip.file("bcf.version", '<Version VersionId="3.0"/>');
    await expect(importBcfArchive(await zip.generateAsync({ type: "uint8array" }))).rejects.toThrow(/2.1/);
    zip.remove("topic-1"); zip.file("bcf.version", '<Version VersionId="2.1"/>');
    await expect(importBcfArchive(await zip.generateAsync({ type: "uint8array" }))).rejects.toThrow(/topic/i);
  });
  it("rejects missing referenced viewpoints instead of inventing a camera", async () => {
    const zip = await archive(); zip.remove("topic-1/camera.bcfv");
    await expect(importBcfArchive(await zip.generateAsync({ type: "uint8array" }))).rejects.toThrow(/camera.bcfv/);
  });
  it("rejects document type declarations", async () => {
    const zip = await archive('<!DOCTYPE Markup [<!ENTITY a "text">]><Markup><Topic Guid="topic-1"><Title>&a;</Title></Topic></Markup>');
    await expect(importBcfArchive(await zip.generateAsync({ type: "uint8array" }))).rejects.toThrow(/XML/);
  });
  it("rejects unsafe relative asset paths", async () => {
    const zip = await archive();
    const markup = await zip.file("topic-1/markup.bcf")!.async("text");
    zip.file("topic-1/markup.bcf", markup.replace("camera.bcfv", "../camera.bcfv"));
    await expect(importBcfArchive(await zip.generateAsync({ type: "uint8array" }))).rejects.toThrow(/path/);
  });
  it("rejects duplicate topic IDs across folders", async () => {
    const zip = await archive();
    zip.file("other/markup.bcf", await zip.file("topic-1/markup.bcf")!.async("text"));
    await expect(importBcfArchive(await zip.generateAsync({ type: "uint8array" }))).rejects.toThrow(/duplicate/);
  });
  it("writes the BCF 2.1 schema structure and retains a local camera", async () => {
    const issue = createBcfIssue("Local", { specificationName: "Walls" }, { topic: { title: "Local", description: "Check", labels: ["Review", "Walls"], index: 4 }, viewpoint: { camera: { camera_type: "orthogonal", position: {x:1,y:2,z:3}, direction: {x:0,y:1,z:0}, up: {x:0,y:0,z:1}, view_to_world_scale: 20 }, components: { selection: [{ifc_guid:"wall-1"}], visibility: { default_visibility: false, exceptions: [{ifc_guid:"wall-1"}] } } }, comment: { comment: "Review" } });
    const data = await bytes(await generateBcfZip([issue]));
    const zip = await JSZip.loadAsync(data);
    const doc = new DOMParser().parseFromString(await zip.file(`${issue.id}/markup.bcf`)!.async("text"), "text/xml");
    expect(doc.querySelector("Markup > Viewpoints[Guid] > Viewpoint")).not.toBeNull();
    expect(doc.querySelector("ViewPoint")).toBeNull();
    expect(Array.from(doc.querySelector("Topic")!.children).map(el => el.tagName)).toEqual(["Title", "Priority", "Index", "Labels", "Labels", "CreationDate", "CreationAuthor", "Description"]);
    const imported = (await importBcfArchive(data))[0]!;
    expect(imported.mapping.viewpoint.camera).toEqual(issue.mapping.viewpoint.camera);
    expect(imported.mapping.topic.labels).toEqual(["Review", "Walls"]);
    expect(imported.mapping.viewpoint.components?.visibility).toEqual(issue.mapping.viewpoint.components?.visibility);
  });

  it("honours the numeric XML boolean for hidden components", async () => {
    const zip = await archive();
    zip.file("topic-1/camera.bcfv", (await zip.file("topic-1/camera.bcfv")!.async("text")).replace('DefaultVisibility="false"', 'DefaultVisibility="0"'));
    const [issue] = await importBcfArchive(await zip.generateAsync({ type: "uint8array" }));
    expect(issue?.mapping.viewpoint.components?.visibility?.default_visibility).toBe(false);
  });

});
