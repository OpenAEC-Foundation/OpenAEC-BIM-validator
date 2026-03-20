/**
 * BcfSyncDialog — modal overlay for BCF Platform sync.
 *
 * Shows a list of existing platform projects (fetched via API)
 * or allows creating a new project. On selection, triggers
 * syncIssuesToPlatform and reports progress.
 */

import { useCallback, useEffect, useState } from "react";

import { useStore } from "../../store";
import {
  listProjects,
  createProject,
  syncIssuesToPlatform,
  type PlatformProject,
} from "../../api/bcfPlatformClient";
import { showToast } from "../Toast";

interface BcfSyncDialogProps {
  onClose: () => void;
}

export function BcfSyncDialog({ onClose }: BcfSyncDialogProps) {
  const issues = useStore((s) => s.bcfIssues);
  const platformProjectId = useStore((s) => s.bcfPlatformProjectId);
  const setBcfPlatformProjectId = useStore((s) => s.setBcfPlatformProjectId);
  const setBcfSyncStatus = useStore((s) => s.setBcfSyncStatus);
  const setBcfSyncProgress = useStore((s) => s.setBcfSyncProgress);

  const [projects, setProjects] = useState<PlatformProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState<string | null>(null);

  // New project form
  const [showNewForm, setShowNewForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  // Fetch projects on mount
  useEffect(() => {
    let cancelled = false;

    async function fetchProjects() {
      try {
        setLoading(true);
        setError(null);
        const result = await listProjects();
        if (!cancelled) {
          setProjects(result);
        }
      } catch (err) {
        if (!cancelled) {
          const msg =
            err instanceof Error ? err.message : "Kan projecten niet ophalen";
          setError(msg);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchProjects();
    return () => {
      cancelled = true;
    };
  }, []);

  /** Create a new project on the platform */
  const handleCreate = useCallback(async () => {
    if (!newName.trim()) return;

    setCreating(true);
    try {
      const project = await createProject(newName.trim());
      setProjects((prev) => [...prev, project]);
      setShowNewForm(false);
      setNewName("");
      showToast(`Project "${project.name}" aangemaakt`);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Project aanmaken mislukt";
      showToast(msg, "error");
    } finally {
      setCreating(false);
    }
  }, [newName]);

  /** Sync issues to a selected project */
  const handleSync = useCallback(
    async (projectId: string) => {
      if (issues.length === 0) {
        showToast("Geen issues om te syncen", "error");
        return;
      }

      setSyncing(true);
      setBcfSyncStatus("syncing");
      setBcfPlatformProjectId(projectId);

      try {
        const synced = await syncIssuesToPlatform(
          projectId,
          issues,
          (progress) => {
            const msg = `${progress.current}/${progress.total}: ${progress.title}`;
            setSyncProgress(msg);
            setBcfSyncProgress(msg);
          }
        );

        setBcfSyncStatus("done");
        setBcfSyncProgress(null);
        showToast(`${synced} van ${issues.length} issues gesynchroniseerd`);
        onClose();
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Synchronisatie mislukt";
        setBcfSyncStatus("error");
        setBcfSyncProgress(null);
        showToast(msg, "error");
      } finally {
        setSyncing(false);
      }
    },
    [
      issues,
      onClose,
      setBcfPlatformProjectId,
      setBcfSyncStatus,
      setBcfSyncProgress,
    ]
  );

  /** Close on backdrop click */
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget && !syncing) {
        onClose();
      }
    },
    [onClose, syncing]
  );

  return (
    <div className="bcf-sync-overlay" onClick={handleBackdropClick}>
      <div className="bcf-sync-dialog">
        <div className="bcf-sync-dialog__header">
          <span className="bcf-sync-dialog__title">
            Sync naar BCF Platform
          </span>
          {!syncing && (
            <button
              type="button"
              className="bcf-sync-dialog__close"
              onClick={onClose}
            >
              x
            </button>
          )}
        </div>

        <div className="bcf-sync-dialog__body">
          {/* Syncing state */}
          {syncing && (
            <div className="bcf-sync-dialog__syncing">
              <div className="bcf-panel__spinner" />
              <span>{syncProgress ?? "Synchroniseren..."}</span>
            </div>
          )}

          {/* Error state */}
          {!syncing && error && (
            <div className="bcf-sync-dialog__error">
              <span>{error}</span>
              <p className="bcf-sync-dialog__hint">
                Controleer of de BCF Platform bereikbaar is.
              </p>
            </div>
          )}

          {/* Loading state */}
          {!syncing && !error && loading && (
            <div className="bcf-sync-dialog__loading">
              <div className="bcf-panel__spinner" />
              <span>Projecten laden...</span>
            </div>
          )}

          {/* Project list */}
          {!syncing && !error && !loading && (
            <>
              <div className="bcf-sync-dialog__list">
                {projects.length === 0 && !showNewForm && (
                  <p className="bcf-sync-dialog__empty">
                    Geen projecten gevonden. Maak een nieuw project aan.
                  </p>
                )}

                {projects.map((p) => (
                  <div
                    key={p.project_id}
                    className={`bcf-sync-dialog__project ${
                      platformProjectId === p.project_id
                        ? "bcf-sync-dialog__project--active"
                        : ""
                    }`}
                  >
                    <div className="bcf-sync-dialog__project-info">
                      <span className="bcf-sync-dialog__project-name">
                        {p.name}
                      </span>
                      {p.description && (
                        <span className="bcf-sync-dialog__project-desc">
                          {p.description}
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      className="bcf-panel__action-btn bcf-panel__action-btn--primary"
                      onClick={() => handleSync(p.project_id)}
                    >
                      Sync
                    </button>
                  </div>
                ))}
              </div>

              {/* New project form */}
              {showNewForm ? (
                <div className="bcf-sync-dialog__new-form">
                  <input
                    type="text"
                    className="bcf-sync-dialog__input"
                    placeholder="Projectnaam..."
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleCreate();
                    }}
                    disabled={creating}
                    autoFocus
                  />
                  <button
                    type="button"
                    className="bcf-panel__action-btn bcf-panel__action-btn--primary"
                    onClick={handleCreate}
                    disabled={creating || !newName.trim()}
                  >
                    {creating ? "..." : "Aanmaken"}
                  </button>
                  <button
                    type="button"
                    className="bcf-panel__action-btn"
                    onClick={() => setShowNewForm(false)}
                    disabled={creating}
                  >
                    Annuleer
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  className="bcf-panel__action-btn"
                  onClick={() => setShowNewForm(true)}
                  style={{ marginTop: 8 }}
                >
                  + Nieuw project
                </button>
              )}
            </>
          )}
        </div>

        <div className="bcf-sync-dialog__footer">
          <span className="bcf-sync-dialog__count">
            {issues.length} issue{issues.length !== 1 ? "s" : ""} te syncen
          </span>
        </div>
      </div>
    </div>
  );
}
