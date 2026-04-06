/**
 * SaveAsDialog — modal for choosing between local and cloud save.
 *
 * Two modes:
 * - Local: generates a .zip with IFC + IDS + validation results and triggers download
 * - Cloud: saves files to a Nextcloud project folder with project container structure
 */

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import Modal from "../chrome/Modal";
import { useStore } from "../../store";
import "./SaveAsDialog.css";

type SaveTarget = "choose" | "local" | "cloud";

interface SaveAsDialogProps {
  open: boolean;
  onClose: () => void;
  /** When true, skip the choose screen and go directly to the save target */
  directTarget?: "local" | "cloud";
  /** Callback after successful save */
  onSaveComplete?: (target: "local" | "cloud", projectName: string) => void;
}

export default function SaveAsDialog({
  open,
  onClose,
  directTarget,
  onSaveComplete,
}: SaveAsDialogProps) {
  const { t } = useTranslation("projectIo");

  const project = useStore((s) => s.project);
  const cloudEnabled = useStore((s) => s.cloudEnabled);
  const cloudProjects = useStore((s) => s.cloudProjects);
  const cloudPhase = useStore((s) => s.cloudPhase);
  const cloudError = useStore((s) => s.cloudError);
  const cloudLoadProjects = useStore((s) => s.cloudLoadProjects);
  const cloudUpload = useStore((s) => s.cloudUpload);
  const cloudSaveManifest = useStore((s) => s.cloudSaveManifest);
  const validationResult = useStore((s) => s.validationResult);
  const bcfIssues = useStore((s) => s.bcfIssues);
  const setSaveInfo = useStore((s) => s.setSaveInfo);
  const markClean = useStore((s) => s.markClean);

  const [target, setTarget] = useState<SaveTarget>("choose");
  const [projectName, setProjectName] = useState("");
  const [selectedCloudProject, setSelectedCloudProject] = useState<string>("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      setTarget(directTarget ?? "choose");
      setProjectName(project?.name ?? "");
      setSelectedCloudProject("");
      setIsSaving(false);
      setError(null);
    }
  }, [open, directTarget, project?.name]);

  // Load cloud projects when switching to cloud target
  useEffect(() => {
    if (open && target === "cloud" && cloudEnabled) {
      cloudLoadProjects();
    }
  }, [open, target, cloudEnabled, cloudLoadProjects]);

  const handleLocalSave = useCallback(async () => {
    if (!project) return;
    setIsSaving(true);
    setError(null);

    try {
      const JSZip = (await import("jszip")).default;
      const zip = new JSZip();

      const name = projectName || project.name || "project";

      // Add IFC files from IndexedDB
      const { getModelBytes } = await import("../../engine/modelCache");
      for (const model of project.models) {
        const bytes = await getModelBytes(model.fileName);
        if (bytes) {
          zip.file(`models/${model.fileName}`, bytes);
        }
      }

      // Add validation results if available
      if (validationResult) {
        zip.file(
          "validation/results/validation-result.json",
          JSON.stringify(validationResult, null, 2)
        );
      }

      // Add project manifest
      const manifest = {
        name,
        created: new Date().toISOString(),
        tool: "bim-validator",
        version: "1.0",
        models: project.models.map((m) => ({
          fileName: m.fileName,
          fileSize: m.fileSize,
          format: m.format,
        })),
        hasValidation: !!validationResult,
      };
      zip.file("project.json", JSON.stringify(manifest, null, 2));

      // Generate and download
      const blob = await zip.generateAsync({ type: "blob" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${name}.zip`;
      a.click();
      URL.revokeObjectURL(url);

      setSaveInfo({
        source: "local",
        localFilename: `${name}.zip`,
        dirty: false,
      });
      markClean();
      onSaveComplete?.("local", name);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setIsSaving(false);
    }
  }, [
    project,
    projectName,
    validationResult,
    setSaveInfo,
    markClean,
    onSaveComplete,
    onClose,
    t,
  ]);

  const handleCloudSave = useCallback(async () => {
    if (!project || !selectedCloudProject) return;
    setIsSaving(true);
    setError(null);

    try {
      const now = new Date().toISOString();
      const manifestData: Record<string, unknown>[] = [];

      // Upload IFC files to models/ directory
      const { getModelBytes } = await import("../../engine/modelCache");
      for (const model of project.models) {
        const bytes = await getModelBytes(model.fileName);
        if (bytes) {
          const blob = new Blob([bytes], {
            type: "application/octet-stream",
          });
          await cloudUpload(selectedCloudProject, model.fileName, blob, "bim");
          manifestData.push({
            type: "WefcModel",
            guid: model.id,
            name: model.fileName,
            path: `models/${model.fileName}`,
            format: model.format ?? "ifc",
            fileSize: model.fileSize,
            status: "active",
            created: now,
            modified: now,
          });
        }
      }

      // Upload validation results to validation/ directory
      if (validationResult) {
        const resultBlob = new Blob(
          [JSON.stringify(validationResult, null, 2)],
          { type: "application/json" }
        );
        await cloudUpload(
          selectedCloudProject,
          "validation-result.json",
          resultBlob,
          "output",
        );
        manifestData.push({
          type: "WefcValidation",
          guid: crypto.randomUUID(),
          name: `BIM Validatie - ${now.slice(0, 10)}`,
          path: "validation/validation-result.json",
          status: "active",
          created: now,
          modified: now,
        });
      }

      // Upload BCF issues as .bcf zip to validation/ directory
      if (bcfIssues.length > 0) {
        const { generateBcfZip } = await import("../../lib/bcfZipGenerator");
        const bcfBlob = await generateBcfZip(bcfIssues);
        const bcfFilename = `${project.name ?? "issues"}.bcf`;
        await cloudUpload(
          selectedCloudProject,
          bcfFilename,
          bcfBlob,
          "output",
        );
        manifestData.push({
          type: "WefcBcf",
          guid: crypto.randomUUID(),
          name: `BCF Issues - ${now.slice(0, 10)}`,
          path: `validation/${bcfFilename}`,
          issueCount: bcfIssues.length,
          status: "active",
          created: now,
          modified: now,
        });
      }

      // Save project.wefc manifest
      await cloudSaveManifest(selectedCloudProject, {
        header: {
          schema: "WeFC",
          schema_version: "1.1.0",
          fileId: crypto.randomUUID(),
          timestamp: now,
          application: "bim-validator",
        },
        data: manifestData,
      });

      setSaveInfo({
        source: "cloud",
        cloudProject: selectedCloudProject,
        dirty: false,
      });
      markClean();
      onSaveComplete?.("cloud", selectedCloudProject);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setIsSaving(false);
    }
  }, [
    project,
    selectedCloudProject,
    validationResult,
    bcfIssues,
    cloudUpload,
    cloudSaveManifest,
    setSaveInfo,
    markClean,
    onSaveComplete,
    onClose,
    t,
  ]);

  const isCloudBusy = cloudPhase === "loading" || cloudPhase === "uploading";
  const canSaveCloud = !!selectedCloudProject && !isCloudBusy && !isSaving;
  const canSaveLocal = !!project && !isSaving;

  const footer = (
    <div className="saveas-dialog__footer">
      {(error || cloudError) && (
        <span className="saveas-dialog__error">
          {error || cloudError}
        </span>
      )}
      <div className="saveas-dialog__actions">
        <button
          className="saveas-dialog__btn saveas-dialog__btn--secondary"
          onClick={target === "choose" ? onClose : () => setTarget("choose")}
        >
          {target === "choose" ? t("cancel") : t("cancel")}
        </button>
        {target === "local" && (
          <button
            className="saveas-dialog__btn saveas-dialog__btn--primary"
            onClick={handleLocalSave}
            disabled={!canSaveLocal}
          >
            {isSaving ? t("saving") : t("save")}
          </button>
        )}
        {target === "cloud" && (
          <button
            className="saveas-dialog__btn saveas-dialog__btn--primary"
            onClick={handleCloudSave}
            disabled={!canSaveCloud}
          >
            {isSaving ? t("saving") : t("save")}
          </button>
        )}
      </div>
    </div>
  );

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("saveAsTitle")}
      width={520}
      footer={target !== "choose" ? footer : undefined}
    >
      <div className="saveas-dialog__body">
        {target === "choose" && (
          <div className="saveas-dialog__options">
            <button
              className="saveas-dialog__option"
              onClick={() => setTarget("local")}
            >
              <div className="saveas-dialog__option-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
              </div>
              <div className="saveas-dialog__option-text">
                <strong>{t("saveLocal")}</strong>
                <span>{t("saveLocalDesc")}</span>
              </div>
            </button>

            <button
              className="saveas-dialog__option"
              onClick={() => setTarget("cloud")}
              disabled={!cloudEnabled}
            >
              <div className="saveas-dialog__option-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 10h-1.26A8 8 0 109 20h9a5 5 0 000-10z" />
                  <polyline points="12 13 12 7" />
                  <polyline points="9 10 12 7 15 10" />
                </svg>
              </div>
              <div className="saveas-dialog__option-text">
                <strong>{t("saveCloud")}</strong>
                <span>
                  {cloudEnabled
                    ? t("saveCloudDesc")
                    : t("cloudNotConfigured")}
                </span>
              </div>
            </button>
          </div>
        )}

        {target === "local" && (
          <div className="saveas-dialog__form">
            <div className="saveas-dialog__field">
              <label className="saveas-dialog__label">
                {t("projectName")}
              </label>
              <input
                className="saveas-dialog__input"
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder={t("projectNamePlaceholder")}
                disabled={isSaving}
                autoFocus
              />
            </div>
            {project && project.models.length > 0 && (
              <div className="saveas-dialog__preview">
                <span className="saveas-dialog__preview-label">
                  {t("projectFiles")}:
                </span>
                <ul className="saveas-dialog__file-list">
                  {project.models.map((m) => (
                    <li key={m.id}>{m.fileName}</li>
                  ))}
                  {validationResult && (
                    <li>validation-result.json</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        )}

        {target === "cloud" && (
          <div className="saveas-dialog__form">
            <div className="saveas-dialog__field">
              <label className="saveas-dialog__label">
                {t("selectProject")}
              </label>
              <div className="saveas-dialog__project-row">
                <select
                  className="saveas-dialog__select"
                  value={selectedCloudProject}
                  onChange={(e) => setSelectedCloudProject(e.target.value)}
                  disabled={isCloudBusy || isSaving}
                >
                  <option value="">{t("selectProject")}</option>
                  {cloudProjects.map((p) => (
                    <option key={p.name} value={p.name}>
                      {p.name}
                    </option>
                  ))}
                </select>
                <button
                  className="saveas-dialog__btn saveas-dialog__btn--icon"
                  onClick={() => cloudLoadProjects()}
                  disabled={isCloudBusy || isSaving}
                  title={t("refresh")}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="23 4 23 10 17 10" />
                    <polyline points="1 20 1 14 7 14" />
                    <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
                  </svg>
                </button>
              </div>
            </div>
            {project && project.models.length > 0 && (
              <div className="saveas-dialog__preview">
                <span className="saveas-dialog__preview-label">
                  {t("projectFiles")}:
                </span>
                <ul className="saveas-dialog__file-list">
                  {project.models.map((m) => (
                    <li key={m.id}>{m.fileName}</li>
                  ))}
                  {validationResult && (
                    <li>validation-result.json</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}
