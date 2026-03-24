/**
 * ValidationPanel — IDS validation workflow in the right panel.
 *
 * Compact layout that integrates IDS selection, validation trigger,
 * progress tracking, and results display. Clicking on failed
 * specifications highlights the affected elements in the 3D viewer.
 */

import { useCallback, useMemo, useState } from "react";

import { useStore } from "../../store";
import type { IdsSelection } from "../IdsSelector";
import IdsSelector from "../IdsSelector";
import ValidationProgress from "../ValidationProgress";
import ErrorDisplay from "../ErrorDisplay";
import ResultsSummary from "../ResultsSummary";
import SpecificationList from "../SpecificationList";
import type { SpecificationResult, RequirementResult, ElementResult } from "../../types/validation";
import { createBcfIssue } from "../../types/bcfIssue";
import {
  mapSpecToTopic,
  mapRequirementToTopic,
  mapElementToTopic,
  mapValidationToTopics,
} from "../../lib/validationToBcf";

import "./ValidationPanel.css";

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

  // Highlight + selection actions
  const selectElement = useStore((s) => s.selectElement);
  const setHighlightGroup = useStore((s) => s.setHighlightGroup);
  const clearHighlights = useStore((s) => s.clearHighlights);
  const setActiveRightTab = useStore((s) => s.setActiveRightTab);

  // BCF actions
  const bcfAddIssue = useStore((s) => s.bcfAddIssue);
  const bcfAddIssues = useStore((s) => s.bcfAddIssues);

  // Inline feedback for BCF actions
  const [bcfFeedback, setBcfFeedback] = useState<string | null>(null);

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
    [selectElement, setHighlightGroup, setActiveRightTab]
  );

  // ── BCF issue creation handlers ───────────────────────
  const showBcfFeedback = useCallback((msg: string) => {
    setBcfFeedback(msg);
    setTimeout(() => setBcfFeedback(null), 2500);
  }, []);

  const ifcFileName = validationResult?.ifc_file_name ?? "";
  const idsFileName = validationResult?.ids_file_name ?? "";

  const handleCreateBcfFromSpec = useCallback(
    (spec: SpecificationResult) => {
      const mapping = mapSpecToTopic(spec, ifcFileName, idsFileName);
      const issue = createBcfIssue(spec.specification_name, { specificationName: spec.specification_name }, mapping);
      bcfAddIssue(issue);
      showBcfFeedback(`BCF issue aangemaakt: ${spec.specification_name}`);
    },
    [ifcFileName, idsFileName, bcfAddIssue, showBcfFeedback],
  );

  const handleCreateBcfFromRequirement = useCallback(
    (spec: SpecificationResult, req: RequirementResult) => {
      const mapping = mapRequirementToTopic(spec, req, ifcFileName, idsFileName);
      const title = `${spec.specification_name} — ${req.requirement_description}`;
      const issue = createBcfIssue(title, {
        specificationName: spec.specification_name,
        requirementDescription: req.requirement_description,
      }, mapping);
      bcfAddIssue(issue);
      showBcfFeedback(`BCF issue aangemaakt: ${req.requirement_description}`);
    },
    [ifcFileName, idsFileName, bcfAddIssue, showBcfFeedback],
  );

  const handleCreateBcfFromElement = useCallback(
    (spec: SpecificationResult, req: RequirementResult, el: ElementResult) => {
      const mapping = mapElementToTopic(spec, req, el, ifcFileName, idsFileName);
      const elName = el.element_name ?? el.element_type;
      const title = `${el.element_type} "${elName}"`;
      const issue = createBcfIssue(title, {
        specificationName: spec.specification_name,
        requirementDescription: req.requirement_description,
        elementGlobalId: el.global_id ?? undefined,
      }, mapping);
      bcfAddIssue(issue);
      showBcfFeedback(`BCF issue aangemaakt: ${elName}`);
    },
    [ifcFileName, idsFileName, bcfAddIssue, showBcfFeedback],
  );

  const handleCreateBcfBulk = useCallback(() => {
    if (!validationResult) return;
    const mappings = mapValidationToTopics(validationResult);
    const issues = mappings.map((mapping, idx) => {
      const spec = validationResult.specifications.filter((s) => s.status === "fail")[idx];
      const specName = spec?.specification_name ?? `Issue ${idx + 1}`;
      return createBcfIssue(specName, { specificationName: specName }, mapping);
    });
    bcfAddIssues(issues);
    showBcfFeedback(`${issues.length} BCF issues aangemaakt`);
    setActiveRightTab("bcf");
  }, [validationResult, bcfAddIssues, showBcfFeedback, setActiveRightTab]);

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
      {/* IDS Selection */}
      <div className="validation-panel__section">
        <h3 className="validation-panel__heading">IDS Standaard</h3>
        <IdsSelector
          onSelectionChange={handleIdsChange}
          disabled={inputsDisabled}
        />
      </div>

      {/* Submit button */}
      <div className="validation-panel__section validation-panel__actions">
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
          />

          {/* Highlight controls + BCF bulk */}
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
              className="validation-panel__btn validation-panel__btn--secondary"
              onClick={handleClearHighlights}
              title="Verwijder highlights"
            >
              Wis highlights
            </button>
            {validationResult.failed_specifications > 0 && (
              <button
                type="button"
                className="validation-panel__btn validation-panel__btn--bcf"
                onClick={handleCreateBcfBulk}
                title="Maak BCF issues van alle failures"
              >
                Alle failures → BCF
              </button>
            )}
          </div>

          {bcfFeedback && (
            <div className="validation-panel__bcf-feedback" role="status">
              {bcfFeedback}
            </div>
          )}

          {validationResult.specifications.length > 0 && (
            <div className="validation-panel__specs">
              <h3 className="validation-panel__heading">Specificaties</h3>
              <SpecificationList
                specifications={validationResult.specifications}
                autoExpandFailed
                onElementSelect={handleElementSelect}
                onCreateBcfFromSpec={handleCreateBcfFromSpec}
                onCreateBcfFromRequirement={handleCreateBcfFromRequirement}
                onCreateBcfFromElement={handleCreateBcfFromElement}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
