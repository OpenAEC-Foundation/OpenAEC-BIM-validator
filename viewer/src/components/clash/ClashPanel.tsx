/**
 * ClashPanel — clash detection between loaded models (or within one).
 *
 * Uploads the loaded model bytes to the async clash endpoint, then lists
 * the clashes; clicking A/B selects the element in 3D.
 */

import { useCallback, useMemo, useState } from "react";

import { useStore } from "../../store";
import { getModelBytes } from "../../engine/modelCache";
import { runClash, type ClashResultBody } from "../../api/toolsApi";

import "./ClashPanel.css";

export function ClashPanel() {
  const project = useStore((s) => s.project);
  const selectElement = useStore((s) => s.selectElement);

  const loadedModels = useMemo(
    () => project?.models.filter((m) => m.loadState === "loaded") ?? [],
    [project]
  );

  const [modelA, setModelA] = useState<string>("");
  const [modelB, setModelB] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ClashResultBody | null>(null);

  const effectiveA = modelA || loadedModels[0]?.fileName || "";

  const handleRun = useCallback(async () => {
    if (!effectiveA) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const bytesA = await getModelBytes(effectiveA);
      if (!bytesA) throw new Error(`Geen bytes voor ${effectiveA}`);
      let b: { bytes: ArrayBuffer; fileName: string } | null = null;
      if (modelB && modelB !== effectiveA) {
        const bytesB = await getModelBytes(modelB);
        if (!bytesB) throw new Error(`Geen bytes voor ${modelB}`);
        b = { bytes: bytesB, fileName: modelB };
      }
      const res = await runClash(
        { bytes: bytesA, fileName: effectiveA },
        b
      );
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Clash-detectie mislukt");
    } finally {
      setRunning(false);
    }
  }, [effectiveA, modelB]);

  if (loadedModels.length === 0) {
    return (
      <div className="empty-state">
        <p className="empty-state__text">
          Upload eerst een IFC model voor clash-detectie
        </p>
      </div>
    );
  }

  return (
    <div className="clash-panel">
      <div className="clash-panel__config">
        <h3 className="clash-panel__heading">CLASH DETECTIE</h3>

        <label className="clash-panel__label">
          Model A
          <select
            className="clash-panel__select"
            value={effectiveA}
            onChange={(e) => setModelA(e.target.value)}
          >
            {loadedModels.map((m) => (
              <option key={m.id} value={m.fileName}>
                {m.fileName}
              </option>
            ))}
          </select>
        </label>

        <label className="clash-panel__label">
          Model B (optioneel — leeg = binnen model A)
          <select
            className="clash-panel__select"
            value={modelB}
            onChange={(e) => setModelB(e.target.value)}
          >
            <option value="">— binnen model A —</option>
            {loadedModels
              .filter((m) => m.fileName !== effectiveA)
              .map((m) => (
                <option key={m.id} value={m.fileName}>
                  {m.fileName}
                </option>
              ))}
          </select>
        </label>

        <button
          type="button"
          className="clash-panel__btn clash-panel__btn--primary"
          onClick={handleRun}
          disabled={running || !effectiveA}
        >
          {running ? "Bezig met detectie…" : "Detecteer clashes"}
        </button>

        {error && <p className="clash-panel__error">{error}</p>}
      </div>

      {result && (
        <div className="clash-panel__results">
          <p className="clash-panel__summary">
            {result.clash_count === 0
              ? "Geen clashes gevonden"
              : `${result.clash_count} clash${
                  result.clash_count === 1 ? "" : "es"
                } gevonden`}
            {result.results_omitted > 0 &&
              ` (${result.results_omitted} niet getoond)`}
          </p>

          <ul className="clash-panel__list">
            {result.clashes.map((clash, i) => (
              <li key={`${clash.a_global_id}-${clash.b_global_id}-${i}`}
                className="clash-panel__item"
              >
                <span className="clash-panel__type">{clash.type}</span>
                <button
                  type="button"
                  className="clash-panel__element"
                  title={`Selecteer ${clash.a_name}`}
                  onClick={() => selectElement(clash.a_global_id, true)}
                >
                  {clash.a_ifc_class}: {clash.a_name}
                </button>
                <span className="clash-panel__vs">×</span>
                <button
                  type="button"
                  className="clash-panel__element"
                  title={`Selecteer ${clash.b_name}`}
                  onClick={() => selectElement(clash.b_global_id, true)}
                >
                  {clash.b_ifc_class}: {clash.b_name}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
