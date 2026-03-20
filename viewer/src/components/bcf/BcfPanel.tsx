/**
 * BcfPanel — BCF issue manager in the right panel.
 *
 * BIMcollab-achtige issue management: grid met thumbnail kaartjes,
 * detail view met edit forms, viewpoint navigation, en export.
 *
 * Replaces the "binnenkort beschikbaar" placeholder in RightPanel.
 */

import { useCallback, useMemo, useRef, useState } from "react";

import { useStore } from "../../store";
import type { BcfIssue, IssueFilter } from "../../types/bcf";
import { exportBcfZip } from "./BcfExporter";
import { importBcfZip } from "./BcfImporter";
import { BcfSyncDialog } from "./BcfSyncDialog";
import { syncIssuesToPlatform } from "../../api/bcfPlatformClient";
import { showToast } from "../Toast";

import "./BcfPanel.css";

/** Filter pill configuration */
const FILTERS: { id: IssueFilter; label: string }[] = [
  { id: "all", label: "Alle" },
  { id: "Open", label: "Open" },
  { id: "In Progress", label: "Actief" },
  { id: "Closed", label: "Gesloten" },
];

export function BcfPanel() {
  // BCF state
  const issues = useStore((s) => s.bcfIssues);
  const activeIssueId = useStore((s) => s.activeBcfIssueId);
  const filter = useStore((s) => s.bcfFilter);
  const generating = useStore((s) => s.bcfGenerating);
  const generationProgress = useStore((s) => s.bcfGenerationProgress);

  // BCF actions
  const setActiveIssue = useStore((s) => s.setActiveBcfIssue);
  const setBcfFilter = useStore((s) => s.setBcfFilter);
  const getFilteredIssues = useStore((s) => s.getFilteredBcfIssues);
  const getStats = useStore((s) => s.getBcfStats);
  const updateIssue = useStore((s) => s.updateBcfIssue);
  const deleteIssue = useStore((s) => s.deleteBcfIssue);

  const clearAllIssues = useStore((s) => s.clearAllBcfIssues);

  // Viewer actions (for viewpoint navigation)
  const selectElement = useStore((s) => s.selectElement);
  const setHighlightGroup = useStore((s) => s.setHighlightGroup);

  // BCF Platform sync state
  const platformProjectId = useStore((s) => s.bcfPlatformProjectId);
  const setBcfSyncStatus = useStore((s) => s.setBcfSyncStatus);
  const setBcfSyncProgress = useStore((s) => s.setBcfSyncProgress);

  // Import file input ref
  const importInputRef = useRef<HTMLInputElement>(null);

  // Sync dialog visibility
  const [syncDialogOpen, setSyncDialogOpen] = useState(false);

  const filteredIssues = useMemo(() => getFilteredIssues(), [getFilteredIssues, issues, filter]);
  const stats = useMemo(() => getStats(), [getStats, issues]);

  const activeIssue = useMemo(
    () => issues.find((i) => i.guid === activeIssueId) ?? null,
    [issues, activeIssueId]
  );

  /** Navigate to an issue's viewpoint in the 3D viewer */
  const handleGoToViewpoint = useCallback(
    (issue: BcfIssue) => {
      // Highlight the issue's elements
      if (issue.failedGlobalIds.length > 0) {
        setHighlightGroup({
          id: "bcf-issue",
          color: "#ff4444",
          globalIds: issue.failedGlobalIds,
        });

        // Zoom to first element
        window.dispatchEvent(
          new CustomEvent("zoom-to-element", {
            detail: { globalId: issue.failedGlobalIds[0] },
          })
        );
      }

      // Restore camera (dispatched as event, handled by CenterPanel)
      if (issue.viewpoint.camera) {
        window.dispatchEvent(
          new CustomEvent("restore-camera", {
            detail: { camera: issue.viewpoint.camera },
          })
        );
      }
    },
    [setHighlightGroup]
  );

  /** Click on an element in the detail view → select + zoom */
  const handleElementClick = useCallback(
    (globalId: string) => {
      selectElement(globalId);
      setHighlightGroup({
        id: "bcf-element",
        color: "#44B6A8",
        globalIds: [globalId],
      });
      window.dispatchEvent(
        new CustomEvent("zoom-to-element", { detail: { globalId } })
      );
    },
    [selectElement, setHighlightGroup]
  );

  /** Export all issues as .bcfzip */
  const handleExport = useCallback(async () => {
    if (issues.length === 0) return;
    try {
      const blob = await exportBcfZip(issues);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `bcf-export-${Date.now()}.bcfzip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      showToast(`${issues.length} issues geëxporteerd als BCF`);
    } catch (err) {
      console.error("BCF export failed:", err);
      showToast("BCF export mislukt", "error");
    }
  }, [issues]);

  /** Import a .bcfzip file */
  const handleImport = useCallback(async (file: File) => {
    try {
      const imported = await importBcfZip(file);
      const addIssue = useStore.getState().addBcfIssue;
      const existingCount = useStore.getState().bcfIssues.length;
      for (const [i, issue] of imported.entries()) {
        issue.index = existingCount + i;
        addIssue(issue);
      }
      showToast(`${imported.length} BCF issues geïmporteerd`);
    } catch (err) {
      console.error("BCF import failed:", err);
      showToast("BCF import mislukt", "error");
    }
  }, []);

  const handleImportClick = useCallback(() => {
    importInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleImport(file);
        e.target.value = "";
      }
    },
    [handleImport]
  );

  /** Handle sync button click — direct sync if project known, dialog otherwise */
  const handleSyncClick = useCallback(async () => {
    if (issues.length === 0) return;

    if (platformProjectId) {
      // Direct sync to known project
      setBcfSyncStatus("syncing");
      try {
        const synced = await syncIssuesToPlatform(
          platformProjectId,
          issues,
          (progress) => {
            setBcfSyncProgress(
              `${progress.current}/${progress.total}: ${progress.title}`
            );
          }
        );
        setBcfSyncStatus("done");
        setBcfSyncProgress(null);
        showToast(`${synced} van ${issues.length} issues gesynchroniseerd`);
      } catch (err) {
        setBcfSyncStatus("error");
        setBcfSyncProgress(null);
        const msg =
          err instanceof Error ? err.message : "Synchronisatie mislukt";
        showToast(msg, "error");
      }
    } else {
      setSyncDialogOpen(true);
    }
  }, [issues, platformProjectId, setBcfSyncStatus, setBcfSyncProgress]);

  // ─── Generation in progress ─────────────────────────────────────

  if (generating) {
    return (
      <div className="bcf-panel">
        <div className="bcf-panel__generating">
          <div className="bcf-panel__spinner" />
          <span>{generationProgress ?? "Issues genereren..."}</span>
        </div>
      </div>
    );
  }

  // ─── Empty state ────────────────────────────────────────────────

  if (issues.length === 0) {
    return (
      <div className="bcf-panel">
        <div className="empty-state">
          <p className="empty-state__text">
            Nog geen BCF issues. Voer eerst een validatie uit en genereer
            issues vanuit de resultaten.
          </p>
          <button
            type="button"
            className="bcf-panel__action-btn"
            onClick={handleImportClick}
            style={{ marginTop: 8 }}
          >
            BCF importeren
          </button>
          <input
            ref={importInputRef}
            type="file"
            accept=".bcfzip,.bcf"
            onChange={handleFileChange}
            style={{ display: "none" }}
          />
        </div>
      </div>
    );
  }

  // ─── Detail view ────────────────────────────────────────────────

  if (activeIssue) {
    return (
      <div className="bcf-panel">
        <div className="bcf-detail">
          <div className="bcf-detail__header">
            <button
              type="button"
              className="bcf-detail__back"
              onClick={() => setActiveIssue(null)}
            >
              ← Terug
            </button>
            <span className="bcf-detail__title">{activeIssue.title}</span>
          </div>

          {/* Viewpoint screenshot */}
          <div
            className="bcf-detail__screenshot"
            onClick={() => handleGoToViewpoint(activeIssue)}
            title="Klik om naar viewpoint te navigeren"
          >
            {activeIssue.viewpoint.screenshotDataUrl ? (
              <img
                src={activeIssue.viewpoint.screenshotDataUrl}
                alt="Viewpoint"
                className="bcf-detail__screenshot-img"
              />
            ) : (
              <span className="bcf-detail__screenshot-placeholder">
                Geen screenshot beschikbaar
              </span>
            )}
            <span className="bcf-detail__screenshot-action">
              Ga naar viewpoint
            </span>
          </div>

          {/* Edit fields */}
          <div className="bcf-detail__fields">
            <div className="bcf-detail__field">
              <label>Status</label>
              <select
                value={activeIssue.status}
                onChange={(e) =>
                  updateIssue(activeIssue.guid, {
                    status: e.target.value as BcfIssue["status"],
                  })
                }
              >
                <option value="Open">Open</option>
                <option value="In Progress">In behandeling</option>
                <option value="Closed">Gesloten</option>
              </select>
            </div>

            <div className="bcf-detail__field">
              <label>Prioriteit</label>
              <select
                value={activeIssue.priority}
                onChange={(e) =>
                  updateIssue(activeIssue.guid, {
                    priority: e.target.value as BcfIssue["priority"],
                  })
                }
              >
                <option value="Critical">Kritiek</option>
                <option value="High">Hoog</option>
                <option value="Normal">Normaal</option>
                <option value="Low">Laag</option>
              </select>
            </div>

            <div className="bcf-detail__field">
              <label>Type</label>
              <select
                value={activeIssue.type}
                onChange={(e) =>
                  updateIssue(activeIssue.guid, {
                    type: e.target.value as BcfIssue["type"],
                  })
                }
              >
                <option value="Error">Error</option>
                <option value="Warning">Warning</option>
                <option value="Info">Info</option>
                <option value="Clash">Clash</option>
                <option value="Comment">Comment</option>
              </select>
            </div>

            <div className="bcf-detail__field">
              <label>Toegewezen</label>
              <input
                type="text"
                value={activeIssue.assignedTo}
                onChange={(e) =>
                  updateIssue(activeIssue.guid, {
                    assignedTo: e.target.value,
                  })
                }
                placeholder="Naam..."
              />
            </div>

            <div className="bcf-detail__field">
              <label>Deadline</label>
              <input
                type="date"
                value={activeIssue.dueDate ?? ""}
                onChange={(e) =>
                  updateIssue(activeIssue.guid, {
                    dueDate: e.target.value || undefined,
                  })
                }
              />
            </div>
          </div>

          {/* Failed elements */}
          {activeIssue.failedGlobalIds.length > 0 && (
            <div className="bcf-detail__elements">
              <h4 className="bcf-detail__section-title">
                Elementen ({activeIssue.failedGlobalIds.length})
              </h4>
              {activeIssue.failedGlobalIds.map((gid) => (
                <div
                  key={gid}
                  className="bcf-detail__element"
                  onClick={() => handleElementClick(gid)}
                >
                  <span className="bcf-detail__element-dot" />
                  <span className="bcf-detail__element-id">{gid}</span>
                </div>
              ))}
            </div>
          )}

          {/* Comments */}
          <div className="bcf-detail__comments">
            <h4 className="bcf-detail__section-title">
              Opmerkingen ({activeIssue.comments.length})
            </h4>
            {activeIssue.comments.map((c) => (
              <div key={c.guid} className="bcf-detail__comment">
                <span className="bcf-detail__comment-author">{c.author}</span>
                <span className="bcf-detail__comment-date">
                  {new Date(c.date).toLocaleDateString("nl-NL")}
                </span>
                <p className="bcf-detail__comment-text">{c.comment}</p>
              </div>
            ))}
          </div>

          {/* Actions */}
          <div className="bcf-detail__actions">
            <button
              type="button"
              className="bcf-detail__btn bcf-detail__btn--danger"
              onClick={() => {
                deleteIssue(activeIssue.guid);
                setActiveIssue(null);
              }}
            >
              Verwijderen
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ─── Issue grid (list view) ─────────────────────────────────────

  return (
    <div className="bcf-panel">
      {/* Toolbar */}
      <div className="bcf-panel__toolbar">
        <div className="bcf-panel__filters">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={`bcf-panel__filter-pill ${
                filter === f.id ? "bcf-panel__filter-pill--active" : ""
              }`}
              onClick={() => setBcfFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="bcf-panel__toolbar-actions">
          <button
            type="button"
            className="bcf-panel__action-btn"
            onClick={handleImportClick}
            title="BCF importeren"
          >
            Import
          </button>
          <button
            type="button"
            className="bcf-panel__action-btn bcf-panel__action-btn--primary"
            onClick={handleExport}
            title="BCF exporteren als .bcfzip"
          >
            Export
          </button>
          <button
            type="button"
            className="bcf-panel__action-btn bcf-panel__action-btn--sync"
            onClick={handleSyncClick}
            title="Sync naar BCF Platform"
          >
            Sync
          </button>
          <button
            type="button"
            className="bcf-panel__action-btn bcf-panel__action-btn--danger"
            onClick={() => {
              clearAllIssues();
              showToast("Alle BCF issues verwijderd");
            }}
            title="Alle issues verwijderen"
          >
            Wis
          </button>
        </div>
        <input
          ref={importInputRef}
          type="file"
          accept=".bcfzip,.bcf"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />
      </div>

      {/* Stats */}
      <div className="bcf-panel__stats">
        <div className="bcf-panel__stat bcf-panel__stat--open">
          <span className="bcf-panel__stat-num">{stats.open}</span>
          <span className="bcf-panel__stat-label">Open</span>
        </div>
        <div className="bcf-panel__stat bcf-panel__stat--closed">
          <span className="bcf-panel__stat-num">{stats.closed}</span>
          <span className="bcf-panel__stat-label">Gesloten</span>
        </div>
        <div className="bcf-panel__stat">
          <span className="bcf-panel__stat-num">{stats.total}</span>
          <span className="bcf-panel__stat-label">Totaal</span>
        </div>
      </div>

      {/* Issue cards */}
      <div className="bcf-panel__grid">
        {filteredIssues.map((issue) => (
          <div
            key={issue.guid}
            className="bcf-issue-card"
            onClick={() => setActiveIssue(issue.guid)}
          >
            {/* Thumbnail */}
            <div className="bcf-issue-card__thumb">
              {issue.viewpoint.screenshotDataUrl ? (
                <img
                  src={issue.viewpoint.screenshotDataUrl}
                  alt=""
                  className="bcf-issue-card__thumb-img"
                />
              ) : (
                <div className="bcf-issue-card__thumb-placeholder" />
              )}
            </div>

            {/* Meta */}
            <div className="bcf-issue-card__meta">
              <span className="bcf-issue-card__title">{issue.title}</span>
              <span className="bcf-issue-card__desc">
                {issue.failedGlobalIds.length} element
                {issue.failedGlobalIds.length !== 1 ? "en" : ""}
              </span>
              <div className="bcf-issue-card__tags">
                <span
                  className={`bcf-tag bcf-tag--${issue.type.toLowerCase()}`}
                >
                  {issue.type}
                </span>
                <span
                  className={`bcf-tag bcf-tag--${issue.status === "Closed" ? "closed" : "open"}`}
                >
                  {issue.status}
                </span>
                {issue.assignedTo && (
                  <span className="bcf-tag bcf-tag--assignee">
                    {issue.assignedTo}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Sync dialog overlay */}
      {syncDialogOpen && (
        <BcfSyncDialog onClose={() => setSyncDialogOpen(false)} />
      )}
    </div>
  );
}
