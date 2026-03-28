/**
 * ViewCube — 3D navigation cube overlay.
 *
 * Renders a CSS 3D cube in the top-left corner of the viewer.
 * Clicking a face animates the camera to that orientation.
 * The cube rotates to reflect the current camera orientation.
 */

import { useEffect, useRef, useCallback } from "react";
import "./ViewCube.css";

interface ViewCubeProps {
  /** Callback to navigate camera. Receives eye position relative to target. */
  onFaceClick?: (face: CubeFace) => void;
  /** Current camera quaternion as [x, y, z, w] for syncing cube rotation. */
  cameraQuaternion?: [number, number, number, number];
}

export type CubeFace =
  | "front"
  | "back"
  | "top"
  | "bottom"
  | "left"
  | "right";

const FACE_LABELS: Record<CubeFace, { nl: string; en: string }> = {
  front: { nl: "Voor", en: "Front" },
  back: { nl: "Achter", en: "Back" },
  top: { nl: "Boven", en: "Top" },
  bottom: { nl: "Onder", en: "Bottom" },
  left: { nl: "Links", en: "Left" },
  right: { nl: "Rechts", en: "Right" },
};

export function ViewCube({ onFaceClick, cameraQuaternion }: ViewCubeProps) {
  const cubeRef = useRef<HTMLDivElement>(null);

  // Update cube rotation from camera quaternion
  useEffect(() => {
    if (!cubeRef.current || !cameraQuaternion) return;

    const [qx, qy, qz, qw] = cameraQuaternion;

    // Convert quaternion to rotation matrix for CSS
    // We invert the camera rotation to show the cube from the camera's perspective
    const m11 = 1 - 2 * (qy * qy + qz * qz);
    const m12 = 2 * (qx * qy - qz * qw);
    const m13 = 2 * (qx * qz + qy * qw);
    const m21 = 2 * (qx * qy + qz * qw);
    const m22 = 1 - 2 * (qx * qx + qz * qz);
    const m23 = 2 * (qy * qz - qx * qw);
    const m31 = 2 * (qx * qz - qy * qw);
    const m32 = 2 * (qy * qz + qx * qw);
    const m33 = 1 - 2 * (qx * qx + qy * qy);

    // CSS matrix3d uses column-major order, and we need to invert (transpose for rotation)
    const matrix = `matrix3d(${m11},${m21},${m31},0,${m12},${m22},${m32},0,${m13},${m23},${m33},0,0,0,0,1)`;
    cubeRef.current.style.transform = matrix;
  }, [cameraQuaternion]);

  const handleClick = useCallback(
    (face: CubeFace) => {
      onFaceClick?.(face);
    },
    [onFaceClick]
  );

  return (
    <div className="viewcube-container">
      <div className="viewcube-scene">
        <div className="viewcube" ref={cubeRef}>
          <div
            className="viewcube-face viewcube-front"
            onClick={() => handleClick("front")}
          >
            {FACE_LABELS.front.nl}
          </div>
          <div
            className="viewcube-face viewcube-back"
            onClick={() => handleClick("back")}
          >
            {FACE_LABELS.back.nl}
          </div>
          <div
            className="viewcube-face viewcube-top"
            onClick={() => handleClick("top")}
          >
            {FACE_LABELS.top.nl}
          </div>
          <div
            className="viewcube-face viewcube-bottom"
            onClick={() => handleClick("bottom")}
          >
            {FACE_LABELS.bottom.nl}
          </div>
          <div
            className="viewcube-face viewcube-left"
            onClick={() => handleClick("left")}
          >
            {FACE_LABELS.left.nl}
          </div>
          <div
            className="viewcube-face viewcube-right"
            onClick={() => handleClick("right")}
          >
            {FACE_LABELS.right.nl}
          </div>
        </div>
      </div>
    </div>
  );
}
