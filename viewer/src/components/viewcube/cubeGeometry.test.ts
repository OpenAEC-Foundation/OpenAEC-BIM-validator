import { describe, expect, it } from "vitest";
import { Quaternion, Vector3 } from "three";
import { cubeFacets, projectCube } from "./cubeGeometry";

describe("orientation cube geometry", () => {
  it("has 26 unique targets with closed shared boundaries", () => {
    expect(cubeFacets).toHaveLength(26);
    expect(new Set(cubeFacets.map(f => f.target)).size).toBe(26);
    expect(cubeFacets.filter(f => f.kind === "face")).toHaveLength(6);
    expect(cubeFacets.filter(f => f.kind === "edge")).toHaveLength(12);
    expect(cubeFacets.filter(f => f.kind === "corner")).toHaveLength(8);
    const edges = new Map<string, number>();
    for (const face of cubeFacets) for (let i = 0; i < face.vertices.length; i++) {
      const key = [face.vertices[i]!.join(","), face.vertices[(i + 1) % face.vertices.length]!.join(",")].sort().join("|");
      edges.set(key, (edges.get(key) ?? 0) + 1);
    }
    expect([...edges.values()].every(n => n === 2)).toBe(true);
  });
  it("shows the front face for an identity camera and culls rear faces", () => {
    expect(projectCube([0, 0, 0, 1]).filter(f => f.kind === "face").map(f => f.target)).toEqual(["front"]);
  });
  it("uses the inverse camera rotation for a right-side view", () => {
    const q = new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), Math.PI / 2);
    expect(projectCube(q.toArray()).filter(f => f.kind === "face").map(f => f.target)).toEqual(["right"]);
    expect(projectCube(q.toArray()).every(f => f.points.every(p => p.every(Number.isFinite)))).toBe(true);
  });
});
