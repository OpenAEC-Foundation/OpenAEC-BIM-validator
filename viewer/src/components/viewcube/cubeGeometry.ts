import { Quaternion, Vector3 } from "three";

export type CubeFace = "front" | "back" | "top" | "bottom" | "left" | "right";
export type CubeTarget = string;
export type QuaternionTuple = [number, number, number, number];
type Point = [number, number, number];
interface Facet {
  target: CubeTarget;
  kind: "face" | "edge" | "corner";
  normal: Point;
  vertices: Point[];
}

// The convex hull of signed permutations gives matching bevels without overlays.
const vertices: Vector3[] = [];
for (const p of [[1, .85, .57], [1, .57, .85], [.85, 1, .57], [.85, .57, 1], [.57, 1, .85], [.57, .85, 1]]) {
  for (const x of [-1, 1]) for (const y of [-1, 1]) for (const z of [-1, 1]) vertices.push(new Vector3(p[0]! * x, p[1]! * y, p[2]! * z));
}

export const cubeFacets: Facet[] = [];
for (const x of [-1, 0, 1]) for (const y of [-1, 0, 1]) for (const z of [-1, 0, 1]) {
  const count = [x, y, z].filter(Boolean).length;
  if (!count) continue;
  const normal = new Vector3(x, y, z).normalize();
  const max = Math.max(...vertices.map(v => v.dot(normal)));
  const ring = vertices.filter(v => Math.abs(v.dot(normal) - max) < 1e-8);
  const center = normal.clone().multiplyScalar(max);
  const u = new Vector3(Math.abs(normal.y) < .9 ? 0 : 1, Math.abs(normal.y) < .9 ? 1 : 0, 0).cross(normal).normalize();
  const v = normal.clone().cross(u);
  ring.sort((a, b) => Math.atan2(a.clone().sub(center).dot(v), a.clone().sub(center).dot(u)) - Math.atan2(b.clone().sub(center).dot(v), b.clone().sub(center).dot(u)));
  cubeFacets.push({
    target: [z > 0 ? "front" : z < 0 ? "back" : "", y > 0 ? "top" : y < 0 ? "bottom" : "", x > 0 ? "right" : x < 0 ? "left" : ""].filter(Boolean).join("-"),
    kind: count === 1 ? "face" : count === 2 ? "edge" : "corner",
    normal: normal.toArray(), vertices: ring.map(p => p.toArray()),
  });
}

/** Orthographic overlay projection in camera space; rear facets are not interactive. */
export function projectCube(cameraQuaternion: QuaternionTuple) {
  const inverse = new Quaternion(...cameraQuaternion).normalize().invert();
  return cubeFacets.flatMap(facet => {
    const normal = new Vector3(...facet.normal).applyQuaternion(inverse);
    if (normal.z <= .025) return [];
    const transformed = facet.vertices.map(v => new Vector3(...v).applyQuaternion(inverse));
    const center = transformed.reduce((sum, p) => sum.add(p), new Vector3()).divideScalar(transformed.length);
    return [{ ...facet, points: transformed.map(p => [70 + p.x * 30, 65 - p.y * 30]), label: [70 + center.x * 30, 65 - center.y * 30], depth: center.z, facing: normal.z }];
  }).sort((a, b) => a.depth - b.depth);
}
