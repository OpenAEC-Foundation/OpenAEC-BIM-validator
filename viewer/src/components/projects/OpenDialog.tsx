/**
 * OpenDialog — modal for choosing between local and cloud open.
 *
 * Two modes:
 * - Local: file picker for .ifc, .ids, or .zip files
 * - Cloud: list cloud projects and open IFC files from them
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import Modal from "../chrome/Modal";
import { useStore } from "../../store";
import "./OpenDialog.css";

type OpenTarget = "choose" | "local" | "cloud";

interface OpenDialogProps {
  open: boolean;
  onClose: () => void;
  /** Callback when files are selected for opening */
  onFilesSelected?: (files: File[]) => void;
  /** When set, skip the choose screen and go directly to the target */
  directTarget?: "local" | "cloud";
}

export default function OpenDialog({
  open,
  onClose,
  onFilesSelected,
  directTarget,
}: OpenDialogProps) {
  const { t } = useTranslation("projectIo");

  const cloudEnabled = useStore((s) => s.cloudEnabled);
  const cloudProjects = useStore((s) => s.cloudProjects);
  const cloudPhase = useStore((s) => s.cloudPhase);
  const cloudError = useStore((s) => s.cloudError);
  const cloudLoadProjects = useStore((s) => s.cloudLoadProjects);
  const cloudFiles = useStore((s) => s.cloudFiles);
  const cloudLoadFiles = useStore((s) => s.cloudLoadFiles);
  const cloudDownload = useStore((s) => s.cloudDownload);
  const setSaveInfo = useStore((s) => s.setSaveInfo);

  const [target, setTarget] = useState<OpenTarget>("choose");
  const [selectedCloudProject, setSelectedCloudProject] = useState<string>("");
  const [selectedCloudFile, setSelectedCloudFile] = useState<string | null>(null);
  const [isOpening, setIsOpening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      const initial = directTarget ?? "choose";
      setTarget(initial);
      setSelectedCloudProject("");
      setSelectedCloudFile(null);
      setIsOpening(false);
      setError(null);
      // If directTarget is "local", immediately open file picker
      if (initial === "local") {
        // Defer to next tick so the modal renders first
        setTimeout(() => fileInputRef.current?.click(), 0);
      }
    }
  }, [open, directTarget]);

  // Load cloud projects when switching to cloud target
  useEffect(() => {
    if (open && target === "cloud" && cloudEnabled) {
      cloudLoadProjects();
    }
  }, [open, target, cloudEnabled, cloudLoadProjects]);

  // Load files when cloud project changes
  useEffect(() => {
    if (open && selectedCloudProject) {
      cloudLoadFiles(selectedCloudProject);
    }
  }, [open, selectedCloudProject, cloudLoadFiles]);

  const handleLocalOpen = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const fileList = e.target.files;
      if (!fileList || fileList.length === 0) return;

      const files = Array.from(fileList);
      const zipFiles = files.filter((f) =>
        f.name.toLowerCase().endsWith(".zip")
      );

      if (zipFiles.length > 0) {
        // Handle zip: extract IFC files
        setIsOpening(true);
        setError(null);
        try {
          const JSZip = (await import("jszip")).default;
          const extractedFiles: File[] = [];

          for (const zipFile of zipFiles) {
            const zip = await JSZip.loadAsync(zipFile);
            for (const [path, entry] of Object.entries(zip.files)) {
              if (entry.dir) continue;
              const lower = path.toLowerCase();
              if (lower.endsWith(".ifc") || lower.endsWith(".ifcx") || lower.endsWith(".ids")) {
                const blob = await entry.async("blob");
                const fileName = path.split("/").pop() ?? path;
                extractedFiles.push(
                  new File([blob], fileName, {
                    type: "application/octet-stream",
                  })
                );
              }
            }
          }

          // Also include any non-zip files that were selected
          const otherFiles = files.filter(
            (f) => !f.name.toLowerCase().endsWith(".zip")
          );
          const allFiles = [...extractedFiles, ...otherFiles];

          if (allFiles.length > 0) {
            const firstZip = zipFiles[0];
            setSaveInfo({ source: "local", localFilename: firstZip?.name });
            onFilesSelected?.(allFiles);
          }
          onClose();
        } catch (err) {
          setError(err instanceof Error ? err.message : t("error"));
        } finally {
          setIsOpening(false);
        }
      } else {
        // Direct IFC/IDS files
        setSaveInfo({ source: "local" });
        onFilesSelected?.(files);
        onClose();
      }

      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [onFilesSelected, onClose, setSaveInfo, t]
  );

  const handleCloudOpen = useCallback(async () => {
    if (!selectedCloudProject || !selectedCloudFile) return;
    setIsOpening(true);
    setError(null);

    try {
      const blob = await cloudDownload(selectedCloudProject, selectedCloudFile);
      if (blob) {
        const file = new File([blob], selectedCloudFile, {
          type: "application/octet-stream",
        });
        setSaveInfo({ source: "cloud", cloudProject: selectedCloudProject });
        onFilesSelected?.([file]);
        onClose();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
    } finally {
      setIsOpening(false);
    }
  }, [
    selectedCloudProject,
    selectedCloudFile,
    cloudDownload,
    setSaveInfo,
    onFilesSelected,
    onClose,
    t,
  ]);

  const isCloudBusy =
    cloudPhase === "loading" || cloudPhase === "downloading";
  const canOpenCloud =
    !!selectedCloudProject && !!selectedCloudFile && !isCloudBusy && !isOpening;

  const footer = target === "cloud" ? (
    <div className="open-dialog__footer">
      {(error || cloudError) && (
        <span className="open-dialog__error">
          {error || cloudError}
        </span>
      )}
      <div className="open-dialog__actions">
        <button
          className="open-dialog__btn open-dialog__btn--secondary"
          onClick={() => setTarget("choose")}
        >
          {t("cancel")}
        </button>
        <button
          className="open-dialog__btn open-dialog__btn--primary"
          onClick={handleCloudOpen}
          disabled={!canOpenCloud}
        >
          {isOpening ? t("opening") : t("open")}
        </button>
      </div>
    </div>
  ) : undefined;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("openTitle")}
      width={520}
      footer={footer}
    >
      <div className="open-dialog__body">
        {target === "choose" && (
          <div className="open-dialog__options">
            <button
              className="open-dialog__option"
              onClick={handleLocalOpen}
            >
              <div className="open-dialog__option-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
                  <line x1="12" y1="11" x2="12" y2="17" />
                  <polyline points="9 14 12 11 15 14" />
                </svg>
              </div>
              <div className="open-dialog__option-text">
                <strong>{t("openLocal")}</strong>
                <span>{t("openLocalDesc")}</span>
              </div>
            </button>

            <button
              className="open-dialog__option"
              onClick={() => setTarget("cloud")}
              disabled={!cloudEnabled}
            >
              <div className="open-dialog__option-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 10h-1.26A8 8 0 109 20h9a5 5 0 000-10z" />
                  <polyline points="12 13 12 19" />
                  <polyline points="9 16 12 19 15 16" />
                </svg>
              </div>
              <div className="open-dialog__option-text">
                <strong>{t("openCloud")}</strong>
                <span>
                  {cloudEnabled
                    ? t("openCloudDesc")
                    : t("cloudNotConfigured")}
                </span>
              </div>
            </button>
          </div>
        )}

        {target === "cloud" && (
          <div className="open-dialog__form">
            <div className="open-dialog__field">
              <label className="open-dialog__label">
                {t("selectProject")}
              </label>
              <div className="open-dialog__project-row">
                <select
                  className="open-dialog__select"
                  value={selectedCloudProject}
                  onChange={(e) => {
                    setSelectedCloudProject(e.target.value);
                    setSelectedCloudFile(null);
                  }}
                  disabled={isCloudBusy || isOpening}
                >
                  <option value="">{t("selectProject")}</option>
                  {cloudProjects.map((p) => (
                    <option key={p.name} value={p.name}>
                      {p.name}
                    </option>
                  ))}
                </select>
                <button
                  className="open-dialog__btn open-dialog__btn--icon"
                  onClick={() => cloudLoadProjects()}
                  disabled={isCloudBusy || isOpening}
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

            {/* .wefc manifest selector removed — open IFC files directly. */}

            {selectedCloudProject && (
              <div className="open-dialog__files">
                {isCloudBusy && cloudPhase === "loading" ? (
                  <p className="open-dialog__notice">{t("loading")}</p>
                ) : cloudFiles.length === 0 ? (
                  <p className="open-dialog__notice">{t("noProjects")}</p>
                ) : (
                  <div className="open-dialog__file-list">
                    {cloudFiles
                      .filter((f) => {
                        const name = f.name.toLowerCase();
                        return (
                          name.endsWith(".ifc") ||
                          name.endsWith(".ifcx") ||
                          name.endsWith(".ids") ||
                          name.endsWith(".zip")
                        );
                      })
                      .map((file) => (
                        <button
                          key={file.name}
                          className={`open-dialog__file-item${
                            selectedCloudFile === file.name
                              ? " open-dialog__file-item--selected"
                              : ""
                          }`}
                          onClick={() => setSelectedCloudFile(file.name)}
                        >
                          <span className="open-dialog__file-name">
                            {file.name}
                          </span>
                          <span className="open-dialog__file-meta">
                            {formatFileSize(file.size)}
                          </span>
                        </button>
                      ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Hidden file input for local open */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".ifc,.ifcx,.ids,.zip"
        multiple
        onChange={handleFileChange}
        style={{ display: "none" }}
        aria-label="Select project files"
      />
    </Modal>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const size = bytes / Math.pow(1024, i);
  return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}
