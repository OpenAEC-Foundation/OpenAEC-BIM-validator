/**
 * AppShell — Chrome orchestration for the BIM Validator.
 *
 * Replaces the old Toolbar with OpenAEC Chrome design system:
 * TitleBar + Ribbon + Panels + StatusBar + Backstage + Dialogs.
 */

import { useState, useRef, useCallback, useEffect } from "react";
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

import { LeftPanel } from "./LeftPanel";
import { CenterPanel } from "./CenterPanel";
import { RightPanel } from "./RightPanel";
import { ToastContainer } from "../Toast";

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

  // --- Local chrome state ---
  const [backstageOpen, setBackstageOpen] = useState(false);
  const [backstageInitialPanel, setBackstageInitialPanel] = useState<string | undefined>();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [cloudDialogOpen, setCloudDialogOpen] = useState(false);
  const [cloudDialogMode, setCloudDialogMode] = useState<"save" | "open">("save");
  const [cloudBcfBlob, setCloudBcfBlob] = useState<Blob | undefined>();
  const [theme, setTheme] = useState(() => getSetting("theme", "light"));

  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleEscape = useCallback(() => {
    if (cloudDialogOpen) { setCloudDialogOpen(false); return; }
    if (backstageOpen) { setBackstageOpen(false); return; }
    if (settingsOpen) { setSettingsOpen(false); return; }
    if (feedbackOpen) { setFeedbackOpen(false); return; }
  }, [cloudDialogOpen, backstageOpen, settingsOpen, feedbackOpen]);

  // --- Keyboard shortcuts ---
  useKeyboardShortcuts({
    onOpenIfc: handleUploadClick,
    onSettings: () => setSettingsOpen(true),
    onValidate: handleValidateClick,
    onExportBcf: handleExportBcf,
    onEscape: handleEscape,
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
        hasModel={hasLoadedModel}
        isValidating={isValidating}
        bcfConnected={bcfConnected}
        bcfHasQueuedIssues={bcfHasQueuedIssues}
        cloudEnabled={cloudEnabled}
        leftPanelVisible={!leftCollapsed}
        rightPanelVisible={!rightCollapsed}
        onToggleLeftPanel={toggleLeftPanel}
        onToggleRightPanel={toggleRightPanel}
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
        onOpenLocal={handleUploadClick}
        onExportBcf={handleExportBcf}
        onCloudOpen={handleCloudOpen}
        onOpenSettings={() => setSettingsOpen(true)}
        onOpenFeedback={() => setFeedbackOpen(true)}
        cloudEnabled={cloudEnabled}
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

      <ToastContainer />
    </div>
  );
}
