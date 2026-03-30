/**
 * AppShell — Chrome orchestration for the BIM Validator.
 *
 * Replaces the old Toolbar with OpenAEC Chrome design system:
 * TitleBar + Ribbon + Panels + StatusBar + Backstage + Dialogs.
 */

import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import {
  Panel,
  Group,
  Separator,
} from "react-resizable-panels";

import { useStore } from "../../store";
import { useDemoMode } from "../../demo/useDemoMode";
import { getSetting } from "../../utils/settingsStore";
import { applyTheme } from "../../utils/settingsStore";
import { useKeyboardShortcuts } from "../../hooks/useKeyboardShortcuts";
import {
  getCachedFile,
  setCachedFile,
  saveModelBytes,
} from "../../engine/modelCache";

import TitleBar from "../chrome/TitleBar";
import Ribbon from "../chrome/ribbon/Ribbon";
import StatusBar from "../chrome/StatusBar";
import Backstage from "../chrome/backstage/Backstage";
import SettingsDialog from "../chrome/settings/SettingsDialog";
import FeedbackDialog from "../feedback/FeedbackDialog";
import CloudDialog from "../cloud/CloudDialog";
import SaveAsDialog from "../projects/SaveAsDialog";
import OpenDialog from "../projects/OpenDialog";

import { LeftPanel } from "./LeftPanel";
import { CenterPanel } from "./CenterPanel";
import { RightPanel } from "./RightPanel";
import { ToastContainer } from "../Toast";

import { ServerProjectStorage } from "../../services/ServerProjectStorage";

import "./AppShell.css";

/** Maximum IFC file size (500 MB) */
const MAX_FILE_SIZE = 500 * 1024 * 1024;

/** Default panel sizes (percentages) */
const LEFT_PANEL_DEFAULT = "25%";
const LEFT_PANEL_MIN = "15%";
const RIGHT_PANEL_DEFAULT = "25%";
const RIGHT_PANEL_MIN = "15%";
const CENTER_PANEL_MIN = "30%";

/** Re-export for backward compat */
export { getCachedFile };

export function AppShell() {
  useDemoMode();

  // --- Store state ---
  const project = useStore((s) => s.project);
  const createProject = useStore((s) => s.createProject);
  const addModel = useStore((s) => s.addModel);
  const leftCollapsed = useStore((s) => s.leftPanelCollapsed);
  const rightCollapsed = useStore((s) => s.rightPanelCollapsed);
  const toggleLeftPanel = useStore((s) => s.toggleLeftPanel);
  const toggleRightPanel = useStore((s) => s.toggleRightPanel);
  const setActiveRightTab = useStore((s) => s.setActiveRightTab);
  const submitValidation = useStore((s) => s.submitValidation);
  const validationPhase = useStore((s) => s.validationPhase);
  const cloudEnabled = useStore((s) => s.cloudEnabled);
  const cloudCheckStatus = useStore((s) => s.cloudCheckStatus);

  // BCF platform state
  const bcfPhase = useStore((s) => s.bcfPhase);
  const bcfIssues = useStore((s) => s.bcfIssues);
  const bcfSelectedProjectId = useStore((s) => s.bcfSelectedProjectId);
  const bcfPushIssues = useStore((s) => s.bcfPushIssues);
  const bcfInitAuth = useStore((s) => s.bcfInitAuth);

  const bcfConnected = bcfPhase === "connected" || bcfPhase === "pushing" || bcfPhase === "done";
  const bcfHasQueuedIssues = bcfIssues.some((i) => i.pushState === "queued");

  // Project I/O state
  const projectSaveInfo = useStore((s) => s.projectSaveInfo);
  const markClean = useStore((s) => s.markClean);

  // --- Local chrome state ---
  const [backstageOpen, setBackstageOpen] = useState(false);
  const [backstageInitialPanel, setBackstageInitialPanel] = useState<string | undefined>();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [cloudDialogOpen, setCloudDialogOpen] = useState(false);
  const [cloudDialogMode, setCloudDialogMode] = useState<"save" | "open">("save");
  const [cloudBcfBlob, setCloudBcfBlob] = useState<Blob | undefined>();
  const [saveAsDialogOpen, setSaveAsDialogOpen] = useState(false);
  const [saveAsDirectTarget, setSaveAsDirectTarget] = useState<"local" | "cloud" | undefined>();
  const [openDialogOpen, setOpenDialogOpen] = useState(false);
  const [openDirectTarget, setOpenDirectTarget] = useState<"local" | "cloud" | undefined>();
  const [theme, setTheme] = useState(() => getSetting("theme", "light"));

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Project storage (server-backed)
  const projectStorage = useMemo(() => new ServerProjectStorage(), []);

  // Open a server project: load its files into the viewer
  const handleOpenProject = useCallback(
    async (projectId: string) => {
      try {
        const detail = await projectStorage.getProject(projectId);

        // Create project in store
        if (!project || project.id !== detail.id) {
          createProject(detail.name);
        }

        // Load IFC files
        const ifcFiles = detail.files.filter((f) => f.fileType === "ifc");
        for (const fileInfo of ifcFiles) {
          const blob = await projectStorage.getFileBlob(projectId, fileInfo.id);
          const file = new File([blob], fileInfo.fileName, {
            type: "application/octet-stream",
          });

          setCachedFile(file.name, file);
          const bytes = await file.arrayBuffer();
          await saveModelBytes(file.name, bytes);
          addModel(file);
          window.dispatchEvent(
            new CustomEvent("model-file-added", { detail: { file } })
          );
        }
      } catch (err) {
        console.error("Failed to open project:", err);
      }
    },
    [projectStorage, project, createProject, addModel]
  );

  // Apply theme on mount
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // Check cloud status on mount
  useEffect(() => {
    cloudCheckStatus();
  }, [cloudCheckStatus]);

  // Initialize BCF auth on mount (restore OIDC session or API key)
  useEffect(() => {
    void bcfInitAuth();
  }, [bcfInitAuth]);

  // Listen for validation requests from the ValidationPanel
  useEffect(() => {
    const handleValidationRequest = (e: Event) => {
      const detail = (
        e as CustomEvent<{ modelId: string; fileName: string }>
      ).detail;
      const file = getCachedFile(detail.fileName);
      if (!file) return;
      const { submitValidation: submit } = useStore.getState();
      submit(file);
    };

    window.addEventListener("validation-request", handleValidationRequest);
    return () => {
      window.removeEventListener("validation-request", handleValidationRequest);
    };
  }, []);

  // --- Handlers ---
  const handleUploadClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files || files.length === 0) return;

      if (!project) {
        createProject("Nieuw project");
      }

      for (const file of Array.from(files)) {
        const ext = file.name.toLowerCase();
        if (!ext.endsWith(".ifc") && !ext.endsWith(".ifcx")) continue;
        if (file.size > MAX_FILE_SIZE) continue;

        setCachedFile(file.name, file);
        file.arrayBuffer().then((bytes) => {
          saveModelBytes(file.name, bytes).catch(console.error);
        });
        addModel(file);
        window.dispatchEvent(
          new CustomEvent("model-file-added", { detail: { file } })
        );
      }

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [project, createProject, addModel]
  );

  const handleValidateClick = useCallback(() => {
    const loadedModel = project?.models.find((m) => m.loadState === "loaded");
    if (!loadedModel) return;
    const file = getCachedFile(loadedModel.fileName);
    if (!file) return;
    setActiveRightTab("validation");
    submitValidation(file);
  }, [project, setActiveRightTab, submitValidation]);

  const handleExportBcf = useCallback(() => {
    // BCF export trigger — dispatches event for BcfPanel to handle
    window.dispatchEvent(new CustomEvent("bcf-export-request"));
  }, []);

  const handleCloudSave = useCallback(() => {
    // Generate BCF blob first, then open cloud dialog in save mode
    const { bcfIssues } = useStore.getState();
    if (bcfIssues.length === 0) return;

    import("../../lib/bcfZipGenerator").then(({ generateBcfZip }) => {
      generateBcfZip(bcfIssues).then((blob) => {
        const timestamp = new Date().toISOString().slice(0, 10);
        setCloudBcfBlob(blob);
        setCloudDialogMode("save");
        setCloudDialogOpen(true);
        // Update suggested filename based on project
        const projectName = project?.name ?? "validation";
        void projectName;
        void timestamp;
      }).catch(console.error);
    }).catch(console.error);
  }, [project]);

  const handleBcfLogin = useCallback(() => {
    setBackstageInitialPanel("bcf-platform");
    setBackstageOpen(true);
  }, []);

  const handleBcfPush = useCallback(() => {
    if (!bcfConnected || !bcfSelectedProjectId || !bcfHasQueuedIssues) return;
    void bcfPushIssues();
  }, [bcfConnected, bcfSelectedProjectId, bcfHasQueuedIssues, bcfPushIssues]);

  const handleCloudOpen = useCallback(() => {
    setCloudDialogMode("open");
    setCloudBcfBlob(undefined);
    setCloudDialogOpen(true);
  }, []);

  const handleCloudFileOpened = useCallback((blob: Blob, filename: string) => {
    // Download the BCF file to local filesystem
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  // --- Save / Save As / Open handlers ---
  const handleSave = useCallback(() => {
    if (!project) return;
    // If we have a known save location, save directly there
    if (projectSaveInfo.source === "cloud" && projectSaveInfo.cloudProject) {
      // Direct cloud save — reuse the cloud upload flow
      const doCloudSave = async () => {
        const { getModelBytes } = await import("../../engine/modelCache");
        const cloudUploadFn = useStore.getState().cloudUpload;
        for (const model of project.models) {
          const bytes = await getModelBytes(model.fileName);
          if (bytes) {
            const blob = new Blob([bytes], { type: "application/octet-stream" });
            await cloudUploadFn(projectSaveInfo.cloudProject!, model.fileName, blob);
          }
        }
        markClean();
      };
      doCloudSave().catch(console.error);
      return;
    }
    // No previous save location or local → open SaveAs dialog
    setSaveAsDialogOpen(true);
  }, [project, projectSaveInfo, markClean]);

  const handleSaveAs = useCallback(() => {
    if (!project) return;
    setSaveAsDirectTarget(undefined);
    setSaveAsDialogOpen(true);
  }, [project]);

  const handleSaveAsLocal = useCallback(() => {
    if (!project) return;
    setSaveAsDirectTarget("local");
    setSaveAsDialogOpen(true);
  }, [project]);

  const handleSaveAsCloud = useCallback(() => {
    if (!project) return;
    setSaveAsDirectTarget("cloud");
    setSaveAsDialogOpen(true);
  }, [project]);

  const handleOpen = useCallback(() => {
    setOpenDirectTarget(undefined);
    setOpenDialogOpen(true);
  }, []);

  const handleOpenLocal = useCallback(() => {
    setOpenDirectTarget("local");
    setOpenDialogOpen(true);
  }, []);

  const handleOpenCloudDirect = useCallback(() => {
    setOpenDirectTarget("cloud");
    setOpenDialogOpen(true);
  }, []);

  const handleOpenFilesSelected = useCallback(
    (files: File[]) => {
      if (!project) {
        createProject("Nieuw project");
      }

      for (const file of files) {
        const ext = file.name.toLowerCase();
        if (!ext.endsWith(".ifc") && !ext.endsWith(".ifcx")) continue;
        if (file.size > MAX_FILE_SIZE) continue;

        setCachedFile(file.name, file);
        file.arrayBuffer().then((bytes) => {
          saveModelBytes(file.name, bytes).catch(console.error);
        });
        addModel(file);
        window.dispatchEvent(
          new CustomEvent("model-file-added", { detail: { file } })
        );
      }
    },
    [project, createProject, addModel]
  );

  const handleEscape = useCallback(() => {
    if (saveAsDialogOpen) { setSaveAsDialogOpen(false); return; }
    if (openDialogOpen) { setOpenDialogOpen(false); return; }
    if (cloudDialogOpen) { setCloudDialogOpen(false); return; }
    if (backstageOpen) { setBackstageOpen(false); return; }
    if (settingsOpen) { setSettingsOpen(false); return; }
    if (feedbackOpen) { setFeedbackOpen(false); return; }
  }, [saveAsDialogOpen, openDialogOpen, cloudDialogOpen, backstageOpen, settingsOpen, feedbackOpen]);

  // --- Keyboard shortcuts ---
  useKeyboardShortcuts({
    onOpenIfc: handleUploadClick,
    onSettings: () => setSettingsOpen(true),
    onValidate: handleValidateClick,
    onExportBcf: handleExportBcf,
    onEscape: handleEscape,
    onSave: handleSave,
    onSaveAs: handleSaveAs,
    onOpen: handleOpen,
  });

  const hasLoadedModel = project?.models.some((m) => m.loadState === "loaded");
  const isValidating =
    validationPhase === "submitting" || validationPhase === "polling";

  return (
    <div className="app-shell" data-theme={theme}>
      <TitleBar
        onUploadClick={handleUploadClick}
        onSettingsClick={() => setSettingsOpen(true)}
        onFeedbackClick={() => setFeedbackOpen(true)}
        onHelpClick={() => window.open("https://github.com/3bm-bouwkunde/openaec-bim-validator", "_blank")}
      />

      <Ribbon
        onFileTabClick={() => { setBackstageInitialPanel(undefined); setBackstageOpen(true); }}
        onUploadIfc={handleUploadClick}
        onValidate={handleValidateClick}
        onExportBcf={handleExportBcf}
        onBcfLogin={handleBcfLogin}
        onBcfPush={handleBcfPush}
        onCloudSave={handleCloudSave}
        onCloudOpen={handleCloudOpen}
        onSave={handleSave}
        onSaveAs={handleSaveAs}
        onOpen={handleOpen}
        hasModel={hasLoadedModel}
        isValidating={isValidating}
        bcfConnected={bcfConnected}
        bcfHasQueuedIssues={bcfHasQueuedIssues}
        cloudEnabled={cloudEnabled}
        leftPanelVisible={!leftCollapsed}
        rightPanelVisible={!rightCollapsed}
        onToggleLeftPanel={toggleLeftPanel}
        onToggleRightPanel={toggleRightPanel}
        onZoomFit={() => window.dispatchEvent(new CustomEvent("zoom-fit-all"))}
        onResetView={() => {
          useStore.getState().selectElement(null);
          window.dispatchEvent(new CustomEvent("reset-view"));
        }}
        onAddSectionX={() => window.dispatchEvent(new CustomEvent("add-section-plane", { detail: { axis: "x" } }))}
        onAddSectionY={() => window.dispatchEvent(new CustomEvent("add-section-plane", { detail: { axis: "y" } }))}
        onAddSectionZ={() => window.dispatchEvent(new CustomEvent("add-section-plane", { detail: { axis: "z" } }))}
        onRemoveSections={() => window.dispatchEvent(new CustomEvent("remove-section-planes"))}
      />

      <div className="app-shell__panels">
        <Group orientation="horizontal" id="bim-panels" style={{ height: "100%" }}>
          {!leftCollapsed && (
            <>
              <Panel
                id="left"
                defaultSize={LEFT_PANEL_DEFAULT}
                minSize={LEFT_PANEL_MIN}
              >
                <LeftPanel />
              </Panel>
              <Separator className="resize-handle resize-handle--horizontal" />
            </>
          )}

          <Panel
            id="center"
            minSize={CENTER_PANEL_MIN}
          >
            <CenterPanel />
          </Panel>

          {!rightCollapsed && (
            <>
              <Separator className="resize-handle resize-handle--horizontal" />
              <Panel
                id="right"
                defaultSize={RIGHT_PANEL_DEFAULT}
                minSize={RIGHT_PANEL_MIN}
              >
                <RightPanel />
              </Panel>
            </>
          )}
        </Group>
      </div>

      <StatusBar />

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".ifc,.ifcx"
        multiple
        onChange={handleFileChange}
        style={{ display: "none" }}
        aria-label="Select IFC file(s)"
      />

      {/* Overlays */}
      <Backstage
        open={backstageOpen}
        initialPanel={backstageInitialPanel}
        onClose={() => { setBackstageOpen(false); setBackstageInitialPanel(undefined); }}
        onSave={handleSave}
        onSaveAsLocal={handleSaveAsLocal}
        onSaveAsCloud={handleSaveAsCloud}
        onOpenLocal={handleOpenLocal}
        onOpenCloud={handleOpenCloudDirect}
        onExportBcf={handleExportBcf}
        onCloudOpen={handleCloudOpen}
        onOpenSettings={() => setSettingsOpen(true)}
        onOpenFeedback={() => setFeedbackOpen(true)}
        cloudEnabled={cloudEnabled}
        hasModel={hasLoadedModel}
        projectStorage={projectStorage}
        onOpenProject={handleOpenProject}
      />

      <SettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        theme={theme}
        onThemeChange={setTheme}
      />

      <FeedbackDialog
        open={feedbackOpen}
        onClose={() => setFeedbackOpen(false)}
      />

      <CloudDialog
        open={cloudDialogOpen}
        onClose={() => setCloudDialogOpen(false)}
        mode={cloudDialogMode}
        bcfBlob={cloudBcfBlob}
        suggestedFilename={`${project?.name ?? "validation"}-${new Date().toISOString().slice(0, 10)}.bcf`}
        onFileOpened={handleCloudFileOpened}
      />

      <SaveAsDialog
        open={saveAsDialogOpen}
        onClose={() => { setSaveAsDialogOpen(false); setSaveAsDirectTarget(undefined); }}
        directTarget={saveAsDirectTarget}
        onSaveComplete={() => { setSaveAsDialogOpen(false); setSaveAsDirectTarget(undefined); }}
      />

      <OpenDialog
        open={openDialogOpen}
        onClose={() => { setOpenDialogOpen(false); setOpenDirectTarget(undefined); }}
        onFilesSelected={handleOpenFilesSelected}
        directTarget={openDirectTarget}
      />

      <ToastContainer />
    </div>
  );
}
