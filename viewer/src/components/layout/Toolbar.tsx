/**
 * Toolbar — top bar with upload, validation, and view controls.
 *
 * Provides the main action buttons for the platform:
 * - Upload IFC model(s)
 * - Select IDS standard
 * - Run validation
 * - Toggle panels
 */

import { useRef, useCallback, useEffect } from "react";

import { useStore } from "../../store";

import "./Toolbar.css";

/** Maximum IFC file size (500 MB) */
const MAX_FILE_SIZE = 500 * 1024 * 1024;

/**
 * Cache of uploaded File objects, keyed by fileName.
 * Needed because Zustand shouldn't store File objects (not serializable).
 */
const fileCache = new Map<string, File>();

/** Get a cached file by name */
export function getCachedFile(fileName: string): File | undefined {
  return fileCache.get(fileName);
}

export function Toolbar() {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const project = useStore((s) => s.project);
  const createProject = useStore((s) => s.createProject);
  const addModel = useStore((s) => s.addModel);
  const statusMessage = useStore((s) => s.statusMessage);
  const toggleLeftPanel = useStore((s) => s.toggleLeftPanel);
  const toggleRightPanel = useStore((s) => s.toggleRightPanel);
  const leftCollapsed = useStore((s) => s.leftPanelCollapsed);
  const rightCollapsed = useStore((s) => s.rightPanelCollapsed);
  const setActiveRightTab = useStore((s) => s.setActiveRightTab);
  const submitValidation = useStore((s) => s.submitValidation);
  const validationPhase = useStore((s) => s.validationPhase);

  const handleUploadClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files || files.length === 0) return;

      // Ensure project exists
      if (!project) {
        createProject("Nieuw project");
      }

      for (const file of Array.from(files)) {
        // Validate extension
        const ext = file.name.toLowerCase();
        if (!ext.endsWith(".ifc") && !ext.endsWith(".ifcx")) {
          continue;
        }

        // Validate size
        if (file.size > MAX_FILE_SIZE) {
          continue;
        }

        // Cache file object for later use (validation, etc.)
        fileCache.set(file.name, file);

        addModel(file);

        // Dispatch custom event so CenterPanel can pick up the file
        window.dispatchEvent(
          new CustomEvent("model-file-added", { detail: { file } })
        );
      }

      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [project, createProject, addModel]
  );

  const handleValidateClick = useCallback(() => {
    // Find first loaded model
    const loadedModel = project?.models.find((m) => m.loadState === "loaded");
    if (!loadedModel) return;

    // Get cached file
    const file = fileCache.get(loadedModel.fileName);
    if (!file) return;

    // Open validation tab
    setActiveRightTab("validation");

    // Submit validation
    submitValidation(file);
  }, [project, setActiveRightTab, submitValidation]);

  // Listen for validation requests from the ValidationPanel
  useEffect(() => {
    const handleValidationRequest = (e: Event) => {
      const detail = (
        e as CustomEvent<{ modelId: string; fileName: string }>
      ).detail;
      const file = fileCache.get(detail.fileName);
      if (!file) return;

      const { submitValidation: submit } = useStore.getState();
      submit(file);
    };

    window.addEventListener("validation-request", handleValidationRequest);
    return () => {
      window.removeEventListener("validation-request", handleValidationRequest);
    };
  }, []);

  const hasLoadedModel = project?.models.some((m) => m.loadState === "loaded");
  const isValidating =
    validationPhase === "submitting" || validationPhase === "polling";

  return (
    <div className="toolbar">
      <div className="toolbar__left">
        <div className="toolbar__brand">
          <span className="toolbar__logo">3BM</span>
          <span className="toolbar__title">BIM Validator</span>
        </div>

        <div className="toolbar__divider" />

        <button
          type="button"
          className="toolbar__btn toolbar__btn--primary"
          onClick={handleUploadClick}
          title="Upload IFC model"
        >
          + Upload IFC
        </button>

        <button
          type="button"
          className="toolbar__btn toolbar__btn--validate"
          onClick={handleValidateClick}
          disabled={!hasLoadedModel || isValidating}
          title="Valideer geladen model"
        >
          {isValidating ? "Valideren..." : "Valideer"}
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept=".ifc,.ifcx"
          multiple
          onChange={handleFileChange}
          style={{ display: "none" }}
          aria-label="Select IFC file(s)"
        />
      </div>

      <div className="toolbar__center">
        {statusMessage && (
          <span className="toolbar__status">{statusMessage}</span>
        )}
      </div>

      <div className="toolbar__right">
        <button
          type="button"
          className={`toolbar__btn toolbar__btn--toggle ${
            !leftCollapsed ? "toolbar__btn--active" : ""
          }`}
          onClick={toggleLeftPanel}
          title={leftCollapsed ? "Show model browser" : "Hide model browser"}
        >
          Models
        </button>

        <button
          type="button"
          className={`toolbar__btn toolbar__btn--toggle ${
            !rightCollapsed ? "toolbar__btn--active" : ""
          }`}
          onClick={toggleRightPanel}
          title={rightCollapsed ? "Show properties" : "Hide properties"}
        >
          Properties
        </button>
      </div>
    </div>
  );
}
