import { Box3, MathUtils, OrthographicCamera, PerspectiveCamera, Sphere, Vector3 } from "three";
import type CameraControls from "camera-controls";

type NavigationCamera = { three: PerspectiveCamera | OrthographicCamera; controls: CameraControls };
type Projection = "Perspective" | "Orthographic";
const directions: Record<string, [number, number, number]> = {
  front: [0, 0, 1], back: [0, 0, -1], top: [0, 1, 0], bottom: [0, -1, 0],
  left: [-1, 0, 0], right: [1, 0, 0],
};

/** Change orientation around the current focus without changing view scale. */
export async function navigateView(cam: NavigationCamera, target: string): Promise<void> {
  const direction = new Vector3();
  for (const part of target.split("-")) {
    const axis = directions[part];
    if (!axis) return;
    direction.add(new Vector3(...axis));
  }
  if (!direction.lengthSq()) return;
  direction.normalize();
  const focus = cam.controls.getTarget(new Vector3());
  const distance = Math.max(cam.controls.getPosition(new Vector3()).distanceTo(focus), .01);
  const position = direction.clone().multiplyScalar(distance).add(focus);
  cam.three.up.set(0, 1, 0);
  if (Math.abs(direction.y) > .9999) cam.three.up.set(0, 0, -Math.sign(direction.y));
  cam.controls.updateCameraUp();
  await cam.controls.setLookAt(position.x, position.y, position.z, focus.x, focus.y, focus.z, false);
}

/** Fit a padded bounding sphere: preserves orientation and handles both projections. */
export async function fitBounds(cam: NavigationCamera, bounds: Box3): Promise<void> {
  if (bounds.isEmpty()) return;
  const sphere = bounds.getBoundingSphere(new Sphere());
  sphere.radius = Math.max(sphere.radius * 1.12, .01);
  const distance = cam.three instanceof PerspectiveCamera
    ? cam.controls.getDistanceToFitSphere(sphere.radius)
    : Math.max(cam.controls.distance, sphere.radius * 2 + cam.three.near);
  // Controller defaults target small scenes; large civil models must still fit.
  cam.controls.maxDistance = Math.max(cam.controls.maxDistance, distance * 2);
  if (cam.three instanceof OrthographicCamera) {
    const zoom = Math.min(cam.three.right - cam.three.left, cam.three.top - cam.three.bottom) / (2 * sphere.radius);
    cam.controls.minZoom = Math.min(cam.controls.minZoom, zoom);
    await cam.controls.dollyTo(distance, false);
  }
  cam.three.far = Math.max(cam.three.far, distance + sphere.radius * 2);
  cam.three.updateProjectionMatrix();
  await cam.controls.fitToSphere(sphere, false);
}

/** Preserve framing and camera roll across the library's projection defaults. */
export async function switchProjection(cam: NavigationCamera & { projection: { current: Projection; set: (projection: Projection) => Promise<void> } }, projection: Projection): Promise<void> {
  if (cam.projection.current === projection) return;
  cam.controls.update(0);
  const focus = cam.controls.getTarget(new Vector3());
  const offset = cam.controls.getPosition(new Vector3()).sub(focus);
  const oldDistance = Math.max(offset.length(), .01);
  const up = cam.three.up.clone();
  const far = cam.three.far;
  const near = cam.three.near;
  const height = cam.three instanceof PerspectiveCamera
    ? 2 * oldDistance * Math.tan(MathUtils.degToRad(cam.three.getEffectiveFOV()) / 2)
    : (cam.three.top - cam.three.bottom) / cam.three.zoom;
  await cam.projection.set(projection);
  cam.three.up.copy(up);
  cam.controls.updateCameraUp();
  let distance = oldDistance;
  if (cam.three instanceof OrthographicCamera) {
    const zoom = (cam.three.top - cam.three.bottom) / height;
    cam.controls.minZoom = Math.min(cam.controls.minZoom, zoom);
    cam.controls.maxZoom = Math.max(cam.controls.maxZoom, zoom);
    await cam.controls.zoomTo(zoom, false);
  } else {
    distance = height / (2 * Math.tan(MathUtils.degToRad(cam.three.getEffectiveFOV()) / 2));
  }
  cam.controls.maxDistance = Math.max(cam.controls.maxDistance, distance * 2);
  const eye = offset.normalize().multiplyScalar(distance).add(focus);
  cam.three.near = Math.min(cam.three.near, near);
  cam.three.far = Math.max(cam.three.far, far, distance * 2);
  cam.three.updateProjectionMatrix();
  await cam.controls.setLookAt(eye.x, eye.y, eye.z, focus.x, focus.y, focus.z, false);
}
