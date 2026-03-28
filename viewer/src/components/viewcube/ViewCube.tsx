/**
 * ViewCube — Revit-style 3D navigation cube.
 *
 * Positioned top-right with compass ring (N/Z/O/W).
 * Clickable faces, edges, and corners for camera navigation.
 * Cube rotation syncs with the 3D camera via quaternion.
 */

import { useEffect, useRef, useCallback } from "react";
import "./ViewCube.css";

export type CubeFace =
  | "front"
  | "back"
  | "top"
  | "bottom"
  | "left"
  | "right";

/** Extended targets include edges and corners. */
export type CubeTarget =
  | CubeFace
  | "front-top"
  | "front-bottom"
  | "front-left"
  | "front-right"
  | "back-top"
  | "back-bottom"
  | "back-left"
  | "back-right"
  | "top-left"
  | "top-right"
  | "bottom-left"
  | "bottom-right"
  | "front-top-left"
  | "front-top-right"
  | "front-bottom-left"
  | "front-bottom-right"
  | "back-top-left"
  | "back-top-right"
  | "back-bottom-left"
  | "back-bottom-right";

interface ViewCubeProps {
  onNavigate?: (target: CubeTarget) => void;
  cameraQuaternion?: [number, number, number, number];
}

const EDGE = 14;
const CORNER = 14;

export function ViewCube({ onNavigate, cameraQuaternion }: ViewCubeProps) {
  const cubeRef = useRef<HTMLDivElement>(null);
  const compassRef = useRef<HTMLDivElement>(null);

  // Sync cube + compass rotation from camera quaternion
  useEffect(() => {
    if (!cameraQuaternion) return;

    const [qx, qy, qz, qw] = cameraQuaternion;

    // Quaternion → rotation matrix (transposed = inverse for camera-relative view)
    const m11 = 1 - 2 * (qy * qy + qz * qz);
    const m12 = 2 * (qx * qy - qz * qw);
    const m13 = 2 * (qx * qz + qy * qw);
    const m21 = 2 * (qx * qy + qz * qw);
    const m22 = 1 - 2 * (qx * qx + qz * qz);
    const m23 = 2 * (qy * qz - qx * qw);
    const m31 = 2 * (qx * qz - qy * qw);
    const m32 = 2 * (qy * qz + qx * qw);
    const m33 = 1 - 2 * (qx * qx + qy * qy);

    const matrix = `matrix3d(${m11},${m21},${m31},0,${m12},${m22},${m32},0,${m13},${m23},${m33},0,0,0,0,1)`;

    if (cubeRef.current) {
      cubeRef.current.style.transform = matrix;
    }

    // Compass rotates only around Y axis — extract yaw from matrix
    // atan2(m31, m11) gives the Y rotation
    if (compassRef.current) {
      const yaw = Math.atan2(m31, m11) * (180 / Math.PI);
      compassRef.current.style.transform = `rotateX(90deg) rotateZ(${-yaw}deg)`;
    }
  }, [cameraQuaternion]);

  const nav = useCallback(
    (target: CubeTarget) => {
      onNavigate?.(target);
    },
    [onNavigate]
  );

  // Edge insets: positioned along face edges
  const edgeStyle = (
    side: "top" | "bottom" | "left" | "right"
  ): React.CSSProperties => {
    const base: React.CSSProperties = { position: "absolute" };
    switch (side) {
      case "top":
        return { ...base, top: 0, left: CORNER, right: CORNER, height: EDGE };
      case "bottom":
        return {
          ...base,
          bottom: 0,
          left: CORNER,
          right: CORNER,
          height: EDGE,
        };
      case "left":
        return { ...base, top: CORNER, bottom: CORNER, left: 0, width: EDGE };
      case "right":
        return {
          ...base,
          top: CORNER,
          bottom: CORNER,
          right: 0,
          width: EDGE,
        };
    }
  };

  // Corner insets
  const cornerStyle = (
    v: "top" | "bottom",
    h: "left" | "right"
  ): React.CSSProperties => ({
    position: "absolute",
    [v]: 0,
    [h]: 0,
    width: CORNER,
    height: CORNER,
  });

  /** Render edge + corner hit zones for a face. */
  const faceOverlays = (
    face: CubeFace,
    adjacents: {
      top: CubeFace;
      bottom: CubeFace;
      left: CubeFace;
      right: CubeFace;
    }
  ) => (
    <>
      {/* Edge zones */}
      <div
        className="vc-edge"
        style={edgeStyle("top")}
        onClick={(e) => {
          e.stopPropagation();
          nav(`${face}-${adjacents.top}` as CubeTarget);
        }}
      />
      <div
        className="vc-edge"
        style={edgeStyle("bottom")}
        onClick={(e) => {
          e.stopPropagation();
          nav(`${face}-${adjacents.bottom}` as CubeTarget);
        }}
      />
      <div
        className="vc-edge"
        style={edgeStyle("left")}
        onClick={(e) => {
          e.stopPropagation();
          nav(`${face}-${adjacents.left}` as CubeTarget);
        }}
      />
      <div
        className="vc-edge"
        style={edgeStyle("right")}
        onClick={(e) => {
          e.stopPropagation();
          nav(`${face}-${adjacents.right}` as CubeTarget);
        }}
      />
      {/* Corner zones */}
      <div
        className="vc-corner"
        style={cornerStyle("top", "left")}
        onClick={(e) => {
          e.stopPropagation();
          nav(
            `${face}-${adjacents.top}-${adjacents.left}` as CubeTarget
          );
        }}
      />
      <div
        className="vc-corner"
        style={cornerStyle("top", "right")}
        onClick={(e) => {
          e.stopPropagation();
          nav(
            `${face}-${adjacents.top}-${adjacents.right}` as CubeTarget
          );
        }}
      />
      <div
        className="vc-corner"
        style={cornerStyle("bottom", "left")}
        onClick={(e) => {
          e.stopPropagation();
          nav(
            `${face}-${adjacents.bottom}-${adjacents.left}` as CubeTarget
          );
        }}
      />
      <div
        className="vc-corner"
        style={cornerStyle("bottom", "right")}
        onClick={(e) => {
          e.stopPropagation();
          nav(
            `${face}-${adjacents.bottom}-${adjacents.right}` as CubeTarget
          );
        }}
      />
    </>
  );

  return (
    <div className="viewcube-container">
      {/* Compass ring */}
      <div className="viewcube-compass">
        <div className="viewcube-compass-ring" ref={compassRef}>
          <span className="vc-dir vc-n">Z</span>
          <span className="vc-dir vc-s">N</span>
          <span className="vc-dir vc-e">O</span>
          <span className="vc-dir vc-w">W</span>
        </div>
      </div>

      {/* 3D Cube */}
      <div className="viewcube-scene">
        <div className="viewcube" ref={cubeRef}>
          {/* Front */}
          <div
            className="vc-face vc-front"
            onClick={() => nav("front")}
          >
            <span className="vc-label">VOOR</span>
            {faceOverlays("front", {
              top: "top",
              bottom: "bottom",
              left: "left",
              right: "right",
            })}
          </div>

          {/* Back */}
          <div
            className="vc-face vc-back"
            onClick={() => nav("back")}
          >
            <span className="vc-label">ACHTER</span>
            {faceOverlays("back", {
              top: "top",
              bottom: "bottom",
              left: "right",
              right: "left",
            })}
          </div>

          {/* Top */}
          <div
            className="vc-face vc-top"
            onClick={() => nav("top")}
          >
            <span className="vc-label">BOVEN</span>
            {faceOverlays("top", {
              top: "back",
              bottom: "front",
              left: "left",
              right: "right",
            })}
          </div>

          {/* Bottom */}
          <div
            className="vc-face vc-bottom"
            onClick={() => nav("bottom")}
          >
            <span className="vc-label">ONDER</span>
            {faceOverlays("bottom", {
              top: "front",
              bottom: "back",
              left: "left",
              right: "right",
            })}
          </div>

          {/* Left */}
          <div
            className="vc-face vc-left"
            onClick={() => nav("left")}
          >
            <span className="vc-label">LINKS</span>
            {faceOverlays("left", {
              top: "top",
              bottom: "bottom",
              left: "front",
              right: "back",
            })}
          </div>

          {/* Right */}
          <div
            className="vc-face vc-right"
            onClick={() => nav("right")}
          >
            <span className="vc-label">RECHTS</span>
            {faceOverlays("right", {
              top: "top",
              bottom: "bottom",
              left: "back",
              right: "front",
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
