/**
 * ValidationPanel — IDS validation workflow in the right panel.
 *
 * Compact layout that integrates IDS selection, validation trigger,
 * progress tracking, and results display. Clicking on failed
 * specifications highlights the affected elements in the 3D viewer.
 */

import { useCallback, useMemo } from "react";

import { downloadBcf } from "../../api/client";
import { useStore } from "../../store";
import type { ViewpointCaptureCallback } from "../../store/slices/bcfSlice";
import type { BcfCameraState } from "../../types/bcf";
import type { SpecificationResult, ElementResult } from "../../types/validation";
import type { IdsSelection } from "../IdsSelector";
import { showToast } from "../Toast";
import IdsSelector from "../IdsSelector";
import ValidationProgress from "../ValidationProgress";
import ErrorDisplay from "../ErrorDisplay";
import ResultsSummary from "../ResultsSummary";
import SpecificationList from "../SpecificationList";

import "./ValidationPanel.css";

/**
 * Request a viewpoint capture from CenterPanel via custom event.
 * Returns a Promise that resolves with the capture result.
 */
function requestViewpointCapture(
  globalIds: string[]
): Promise<{ screenshot: string; camera: BcfCameraState } | null> {
  return new Promise((resolve) => {
    const requestId = crypto.randomUUID();

    const handleResponse = (e: Event) => {
      const detail = (
        e as CustomEvent<{
          requestId: string;
          result: { screenshot: string; camera: BcfCameraState } | null;
        }>
      ).detail;
      if (detail.requestId === requestId) {
        window.removeEventListener("capture-viewpoint-response", handleResponse);
        resolve(detail.result);
      }
    };

    window.addEventListener("capture-viewpoint-response", handleResponse);
    window.dispatchEvent(
      new CustomEvent("capture-viewpoint", {
        detail: { globalIds, requestId },
      })
    );
  });
}

export function ValidationPanel() {
  const project = useStore((s) => s.project);
  const viewerReady = useStore((s) => s.viewerReady);

  // Validation state
  const phase = useStore((s) => s.validationPhase);
  const idsSelection = useStore((s) => s.idsSelection);
  const jobStatus = useStore((s) => s.jobStatus);
  const validationResult = useStore((s) => s.validationResult);
  const validationError = useStore((s) => s.validationError);

  // Validation actions
  const setIdsSelection = useStore((s) => s.setIdsSelection);
  const cancelValidation = useStore((s) => s.cancelValidation);
  const resetValidation = useStore((s) => s.resetValidation);
  const retryValidation = useStore((s) => s.retryValidation);
  const dismissValidationError = useStore((s) => s.dismissValidationError);

  // BCF actions
  const generateBcfFromValidation = useStore((s) => s.generateBcfFromValidation);
  const createBcfFromSpecification = useStore((s) => s.createBcfFromSpecification);
  const createBcfFromElement = useStore((s) => s.createBcfFromElement);
  const setActiveRightTab = useStore((s) => s.setActiveRightTab);

  // Highlight + selection actions
  const selectElement = useStore((s) => s.selectElement);
  const setHighlightGroup = useStore((s) => s.setHighlightGroup);
  const clearHighlights = useStore((s) => s.clearHighlights);
  /** Get the first loaded IFC file from the project */
  const loadedModel = useMemo(() => {
    return project?.models.find((m) => m.loadState === "loaded");
  }, [project]);

  const handleIdsChange = useCallback(
    (selection: IdsSelection | null) => {
      setIdsSelection(selection);
    },
    [setIdsSelection]
  );

  const handleSubmit = useCallback(() => {
    if (!loadedModel) return;

    // Find the original file — we need the File object from the input
    // Since we don't store File references in the store, dispatch an event
    // to get the file from the Toolbar's recent uploads
    // For now, use a stored file reference approach
    window.dispatchEvent(
      new CustomEvent("validation-request", {
        detail: { modelId: loadedModel.id, fileName: loadedModel.fileName },
      })
    );
  }, [loadedModel]);

  const handleDownloadJson = useCallback(() => {
    if (!validationResult) return;
    const jsonString = JSON.stringify(validationResult, null, 2);
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `validation-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [validationResult]);

  const jobId = useStore((s) => s.jobId);

  const handleDownloadBcf = useCallback(async () => {
    if (!jobId) return;
    try {
      const blob = await downloadBcf(jobId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `validation-${jobId.slice(0, 8)}.bcfzip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("BCF download failed:", err);
    }
  }, [jobId]);

  /** Highlight failed elements when clicking a specification */
  const handleHighlightFailures = useCallback(() => {
    if (!validationResult) return;

    const failedIds: string[] = [];
    for (const spec of validationResult.specifications) {
      if (spec.status === "fail") {
        for (const req of spec.requirements) {
          for (const el of req.elements) {
            if (el.status === "fail" && el.global_id) {
              failedIds.push(el.global_id);
            }
          }
        }
      }
    }

    if (failedIds.length > 0) {
      setHighlightGroup({
        id: "validation-failures",
        color: "#ff4444",
        globalIds: failedIds,
      });
    }
  }, [validationResult, setHighlightGroup]);

  const handleClearHighlights = useCallback(() => {
    clearHighlights();
  }, [clearHighlights]);

  /** Generate BCF issues from all failed validation specs */
  const handleGenerateBcf = useCallback(async () => {
    if (!validationResult) return;
    const captureViewpoint: ViewpointCaptureCallback = requestViewpointCapture;
    await generateBcfFromValidation(validationResult, captureViewpoint);
    setActiveRightTab("bcf");
    showToast("BCF issues gegenereerd vanuit validatie");
  }, [validationResult, generateBcfFromValidation, setActiveRightTab]);

  /** Create BCF issue from a single specification */
  const handleCreateBcfFromSpec = useCallback(
    async (spec: SpecificationResult) => {
      const captureViewpoint: ViewpointCaptureCallback = requestViewpointCapture;
      await createBcfFromSpecification(spec, captureViewpoint);
      showToast(`BCF issue aangemaakt: ${spec.specification_name}`);
    },
    [createBcfFromSpecification]
  );

  /** Create BCF issue from a single element */
  const handleCreateBcfFromElement = useCallback(
    async (element: ElementResult, specName: string) => {
      const captureViewpoint: ViewpointCaptureCallback = requestViewpointCapture;
      await createBcfFromElement(element, specName, captureViewpoint);
      showToast("BCF issue aangemaakt voor element");
    },
    [createBcfFromElement]
  );

  /** Click on an element in the results → select, highlight, zoom, switch tab */
  const handleElementSelect = useCallback(
    (globalId: string) => {
      selectElement(globalId);
      setHighlightGroup({
        id: "element-selection",
        color: "#44B6A8",
        globalIds: [globalId],
      });

      window.dispatchEvent(
        new CustomEvent("zoom-to-element", { detail: { globalId } })
      );
    },
    [selectElement, setHighlightGroup]
  );

  const inputsDisabled = phase === "submitting" || phase === "polling";
  const canSubmit =
    loadedModel !== undefined &&
    idsSelection !== null &&
    viewerReady &&
    (phase === "idle" || phase === "error" || phase === "completed");

  // No model loaded
  if (!project || project.models.length === 0) {
    return (
      <div className="validation-panel">
        <div className="empty-state">
          <p className="empty-state__text">
            Upload eerst een IFC model om te valideren
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="validation-panel">
      {/* IDS Selection + Submit in one block */}
      <div className="validation-panel__section">
        <IdsSelector
          onSelectionChange={handleIdsChange}
          disabled={inputsDisabled}
        />
      </div>

      <div className="validation-panel__actions">
        <button
          type="button"
          className="validation-panel__btn validation-panel__btn--primary"
          onClick={handleSubmit}
          disabled={!canSubmit || inputsDisabled}
          aria-busy={phase === "submitting"}
        >
          {phase === "submitting" ? "Bezig..." : "Valideer"}
        </button>
        {phase === "completed" && (
          <button
            type="button"
            className="validation-panel__btn validation-panel__btn--secondary"
            onClick={resetValidation}
          >
            Reset
          </button>
        )}
      </div>

      {/* Error */}
      {validationError && (
        <div className="validation-panel__section">
          <ErrorDisplay
            message={validationError.message}
            details={validationError.details}
            type="validation"
            onRetry={retryValidation}
            onDismiss={dismissValidationError}
            compact
          />
        </div>
      )}

      {/* Progress */}
      {(phase === "polling" || phase === "submitting") && jobStatus && (
        <div className="validation-panel__section">
          <ValidationProgress
            status={jobStatus.status}
            progressMessage={jobStatus.progress}
            createdAt={jobStatus.created_at}
            startedAt={jobStatus.started_at}
            onCancel={cancelValidation}
          />
        </div>
      )}

      {phase === "submitting" && !jobStatus && (
        <div className="validation-panel__section">
          <div className="validation-panel__submitting" role="status">
            <div className="validation-panel__spinner" />
            <span>Bestanden uploaden...</span>
          </div>
        </div>
      )}

      {/* Results */}
      {validationResult && (
        <div className="validation-panel__section validation-panel__results">
          <ResultsSummary
            result={validationResult}
            onDownloadJson={handleDownloadJson}
            onDownloadBcf={jobId ? handleDownloadBcf : undefined}
          />

          {/* Highlight controls */}
          <div className="validation-panel__highlight-bar">
            <button
              type="button"
              className="validation-panel__btn validation-panel__btn--highlight"
              onClick={handleHighlightFailures}
              title="Toon gefaalde elementen in 3D"
            >
              Toon failures in 3D
            </button>
            <button
              type="button"
              className="validation-panel__btn validation-panel__btn--bcf"
              onClick={handleGenerateBcf}
              title="Genereer BCF issues vanuit validatie"
            >
              BCF issues genereren
            </button>
            <button
              type="button"
              className="validation-panel__btn validation-panel__btn--secondary"
              onClick={handleClearHighlights}
              title="Verwijder highlights"
            >
              Wis highlights
            </button>
          </div>

          {validationResult.specifications.length > 0 && (
            <div className="validation-panel__specs">
              <h3 className="validation-panel__heading">Specificaties</h3>
              <SpecificationList
                specifications={validationResult.specifications}
                autoExpandFailed
                onElementSelect={handleElementSelect}
                onCreateBcfFromSpec={handleCreateBcfFromSpec}
                onCreateBcfFromElement={handleCreateBcfFromElement}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
