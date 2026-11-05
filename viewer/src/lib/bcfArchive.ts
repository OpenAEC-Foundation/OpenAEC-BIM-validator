/** BCF 2.1 import for the active queue, retaining original topic assets for round trips. */
import JSZip, { type JSZipObject } from "jszip";
import type { BcfIssue } from "../types/bcfIssue";
import type { BcfCamera, BcfComponents, Point3D } from "../types/bcfPlatform";

const MAX_COMPRESSED = 50 * 1024 * 1024;
const MAX_EXPANDED = 100 * 1024 * 1024;
const MAX_ENTRIES = 2000;

export function parseBcfXml(xml: string): Document {
  if (/<!DOCTYPE|<!ENTITY/i.test(xml)) throw new Error("XML document types are not supported.");
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  if (doc.querySelector("parsererror")) throw new Error("Invalid BCF XML.");
  return doc;
}
function content(parent: ParentNode, name: string): string {
  return parent.querySelector(name)?.textContent ?? "";
}
function point(parent: ParentNode, name: string): Point3D {
  const node = parent.querySelector(name);
  if (!node) throw new Error(`Missing camera vector: ${name}`);
  const values = ["X", "Y", "Z"].map(axis => {
    const value = content(node, axis);
    if (!value.trim() || !Number.isFinite(Number(value))) throw new Error("Invalid camera coordinates.");
    return Number(value);
  });
  return { x: values[0]!, y: values[1]!, z: values[2]! };
}
function viewpoint(doc: Document): { camera?: BcfCamera; components: BcfComponents } {
  if (doc.documentElement.localName !== "VisualizationInfo") throw new Error("Invalid BCF viewpoint.");
  const refs = (selector: string) => Array.from(doc.querySelectorAll(selector)).map(el => ({ ifc_guid: el.getAttribute("IfcGuid") ?? "" })).filter(ref => ref.ifc_guid);
  const components: BcfComponents = {
    selection: refs("Selection > Component"),
    visibility: { default_visibility: !["false", "0"].includes(doc.querySelector("Visibility")?.getAttribute("DefaultVisibility")?.trim() ?? "true"), exceptions: refs("Visibility > Exceptions > Component") },
    coloring: Array.from(doc.querySelectorAll("Coloring > Color")).map(color => ({ color: color.getAttribute("Color") ?? "FFFFFF", components: Array.from(color.querySelectorAll("Component")).map(el => ({ ifc_guid: el.getAttribute("IfcGuid") ?? "" })).filter(ref => ref.ifc_guid) })),
  };
  const camera = doc.querySelector("PerspectiveCamera, OrthogonalCamera");
  if (!camera) return { components };
  const perspective = camera.localName === "PerspectiveCamera";
  const scale = Number(content(camera, perspective ? "FieldOfView" : "ViewToWorldScale"));
  if (!Number.isFinite(scale) || scale <= 0 || (perspective && scale >= 180)) throw new Error("Invalid camera field of view or scale.");
  return { components, camera: {
    camera_type: perspective ? "perspective" : "orthogonal",
    position: point(camera, "CameraViewPoint"), direction: point(camera, "CameraDirection"), up: point(camera, "CameraUpVector"),
    ...(perspective ? { field_of_view: scale } : { view_to_world_scale: scale }),
  } };
}

/** Read incrementally so a highly compressed archive cannot allocate unbounded output. */
function readEntry(entry: JSZipObject, budget: { remaining: number }): Promise<Uint8Array> {
  return new Promise((resolve, reject) => {
    const chunks: Uint8Array[] = []; let length = 0;
    // JSZip exposes this streaming API at runtime; its entry typings omit it.
    const stream = (entry as JSZipObject & { internalStream(type: "uint8array"): JSZip.JSZipStreamHelper<Uint8Array> }).internalStream("uint8array");
    stream.on("data", chunk => {
      budget.remaining -= chunk.length;
      if (budget.remaining < 0) { stream.pause(); reject(new Error("BCF archive exceeds the 100 MB expanded size limit.")); return; }
      chunks.push(chunk); length += chunk.length;
    }).on("error", reject).on("end", () => {
      const result = new Uint8Array(length); let offset = 0;
      for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.length; }
      resolve(result);
    }).resume();
  });
}
function base64(data: Uint8Array): string {
  let binary = "";
  for (let start = 0; start < data.length; start += 8192) binary += String.fromCharCode(...data.subarray(start, start + 8192));
  return btoa(binary);
}
function relativeAsset(name: string): string {
  if (!name || name.startsWith("/") || name.includes("\\") || name.split("/").some(part => part === ".." || part === ".") || /^[a-z]+:/i.test(name)) throw new Error(`Invalid BCF asset path: ${name}`);
  return name;
}
export async function importBcfArchive(data: ArrayBuffer | Uint8Array): Promise<BcfIssue[]> {
  if (data.byteLength > MAX_COMPRESSED) throw new Error("BCF archive exceeds the 50 MB file limit.");
  const zip = await JSZip.loadAsync(data);
  const entries = Object.values(zip.files);
  if (entries.length > MAX_ENTRIES) throw new Error("BCF archive contains too many entries.");
  const budget = { remaining: MAX_EXPANDED };
  const files = new Map<string, Uint8Array>();
  for (const entry of entries) {
    if (entry.dir) continue;
    relativeAsset(entry.unsafeOriginalName ?? entry.name);
    files.set(entry.name, await readEntry(entry, budget));
  }
  const decoder = new TextDecoder();
  const xml = (name: string) => {
    const value = files.get(name);
    if (!value) throw new Error(`Missing BCF file: ${name}`);
    return parseBcfXml(decoder.decode(value));
  };
  if (xml("bcf.version").documentElement.getAttribute("VersionId") !== "2.1") throw new Error("Only BCF 2.1 archives are supported.");
  const issues: BcfIssue[] = [];
  const seen = new Set<string>();
  for (const name of files.keys()) {
    const match = /^([^/]+)\/markup\.bcf$/.exec(name);
    if (!match) continue;
    const folder = match[1]!;
    const doc = xml(name);
    const topic = doc.querySelector("Markup > Topic");
    const id = topic?.getAttribute("Guid") ?? "";
    if (!topic || !/^[a-zA-Z0-9_-]+$/.test(id) || seen.has(id)) throw new Error("Missing, invalid or duplicate BCF topic GUID.");
    seen.add(id);
    const title = content(topic, "Title");
    if (!title.trim()) throw new Error("BCF topic has no title.");
    const assets: Record<string, string> = {};
    for (const [path, bytes] of files) if (path.startsWith(`${folder}/`)) assets[path.slice(folder.length + 1)] = base64(bytes);
    let first: ReturnType<typeof viewpoint> = { components: {} };
    let screenshot: string | undefined;
    const references = Array.from(doc.querySelectorAll("Markup > Viewpoints[Guid], Viewpoints > ViewPoint"));
    for (const [index, ref] of references.entries()) {
      const viewpointName = content(ref, "Viewpoint");
      if (viewpointName) {
        const asset = relativeAsset(viewpointName);
        const parsed = viewpoint(xml(`${folder}/${asset}`));
        if (index === 0) first = parsed;
      }
      const snapshot = content(ref, "Snapshot");
      if (snapshot) {
        const image = files.get(`${folder}/${relativeAsset(snapshot)}`);
        if (!image) throw new Error(`Missing BCF file: ${snapshot}`);
        if (!/\.(png|jpe?g)$/i.test(snapshot)) throw new Error("BCF snapshots must be PNG or JPEG.");
        if (index === 0) screenshot = `data:image/${/\.png$/i.test(snapshot) ? "png" : "jpeg"};base64,${base64(image)}`;
      }
    }
    issues.push({
      id, title, createdAt: content(topic, "CreationDate") || new Date().toISOString(), pushState: "queued", screenshot,
      source: { specificationName: "BCF import" },
      mapping: {
        topic: { title, description: content(topic, "Description"), topic_type: topic.getAttribute("TopicType") ?? "Issue", topic_status: topic.getAttribute("TopicStatus") ?? "Open", priority: content(topic, "Priority") || "Normal", assigned_to: content(topic, "AssignedTo"), due_date: content(topic, "DueDate") || null, stage: content(topic, "Stage"), labels: Array.from(topic.querySelectorAll("Labels")).flatMap(el => el.children.length ? Array.from(el.querySelectorAll("Label")).map(label => label.textContent ?? "") : [el.textContent ?? ""]) },
        viewpoint: first, comment: { comment: Array.from(doc.querySelectorAll("Markup > Comment > Comment")).map(el => el.textContent ?? "").join("\n\n") },
      },
      archive: { files: assets },
    });
  }
  if (!issues.length) throw new Error("BCF archive contains no topics.");
  return issues;
}

/** Preserve comments, all viewpoints and attachments while updating editable topic fields. */
export function updateArchivedMarkup(xml: string, issue: BcfIssue): string {
  const doc = parseBcfXml(xml);
  const topic = doc.querySelector("Markup > Topic");
  if (!topic) throw new Error("Missing BCF topic.");
  topic.setAttribute("Guid", issue.id);
  topic.setAttribute("TopicStatus", issue.mapping.topic.topic_status ?? "Open");
  topic.setAttribute("TopicType", issue.mapping.topic.topic_type ?? "Issue");
  for (const [tag, value] of Object.entries({ Title: issue.mapping.topic.title, Description: issue.mapping.topic.description, Priority: issue.mapping.topic.priority, AssignedTo: issue.mapping.topic.assigned_to, DueDate: issue.mapping.topic.due_date, Stage: issue.mapping.topic.stage })) {
    let element = topic.querySelector(tag);
    if (value == null || value === "") { element?.remove(); continue; }
    if (!element) { element = doc.createElement(tag); topic.append(element); }
    element.textContent = value;
  }
  // Keep the schema sequence when an optional topic field has been added.
  const order = ["ReferenceLink", "Title", "Priority", "Index", "Labels", "CreationDate", "CreationAuthor", "ModifiedDate", "ModifiedAuthor", "DueDate", "AssignedTo", "Stage", "Description", "BimSnippet", "DocumentReference", "RelatedTopic"];
  const elements = Array.from(topic.children);
  elements.sort((a, b) => order.indexOf(a.localName) - order.indexOf(b.localName));
  for (const element of elements) topic.append(element);
  return new XMLSerializer().serializeToString(doc);
}
