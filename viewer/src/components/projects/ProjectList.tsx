/**
 * ProjectList — Backstage panel for managing projects.
 *
 * Shows a list of projects (server or local), with options to
 * create, open, and delete projects.
 */

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import type { ProjectSummary } from "../../services/ProjectStorage";
import type { IProjectStorage } from "../../services/ProjectStorage";
import "./ProjectList.css";

interface ProjectListProps {
  storage: IProjectStorage;
  onOpenProject: (projectId: string) => void;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("nl-NL", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function ProjectList({
  storage,
  onOpenProject,
}: ProjectListProps) {
  const { t } = useTranslation("backstage");
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create project form
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);

  // Delete confirmation
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await storage.listProjects();
      setProjects(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, [storage]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleCreate = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!newName.trim()) return;

      setCreating(true);
      try {
        const project = await storage.createProject(
          newName.trim(),
          newDesc.trim() || undefined
        );
        setNewName("");
        setNewDesc("");
        setShowCreate(false);
        // Open the new project immediately
        onOpenProject(project.id);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to create project"
        );
      } finally {
        setCreating(false);
      }
    },
    [storage, newName, newDesc, onOpenProject]
  );

  const handleDelete = useCallback(
    async (projectId: string) => {
      if (confirmDelete !== projectId) {
        setConfirmDelete(projectId);
        return;
      }

      try {
        await storage.deleteProject(projectId);
        setProjects((prev) => prev.filter((p) => p.id !== projectId));
        setConfirmDelete(null);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to delete project"
        );
      }
    },
    [storage, confirmDelete]
  );

  return (
    <div className="project-list">
      <h2 className="project-list__title">
        {t("projectsPanel.title", "Projecten")}
      </h2>
      <p className="project-list__desc">
        {t(
          "projectsPanel.description",
          "Beheer je BIM validatie projecten."
        )}
      </p>

      {/* Actions bar */}
      <div className="project-list__actions">
        <button
          className="project-list__btn project-list__btn--primary"
          onClick={() => setShowCreate(true)}
          disabled={showCreate}
        >
          + {t("projectsPanel.newProject", "Nieuw project")}
        </button>
        <button
          className="project-list__btn project-list__btn--icon"
          onClick={() => loadProjects()}
          title={t("projectsPanel.refresh", "Vernieuwen")}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <polyline points="23 4 23 10 17 10" />
            <polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
          </svg>
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <form onSubmit={handleCreate} className="project-list__create-form">
          <div className="project-list__field">
            <label className="project-list__label">
              {t("projectsPanel.projectName", "Naam")}
            </label>
            <input
              className="project-list__input"
              type="text"
              placeholder="Kantoorgebouw X"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              disabled={creating}
              autoFocus
            />
          </div>
          <div className="project-list__field">
            <label className="project-list__label">
              {t("projectsPanel.projectDesc", "Beschrijving")}
            </label>
            <input
              className="project-list__input"
              type="text"
              placeholder="BIM validatie project"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              disabled={creating}
            />
          </div>
          <div className="project-list__form-actions">
            <button
              type="submit"
              className="project-list__btn project-list__btn--primary"
              disabled={!newName.trim() || creating}
            >
              {creating
                ? t("projectsPanel.creating", "Aanmaken...")
                : t("projectsPanel.create", "Aanmaken")}
            </button>
            <button
              type="button"
              className="project-list__btn project-list__btn--secondary"
              onClick={() => setShowCreate(false)}
              disabled={creating}
            >
              {t("projectsPanel.cancel", "Annuleren")}
            </button>
          </div>
        </form>
      )}

      {/* Error */}
      {error && (
        <div className="project-list__error">
          <span className="project-list__error-dot" />
          {error}
        </div>
      )}

      {/* Project list */}
      <div className="project-list__items">
        {loading ? (
          <p className="project-list__notice">
            {t("projectsPanel.loading", "Laden...")}
          </p>
        ) : projects.length === 0 ? (
          <p className="project-list__notice">
            {t("projectsPanel.noProjects", "Nog geen projecten.")}
          </p>
        ) : (
          projects.map((project) => (
            <div key={project.id} className="project-list__item">
              <div
                className="project-list__item-main"
                onClick={() => onOpenProject(project.id)}
              >
                <div className="project-list__item-icon">
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
                  </svg>
                </div>
                <div className="project-list__item-info">
                  <span className="project-list__item-name">
                    {project.name}
                  </span>
                  <span className="project-list__item-meta">
                    {project.fileCount}{" "}
                    {project.fileCount === 1 ? "bestand" : "bestanden"} &middot;{" "}
                    {formatDate(project.updatedAt)}
                  </span>
                </div>
              </div>
              <button
                className="project-list__btn project-list__btn--danger project-list__btn--small"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(project.id);
                }}
                title={
                  confirmDelete === project.id ? "Bevestig verwijderen" : "Verwijderen"
                }
              >
                {confirmDelete === project.id ? "!" : "\u00d7"}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
