import { describe, expect, it } from "vitest";
import * as THREE from "three";
import CameraControls from "camera-controls";
import type { OrthoPerspectiveCamera } from "@thatopen/components";
// Exercise the browser ESM build; the Node CJS build has different dependency interop.
// @ts-expect-error The package supplies declarations only at its root.
import { ProjectionManager } from "../../node_modules/@thatopen/components/dist/index.mjs";
import { fitBounds, navigateView, switchProjection } from "./viewNavigation";

CameraControls.install({ THREE });

describe("view navigation", () => {
  for (const target of ["top", "bottom", "front-top-right"]) it(`preserves focus, roll and visible scale across real projection switches: ${target}`, async () => {
    const threePersp = new THREE.PerspectiveCamera(50, 1.5, .1, 1000);
    const threeOrtho = new THREE.OrthographicCamera(-15, 15, 10, -10, .1, 1000);
    const controls = new CameraControls(threePersp);
    const component = { three: threePersp as THREE.PerspectiveCamera | THREE.OrthographicCamera, threePersp, threeOrtho, controls, mode: { id: "Orbit" }, currentWorld: { renderer: { getSize: () => new THREE.Vector2(900, 600) } } };
    const projection = new ProjectionManager(component as unknown as OrthoPerspectiveCamera);
    projection.onChanged.add((camera: THREE.PerspectiveCamera | THREE.OrthographicCamera) => { component.three = camera; });
    const cam = Object.assign(component, { projection });
    await controls.setLookAt(10, 20, 30, 4, 5, 6, false);
    await navigateView(cam, target);
    if (target === "front-top-right") {
      component.three.up.set(1, 1, 0).normalize();
      controls.updateCameraUp();
    }
    controls.update(1);
    const before = component.three.getWorldDirection(new THREE.Vector3());
    const up = component.three.up.clone();
    const height = 2 * controls.distance * Math.tan(THREE.MathUtils.degToRad(threePersp.getEffectiveFOV()) / 2);
    component.three.far = 20000;
    await switchProjection(cam, "Orthographic");
    controls.update(1);
    expect(component.three.up.distanceTo(up)).toBeLessThan(1e-8);
    expect(component.three.getWorldDirection(new THREE.Vector3()).dot(before)).toBeCloseTo(1, 5);
    expect((threeOrtho.top - threeOrtho.bottom) / threeOrtho.zoom).toBeCloseTo(height);
    expect(threeOrtho.far).toBeGreaterThanOrEqual(20000);
    await controls.zoomTo(threeOrtho.zoom * 2, false);
    controls.update(1);
    await switchProjection(cam, "Perspective");
    controls.update(1);
    expect(controls.getTarget(new THREE.Vector3()).toArray()).toEqual([4, 5, 6]);
    expect(component.three.getWorldDirection(new THREE.Vector3()).dot(before)).toBeCloseTo(1, 5);
    expect(component.three.up.distanceTo(up)).toBeLessThan(1e-8);
    expect(2 * controls.distance * Math.tan(THREE.MathUtils.degToRad(threePersp.getEffectiveFOV()) / 2)).toBeCloseTo(height / 2);
    controls.dispose();
  });
  for (const orthographic of [false, true]) it(`fits large models beyond default controller limits: orthographic=${orthographic}`, async () => {
    const three = orthographic ? new THREE.OrthographicCamera(-10, 10, 10, -10, .1, 1000) : new THREE.PerspectiveCamera(50, 1, .1, 1000);
    const controls = new CameraControls(three);
    controls.maxDistance = 300;
    await controls.setLookAt(0, 0, 10, 0, 0, 0, false);
    await fitBounds({ three, controls }, new THREE.Box3(new THREE.Vector3(-2500, -1500, -1000), new THREE.Vector3(2500, 1500, 1000)));
    controls.update(1);
    three.updateMatrixWorld();
    for (const x of [-2500, 2500]) for (const y of [-1500, 1500]) for (const z of [-1000, 1000]) {
      const p = new THREE.Vector3(x, y, z).project(three);
      expect(Math.max(Math.abs(p.x), Math.abs(p.y), Math.abs(p.z))).toBeLessThan(1);
    }
    controls.dispose();
  });
  it("preserves orbit focus and distance across top, bottom and side views", async () => {
    const three = new THREE.PerspectiveCamera(50, 1, .01, 10000);
    const controls = new CameraControls(three);
    await controls.setLookAt(14, 25, 36, 4, 5, 6, false);
    controls.update(1);
    const distance = controls.distance;
    for (const target of ["top", "front", "bottom", "right", "front-top-right"]) {
      await navigateView({ three, controls }, target);
      controls.update(1);
      expect(controls.getTarget(new THREE.Vector3()).toArray()).toEqual([4, 5, 6]);
      expect(controls.distance).toBeCloseTo(distance);
      expect(three.quaternion.toArray().every(Number.isFinite)).toBe(true);
      const expected = new THREE.Vector3(target.includes("right") ? 1 : 0, target.includes("top") ? 1 : target.includes("bottom") ? -1 : 0, target.includes("front") ? 1 : 0).normalize();
      expect(three.getWorldDirection(new THREE.Vector3()).dot(expected)).toBeCloseTo(-1, 4);
    }
    controls.dispose();
  });

  it("preserves orthographic scale on orientation changes", async () => {
    const three = new THREE.OrthographicCamera(-20, 20, 10, -10, .01, 10000);
    const controls = new CameraControls(three);
    await controls.setLookAt(10, 10, 10, 0, 0, 0, false);
    await controls.zoomTo(4, false);
    await navigateView({ three, controls }, "top");
    controls.update(1);
    expect(three.zoom).toBeCloseTo(4);
    controls.dispose();
  });

  for (const orthographic of [false, true]) for (const aspect of [.35, 2.5]) {
    it(`fits all bounds and preserves orientation: orthographic=${orthographic}, aspect=${aspect}`, async () => {
      const three = orthographic ? new THREE.OrthographicCamera(-10 * aspect, 10 * aspect, 10, -10, .01, 10000) : new THREE.PerspectiveCamera(50, aspect, .01, 10000);
      const controls = new CameraControls(three);
      await controls.setLookAt(20, 15, 30, 0, 0, 0, false);
      controls.update(1);
      const direction = three.getWorldDirection(new THREE.Vector3());
      const box = new THREE.Box3(new THREE.Vector3(-50, -10, -5), new THREE.Vector3(50, 10, 5));
      await fitBounds({ three, controls }, box);
      controls.update(1);
      three.updateMatrixWorld();
      expect(three.getWorldDirection(new THREE.Vector3()).dot(direction)).toBeCloseTo(1);
      for (const x of [-50, 50]) for (const y of [-10, 10]) for (const z of [-5, 5]) {
        const projected = new THREE.Vector3(x, y, z).project(three);
        expect(Math.abs(projected.x)).toBeLessThan(1);
        expect(Math.abs(projected.y)).toBeLessThan(1);
        expect(Math.abs(projected.z)).toBeLessThan(1);
      }
      controls.dispose();
    });
  }
});
