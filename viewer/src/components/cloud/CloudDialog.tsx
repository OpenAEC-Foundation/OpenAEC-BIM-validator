/**
 * CloudDialog — modal for saving/opening BCF files to/from Nextcloud.
 *
 * Uses the Modal component and cloud store slice. Two modes:
 * - "save": upload a BCF blob to a selected project
 * - "open": download a BCF file from a project
 */

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import Modal from "../chrome/Modal";
import { useStore } from "../../store";
import "./CloudDialog.css";

interface CloudDialogProps {
  open: boolean;
  onClose: () => void;
  mode: "save" | "open";
  bcfBlob?: Blob;
  suggestedFilename?: string;
  onFileOpened?: (blob: Blob, filename: string) => void;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const size = bytes / Math.pow(1024, i);
  return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

export default function CloudDialog({
  open,
  onClose,
  mode,
  bcfBlob,
  suggestedFilename,
  onFileOpened,
}: CloudDialogProps) {
  const { t } = useTranslation("cloud");

  const cloudEnabled = useStore((s) => s.cloudEnabled);
  const cloudPhase = useStore((s) => s.cloudPhase);
  const cloudError = useStore((s) => s.cloudError);
  const cloudProjects = useStore((s) => s.cloudProjects);
  const cloudSelectedProject = useStore((s) => s.cloudSelectedProject);
  const cloudFiles = useStore((s) => s.cloudFiles);
  const cloudLoadProjects = useStore((s) => s.cloudLoadProjects);
  const cloudSelectProject = useStore((s) => s.cloudSelectProject);
  const cloudLoadFiles = useStore((s) => s.cloudLoadFiles);
  const cloudUpload = useStore((s) => s.cloudUpload);
  const cloudDownload = useStore((s) => s.cloudDownload);
  const cloudDelete = useStore((s) => s.cloudDelete);

  const [filename, setFilename] = useState(suggestedFilename ?? "validation.bcf");
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [confirmOverwrite, setConfirmOverwrite] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  // Load projects when dialog opens
  useEffect(() => {
    if (open && cloudEnabled) {
      cloudLoadProjects();
    }
  }, [open, cloudEnabled, cloudLoadProjects]);

  // Reset local state when dialog opens
  useEffect(() => {
    if (open) {
      setFilename(suggestedFilename ?? "validation.bcf");
      setSelectedFile(null);
      setConfirmOverwrite(false);
      setConfirmDelete(null);
    }
  }, [open, suggestedFilename]);

  // Load files when project changes
  useEffect(() => {
    if (open && cloudSelectedProject) {
      cloudLoadFiles(cloudSelectedProject);
    }
  }, [open, cloudSelectedProject, cloudLoadFiles]);

  const handleProjectChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const value = e.target.value || null;
      cloudSelectProject(value);
    },
    [cloudSelectProject],
  );

  const handleSave = useCallback(async () => {
    if (!cloudSelectedProject || !bcfBlob || !filename) return;

    // Check if file exists → prompt overwrite
    const existing = cloudFiles.find((f) => f.name === filename);
    if (existing && !confirmOverwrite) {
      setConfirmOverwrite(true);
      return;
    }

    const success = await cloudUpload(cloudSelectedProject, filename, bcfBlob);
    if (success) {
      setConfirmOverwrite(false);
      onClose();
    }
  }, [
    cloudSelectedProject,
    bcfBlob,
    filename,
    cloudFiles,
    confirmOverwrite,
    cloudUpload,
    onClose,
  ]);

  const handleOpen = useCallback(async () => {
    if (!cloudSelectedProject || !selectedFile) return;

    const blob = await cloudDownload(cloudSelectedProject, selectedFile);
    if (blob) {
      onFileOpened?.(blob, selectedFile);
      onClose();
    }
  }, [cloudSelectedProject, selectedFile, cloudDownload, onFileOpened, onClose]);

  const handleDelete = useCallback(
    async (fname: string) => {
      if (confirmDelete !== fname) {
        setConfirmDelete(fname);
        return;
      }
      if (!cloudSelectedProject) return;
      await cloudDelete(cloudSelectedProject, fname);
      setConfirmDelete(null);
    },
    [cloudSelectedProject, confirmDelete, cloudDelete],
  );

  const isBusy =
    cloudPhase === "loading" ||
    cloudPhase === "uploading" ||
    cloudPhase === "downloading" ||
    cloudPhase === "deleting";

  const title = mode === "save" ? t("saveTitle") : t("openTitle");

  const footer = (
    <div className="cloud-dialog__footer">
      {cloudError && <span className="cloud-dialog__error">{cloudError}</span>}
      <div className="cloud-dialog__actions">
        <button
          className="cloud-dialog__btn cloud-dialog__btn--secondary"
          onClick={onClose}
        >
          {t("cancel")}
        </button>
        {mode === "save" ? (
          <button
            className="cloud-dialog__btn cloud-dialog__btn--primary"
            onClick={handleSave}
            disabled={!cloudSelectedProject || !filename || isBusy}
          >
            {cloudPhase === "uploading" ? t("uploading") : confirmOverwrite ? t("overwriteConfirm") : t("save")}
          </button>
        ) : (
          <button
            className="cloud-dialog__btn cloud-dialog__btn--primary"
            onClick={handleOpen}
            disabled={!cloudSelectedProject || !selectedFile || isBusy}
          >
            {cloudPhase === "downloading" ? t("downloading") : t("open")}
          </button>
        )}
      </div>
    </div>
  );

  if (!cloudEnabled) {
    return (
      <Modal open={open} onClose={onClose} title={title} width={560} footer={footer}>
        <div className="cloud-dialog__body">
          <p className="cloud-dialog__notice">{t("notConfigured")}</p>
        </div>
      </Modal>
    );
  }

  return (
    <Modal open={open} onClose={onClose} title={title} width={560} footer={footer}>
      <div className="cloud-dialog__body">
        {/* Project selector */}
        <div className="cloud-dialog__row">
          <label className="cloud-dialog__label">{t("project")}</label>
          <div className="cloud-dialog__project-row">
            <select
              className="cloud-dialog__select"
              value={cloudSelectedProject ?? ""}
              onChange={handleProjectChange}
              disabled={isBusy}
            >
              <option value="">{t("selectProject")}</option>
              {cloudProjects.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name}
                </option>
              ))}
            </select>
            <button
              className="cloud-dialog__btn cloud-dialog__btn--icon"
              onClick={() => cloudLoadProjects()}
              disabled={isBusy}
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

        {/* Save mode: filename input */}
        {mode === "save" && (
          <div className="cloud-dialog__row">
            <label className="cloud-dialog__label">{t("filename")}</label>
            <input
              className="cloud-dialog__input"
              type="text"
              value={filename}
              onChange={(e) => {
                setFilename(e.target.value);
                setConfirmOverwrite(false);
              }}
              disabled={isBusy}
            />
          </div>
        )}

        {/* File list */}
        {cloudSelectedProject && (
          <div className="cloud-dialog__files">
            {isBusy && cloudPhase === "loading" ? (
              <p className="cloud-dialog__notice">{t("loading")}</p>
            ) : cloudFiles.length === 0 ? (
              <p className="cloud-dialog__notice">{t("noFiles")}</p>
            ) : (
              <table className="cloud-dialog__table">
                <thead>
                  <tr>
                    <th>{t("filename")}</th>
                    <th>{t("fileSize")}</th>
                    <th>{t("lastModified")}</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {cloudFiles.map((file) => (
                    <tr
                      key={file.name}
                      className={
                        mode === "open" && selectedFile === file.name
                          ? "cloud-dialog__row--selected"
                          : ""
                      }
                      onClick={() => {
                        if (mode === "open") setSelectedFile(file.name);
                        if (mode === "save") setFilename(file.name);
                      }}
                    >
                      <td>{file.name}</td>
                      <td>{formatFileSize(file.size)}</td>
                      <td>{file.last_modified}</td>
                      <td>
                        <button
                          className="cloud-dialog__btn cloud-dialog__btn--danger cloud-dialog__btn--small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(file.name);
                          }}
                          disabled={isBusy}
                          title={
                            confirmDelete === file.name
                              ? t("deleteConfirm")
                              : t("delete")
                          }
                        >
                          {confirmDelete === file.name ? "!" : "\u00d7"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}
