/**
 * ValidationPanel — BIMcollab-style IDS validation workflow.
 *
 * Layout: IDS selection + submit → header bar + ResultsTree + DetailPane.
 * Replaces the old card-based layout with a flat tree and context detail pane.
 */

import { useCallback, useMemo, useState } from "react";

import { useStore } from "../../store";
import type { IdsSelection } from "../IdsSelector";
import IdsSelector from "../IdsSelector";
import ValidationProgress from "../ValidationProgress";
import ErrorDisplay from "../ErrorDisplay";
import { ResultsTree } from "../SpecificationList";
import { DetailPane } from "./DetailPane";
import type {
  SpecificationResult,
  RequirementResult,
  ElementResult,
  SelectedTreeItem,
} from "../../types/validation";
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

  // Tree selection state
  const [selectedItem, setSelectedItem] = useState<SelectedTreeItem | null>(
    null
  );

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

  /** Highlight all failed elements in 3D */
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

  /** Tree item selected → update detail pane + 3D interaction for elements */
  const handleItemSelect = useCallback(
    (item: SelectedTreeItem) => {
      setSelectedItem(item);

      // Auto-select and zoom for elements with GlobalId
      if (item.kind === "element" && item.el.global_id) {
        selectElement(item.el.global_id);
        setHighlightGroup({
          id: "element-selection",
          color: "#44B6A8",
          globalIds: [item.el.global_id],
        });
        window.dispatchEvent(
          new CustomEvent("zoom-to-element", {
            detail: { globalId: item.el.global_id },
          })
        );
      }
    },
    [selectElement, setHighlightGroup]
  );

  /** Zoom from detail pane */
  const handleElementZoom = useCallback(
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
      const issue = createBcfIssue(
        spec.specification_name,
        { specificationName: spec.specification_name },
        mapping
      );
      bcfAddIssue(issue);
      showBcfFeedback(`BCF issue: ${spec.specification_name}`);
    },
    [ifcFileName, idsFileName, bcfAddIssue, showBcfFeedback]
  );

  const handleCreateBcfFromRequirement = useCallback(
    (spec: SpecificationResult, req: RequirementResult) => {
      const mapping = mapRequirementToTopic(
        spec,
        req,
        ifcFileName,
        idsFileName
      );
      const title = `${spec.specification_name} — ${req.requirement_description}`;
      const issue = createBcfIssue(
        title,
        {
          specificationName: spec.specification_name,
          requirementDescription: req.requirement_description,
        },
        mapping
      );
      bcfAddIssue(issue);
      showBcfFeedback(`BCF issue: ${req.requirement_description}`);
    },
    [ifcFileName, idsFileName, bcfAddIssue, showBcfFeedback]
  );

  const handleCreateBcfFromElement = useCallback(
    (spec: SpecificationResult, req: RequirementResult, el: ElementResult) => {
      const mapping = mapElementToTopic(
        spec,
        req,
        el,
        ifcFileName,
        idsFileName
      );
      const elName = el.element_name ?? el.element_type;
      const title = `${el.element_type} "${elName}"`;
      const issue = createBcfIssue(
        title,
        {
          specificationName: spec.specification_name,
          requirementDescription: req.requirement_description,
          elementGlobalId: el.global_id ?? undefined,
        },
        mapping
      );
      bcfAddIssue(issue);
      showBcfFeedback(`BCF issue: ${elName}`);
    },
    [ifcFileName, idsFileName, bcfAddIssue, showBcfFeedback]
  );

  const handleCreateBcfBulk = useCallback(() => {
    if (!validationResult) return;
    const mappings = mapValidationToTopics(validationResult);
    const issues = mappings.map((mapping, idx) => {
      const spec = validationResult.specifications.filter(
        (s) => s.status === "fail"
      )[idx];
      const specName = spec?.specification_name ?? `Issue ${idx + 1}`;
      return createBcfIssue(
        specName,
        { specificationName: specName },
        mapping
      );
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

  // Result counts for header bar
  const totalSpecs = validationResult?.total_specifications ?? 0;
  const failedSpecs = validationResult?.failed_specifications ?? 0;
  const passedSpecs = totalSpecs - failedSpecs;

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
        <>
          {/* Header bar */}
          <div className="vt-header">
            <span className="vt-header__title">
              Results ({totalSpecs})
            </span>
            <span className="vt-header__counts">
              <span className="vt-header__pass">{passedSpecs}</span>
              <span className="vt-header__sep">/</span>
              <span className="vt-header__fail">{failedSpecs}</span>
            </span>
            <div className="vt-header__actions">
              <button
                type="button"
                className="vt-header__icon-btn"
                onClick={handleHighlightFailures}
                title="Toon failures in 3D"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 1a7 7 0 100 14A7 7 0 008 1zm0 2a2 2 0 110 4 2 2 0 010-4z" />
                </svg>
              </button>
              <button
                type="button"
                className="vt-header__icon-btn"
                onClick={handleClearHighlights}
                title="Wis highlights"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M4.646 4.646a.5.5 0 01.708 0L8 7.293l2.646-2.647a.5.5 0 01.708.708L8.707 8l2.647 2.646a.5.5 0 01-.708.708L8 8.707l-2.646 2.647a.5.5 0 01-.708-.708L7.293 8 4.646 5.354a.5.5 0 010-.708z" />
                </svg>
              </button>
              <button
                type="button"
                className="vt-header__icon-btn"
                onClick={handleDownloadJson}
                title="Download JSON"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M4 1h8a1 1 0 011 1v12a1 1 0 01-1 1H4a1 1 0 01-1-1V2a1 1 0 011-1zm1 2v2h6V3H5zm0 4v1h6V7H5zm0 3v1h4v-1H5z" />
                </svg>
              </button>
              {failedSpecs > 0 && (
                <button
                  type="button"
                  className="vt-header__icon-btn vt-header__icon-btn--bcf"
                  onClick={handleCreateBcfBulk}
                  title="Alle failures → BCF"
                >
                  BCF
                </button>
              )}
            </div>
          </div>

          {/* BCF feedback toast */}
          {bcfFeedback && (
            <div className="validation-panel__bcf-feedback" role="status">
              {bcfFeedback}
            </div>
          )}

          {/* Tree container */}
          <div className="vt-tree-container">
            <ResultsTree
              specifications={validationResult.specifications}
              autoExpandFailed
              selectedItem={selectedItem}
              onItemSelect={handleItemSelect}
            />
          </div>

          {/* Detail pane */}
          {selectedItem && (
            <div className="vt-detail-container">
              <DetailPane
                item={selectedItem}
                onElementZoom={handleElementZoom}
                onCreateBcfFromSpec={handleCreateBcfFromSpec}
                onCreateBcfFromRequirement={handleCreateBcfFromRequirement}
                onCreateBcfFromElement={handleCreateBcfFromElement}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
