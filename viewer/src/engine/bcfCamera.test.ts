import { describe, it, expect, vi } from "vitest";
import * as THREE from "three";
import CameraControls from "camera-controls";
import { restoreBcfCamera } from "./bcfCamera";
CameraControls.install({ THREE });
describe("BCF orthographic camera", () => {
  it("retains the imported visible height after the next controller frame", async () => {
    const camera = new THREE.OrthographicCamera(-10, 10, 10, -10, .1, 1000);
    const controls = new CameraControls(camera);
    const projection = { set: vi.fn(async () => {}) };
    await restoreBcfCamera({ three: camera, controls, projection } as unknown as Parameters<typeof restoreBcfCamera>[0], { type: "orthogonal", position: { x: 1, y: 2, z: 3 }, direction: { x: 0, y: 0, z: -1 }, up: { x: 0, y: 1, z: 0 }, viewToWorldScale: 40 });
    controls.update(1 / 60);
    expect((camera.top - camera.bottom) / camera.zoom).toBeCloseTo(40);
    expect(projection.set).toHaveBeenCalledWith("Orthographic");
    controls.dispose();
  });
});
