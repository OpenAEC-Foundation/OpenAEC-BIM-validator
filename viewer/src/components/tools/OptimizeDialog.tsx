/**
 * OptimizeDialog — run the IFC optimizer on a loaded model.
 *
 * Selectable passes (all on by default), then a change report with the
 * size delta and a download button for the optimized file. The original
 * model is never modified.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import Modal from "../chrome/Modal";
import { useStore } from "../../store";
import { getModelBytes } from "../../engine/modelCache";
import {
  listOptimizePasses,
  runOptimize,
  type OptimizeJobResult,
  type OptimizePassInfo,
} from "../../api/toolsApi";

import "./OptimizeDialog.css";

interface OptimizeDialogProps {
  open: boolean;
  onClose: () => void;
}

function formatBytes(n: number): string {
  if (n >= 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  if (n >= 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${n} B`;
}

export function OptimizeDialog({ open, onClose }: OptimizeDialogProps) {
  const project = useStore((s) => s.project);

  const loadedModels = useMemo(
    () => project?.models.filter((m) => m.loadState === "loaded") ?? [],
    [project]
  );

  const [passes, setPasses] = useState<OptimizePassInfo[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [model, setModel] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OptimizeJobResult | null>(null);

  const effectiveModel = model || loadedModels[0]?.fileName || "";

  useEffect(() => {
    if (!open) return;
    setResult(null);
    setError(null);
    listOptimizePasses()
      .then((p) => {
        setPasses(p);
        setSelected(new Set(p.map((x) => x.name)));
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Kon passes niet laden")
      );
  }, [open]);

  const togglePass = useCallback((name: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }, []);

  const handleRun = useCallback(async () => {
    if (!effectiveModel || selected.size === 0) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const bytes = await getModelBytes(effectiveModel);
      if (!bytes) throw new Error(`Geen bytes voor ${effectiveModel}`);
      const res = await runOptimize(bytes, effectiveModel, [...selected]);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Optimalisatie mislukt");
    } finally {
      setRunning(false);
    }
  }, [effectiveModel, selected]);

  const sizeDelta = result
    ? result.report.size_before - result.report.size_after
    : 0;

  return (
    <Modal open={open} onClose={onClose} title="IFC Optimaliseren" width={520}>
      <div className="optimize-dialog">
        {loadedModels.length === 0 ? (
          <p className="optimize-dialog__empty">
            Upload eerst een IFC model om te optimaliseren.
          </p>
        ) : (
          <>
            {loadedModels.length > 1 && (
              <label className="optimize-dialog__label">
                Model
                <select
                  className="optimize-dialog__select"
                  value={effectiveModel}
                  onChange={(e) => setModel(e.target.value)}
                  disabled={running}
                >
                  {loadedModels.map((m) => (
                    <option key={m.id} value={m.fileName}>
                      {m.fileName}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <div className="optimize-dialog__passes">
              {passes.map((pass) => (
                <label key={pass.name} className="optimize-dialog__pass">
                  <input
                    type="checkbox"
                    checked={selected.has(pass.name)}
                    onChange={() => togglePass(pass.name)}
                    disabled={running}
                  />
                  <span>
                    <strong>{pass.title}</strong>
                    <br />
                    <small>{pass.description}</small>
                  </span>
                </label>
              ))}
            </div>

            <button
              type="button"
              className="optimize-dialog__btn optimize-dialog__btn--primary"
              onClick={handleRun}
              disabled={running || selected.size === 0 || !effectiveModel}
            >
              {running ? "Bezig met optimaliseren…" : "Optimaliseer"}
            </button>

            {error && <p className="optimize-dialog__error">{error}</p>}

            {result && (
              <div className="optimize-dialog__report">
                <p className="optimize-dialog__delta">
                  {formatBytes(result.report.size_before)} →{" "}
                  {formatBytes(result.report.size_after)}
                  {sizeDelta > 0 &&
                    ` (−${formatBytes(sizeDelta)}, ${(
                      (sizeDelta / result.report.size_before) *
                      100
                    ).toFixed(1)}%)`}
                </p>
                <ul className="optimize-dialog__pass-results">
                  {result.report.passes.map((p) => (
                    <li key={p.name}>
                      {passes.find((x) => x.name === p.name)?.title ?? p.name}:{" "}
                      <strong>{p.changed}</strong> wijziging(en)
                    </li>
                  ))}
                </ul>
                <a
                  className="optimize-dialog__btn optimize-dialog__btn--primary"
                  href={result.downloadUrl}
                  download
                >
                  Download geoptimaliseerd bestand
                </a>
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}
