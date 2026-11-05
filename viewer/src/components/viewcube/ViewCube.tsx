import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { projectCube, type CubeTarget, type QuaternionTuple } from "./cubeGeometry";
import "./ViewCube.css";

export type { CubeTarget, CubeFace } from "./cubeGeometry";
interface ViewCubeProps {
  onNavigate: (target: CubeTarget) => void;
  cameraQuaternion: QuaternionTuple;
}

export function ViewCube({ onNavigate, cameraQuaternion }: ViewCubeProps) {
  const { t } = useTranslation("common");
  const facets = useMemo(() => projectCube(cameraQuaternion), [cameraQuaternion]);
  return (
    <svg className="viewcube" viewBox="0 0 140 130" role="group" aria-label={t("viewer.orientation")}>
      {facets.map(facet => {
        const label = facet.target.split("-").map(part => t(`viewer.${part}`)).join(" · ");
        return (
          <g key={facet.target}>
            <polygon
              className={`viewcube__facet viewcube__facet--${facet.kind}`}
              points={facet.points.map(p => p.join(",")).join(" ")}
              role="button" tabIndex={0} aria-label={label}
              onClick={() => onNavigate(facet.target)}
              onKeyDown={event => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  event.stopPropagation();
                  onNavigate(facet.target);
                }
              }}
            ><title>{label}</title></polygon>
            {facet.kind === "face" && facet.facing > .3 && (
              <text className="viewcube__label" x={facet.label[0]} y={facet.label[1]} aria-hidden="true">{label}</text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
