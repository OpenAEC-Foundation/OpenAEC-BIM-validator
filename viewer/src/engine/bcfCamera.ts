import * as THREE from "three";
import type { OrthoPerspectiveCamera } from "@thatopen/components";
import type { BcfCameraState } from "../types/bcf";

/** Restore BCF projection, orientation and scale through the camera controller. */
export async function restoreBcfCamera(cam: Pick<OrthoPerspectiveCamera, "three" | "controls" | "projection">, state: BcfCameraState): Promise<void> {
    const { position: p, direction: d } = state;
    await cam.projection.set(state.type === "orthogonal" ? "Orthographic" : "Perspective");
    cam.three.up.set(state.up.x, state.up.y, state.up.z).normalize();
    cam.controls.updateCameraUp();
    if (cam.three instanceof THREE.PerspectiveCamera && state.fieldOfView) {
      cam.three.fov = state.fieldOfView;
      cam.three.updateProjectionMatrix();
    }
    if (cam.three instanceof THREE.OrthographicCamera && state.viewToWorldScale) {
      await cam.controls.zoomTo((cam.three.top - cam.three.bottom) / state.viewToWorldScale, false);
    }


    // Compute a target point at a reasonable distance along the direction
    const dist = 10; // arbitrary look-at distance
    await cam.controls.setLookAt(
      p.x,
      p.y,
      p.z,
      p.x + d.x * dist,
      p.y + d.y * dist,
      p.z + d.z * dist
    );
}
