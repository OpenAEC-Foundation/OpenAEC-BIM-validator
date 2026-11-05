import { useEffect, useState } from "react";
import { Button, IconButton, Select } from "@openaec/ui-react";
import { useTranslation } from "react-i18next";
import type { ViewerEngine } from "../../engine/ViewerEngine";
import { ViewCube } from "./ViewCube";
import type { QuaternionTuple } from "./cubeGeometry";

type NavigationEngine = Pick<ViewerEngine, "getCameraQuaternion" | "getProjection" | "setProjection" | "navigateToFace" | "resetView" | "fitToAllModels">;
const faces = ["front", "back", "left", "right", "top", "bottom", "front-top-right"];

/** Only this small overlay observes camera frames; the model panel stays untouched. */
export function ViewNavigation({ engine }: { engine: NavigationEngine }) {
  const { t } = useTranslation("common");
  const [state, setState] = useState(() => ({ q: engine.getCameraQuaternion() ?? [0, 0, 0, 1] as QuaternionTuple, projection: engine.getProjection() }));
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let frame: number;
    let previous = { q: engine.getCameraQuaternion(), projection: engine.getProjection() };
    const sync = () => {
      const q = engine.getCameraQuaternion();
      const projection = engine.getProjection();
      if (q && (!previous.q || q.some((v, i) => Math.abs(v - previous.q![i]!) > 1e-6) || projection !== previous.projection)) {
        previous = { q, projection };
        setState({ q, projection });
      }
      frame = requestAnimationFrame(sync);
    };
    frame = requestAnimationFrame(sync);
    return () => cancelAnimationFrame(frame);
  }, [engine]);
  const run = async (action: () => void | Promise<void>) => {
    setError(false);
    try { await action(); } catch { setError(true); }
  };
  return (
    <div className="view-navigation" onKeyDown={event => event.stopPropagation()}>
      <ViewCube cameraQuaternion={state.q} onNavigate={target => { void run(() => engine.navigateToFace(target)); }} />
      <div className="view-navigation__controls">
        <div className="view-navigation__actions">
          <IconButton icon="view.reset-camera" label={t("viewer.home")} onClick={() => { void run(() => engine.resetView()); }} />
          <IconButton icon="view.fit" label={t("viewer.fit")} onClick={() => { void run(() => engine.fitToAllModels()); }} />
          <Button compact kind="quiet" className="view-navigation__projection" aria-label={t("viewer.toggleProjection")} title={t("viewer.toggleProjection")} aria-pressed={state.projection === "Orthographic"} disabled={busy}
            onClick={() => {
              setBusy(true);
              void run(async () => {
                try { await engine.setProjection(state.projection === "Perspective" ? "Orthographic" : "Perspective"); }
                finally { setBusy(false); }
              });
            }}>
            {state.projection === "Perspective" ? t("viewer.perspectiveShort") : t("viewer.orthographicShort")}
          </Button>
        </div>
        <Select compact label={t("viewer.standardView")} value="" options={[
          { value: "", label: t("viewer.chooseView") },
          ...faces.map(face => ({ value: face, label: face === "front-top-right" ? t("viewer.isometric") : t(`viewer.${face}`) })),
        ]} onChange={event => { const target = event.target.value; if (target) void run(() => engine.navigateToFace(target)); }} />
        {error && <p role="alert" className="view-navigation__error">{t("viewer.navigationError")}</p>}
      </div>
    </div>
  );
}
