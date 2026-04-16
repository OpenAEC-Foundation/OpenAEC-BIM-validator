import { useState, useEffect, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "../../../stores/authStore";
import { showToast } from "../../Toast";
import "./Backstage.css";

const ICONS = {
  new: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/><path d="M12 18v-6m-3 3h6"/></svg>',
  open: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>',
  save: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V7l-4-4z"/><path d="M17 3v4a1 1 0 01-1 1H8"/><path d="M7 14h10v7H7z"/></svg>',
  saveAs: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V7l-4-4z"/><path d="M17 3v4a1 1 0 01-1 1H8"/><path d="M12 12v6m-3-3h6"/></svg>',
  close: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9l6 6m0-6l-6 6"/></svg>',
  preferences: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>',
  about: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  exit: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
  server: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>',
  file: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/></svg>',
};

function MenuItem({
  icon,
  label,
  shortcut,
  active,
  onClick,
}: {
  icon: string;
  label: string;
  shortcut?: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`backstage-item${active ? " active" : ""}`}
      onClick={onClick}
    >
      <span
        className="backstage-item-icon"
        dangerouslySetInnerHTML={{ __html: icon }}
      />
      <span className="backstage-item-label">{label}</span>
      {shortcut && (
        <span className="backstage-item-shortcut">{shortcut}</span>
      )}
    </button>
  );
}

function SubMenuItem({
  icon,
  label,
  onClick,
  disabled,
}: {
  icon: string;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      className="backstage-item backstage-sub-item"
      onClick={onClick}
      disabled={disabled}
      style={{ opacity: disabled ? 0.4 : 1 }}
    >
      <span
        className="backstage-item-icon"
        style={{ width: 18, height: 18 }}
        dangerouslySetInnerHTML={{ __html: icon }}
      />
      <span className="backstage-item-label" style={{ fontSize: 12 }}>
        {label}
      </span>
    </button>
  );
}

function Divider() {
  return <div className="backstage-divider" />;
}

interface BackstageProps {
  open: boolean;
  onClose: () => void;
  onOpenSettings: () => void;
  onNavigate?: (path: string) => void;
}

export default function Backstage({
  open,
  onClose,
  onOpenSettings,
  onNavigate,
}: BackstageProps) {
  const { t } = useTranslation("backstage");
  const [activePanel, setActivePanel] = useState<string>("none");
  const [openExpanded, setOpenExpanded] = useState(false);
  const [saveAsExpanded, setSaveAsExpanded] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const user = useAuthStore((s) => s.user);
  const isLoggedIn = !!user;

  const actionAndClose = useCallback(
    (fn?: () => void) => {
      onClose();
      fn?.();
    },
    [onClose],
  );

  useEffect(() => {
    if (!open) {
      setActivePanel("none");
      setOpenExpanded(false);
      setSaveAsExpanded(false);
      return;
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  // --- File actions ---

  const handleNew = useCallback(() => {
    // TODO: Reset project state
    onClose();
    onNavigate?.("/");
    showToast(t("newProject"), "info");
  }, [onClose, onNavigate, t]);

  const handleOpenServer = useCallback(() => {
    onClose();
    onNavigate?.("/projects");
  }, [onClose, onNavigate]);

  const handleOpenLocal = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileSelected = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      try {
        // Check if it's a .wefc file
        const ext = file.name.toLowerCase().split('.').pop();
        if (ext !== 'wefc') {
          showToast(`${t("importError")}: Only .wefc files are supported`, "error");
          e.target.value = "";
          return;
        }

        // TODO: Parse .wefc envelope and load project
        // For now, just show success
        showToast(t("opened"), "success");
        onClose();
        onNavigate?.("/");
      } catch (err) {
        showToast(
          `${t("importError")}: ${err instanceof Error ? err.message : String(err)}`,
          "error",
        );
      }

      // Reset file input so the same file can be selected again
      e.target.value = "";
    },
    [onClose, onNavigate, t],
  );

  const handleSave = useCallback(async () => {
    if (isLoggedIn) {
      try {
        // TODO: Get current project data and save to cloud
        const projectData = { placeholder: "project data" };
        const response = await fetch("/api/cloud/projects/current-project/manifest", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(projectData),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        showToast(t("savedToServer"), "success");
        onClose();
      } catch (err) {
        showToast(
          `${t("saveError")}: ${err instanceof Error ? err.message : String(err)}`,
          "error",
        );
      }
    } else {
      // Not logged in — fallback to local export
      handleSaveAsLocal();
    }
  }, [isLoggedIn, onClose, t]);

  const handleSaveAsServer = useCallback(async () => {
    const name = window.prompt(
      t("projectNamePrompt"),
      "Nieuw project"
    );
    if (!name) return;

    try {
      // TODO: Get current project data and save as new cloud project
      const projectData = { placeholder: "project data" };
      const response = await fetch(`/api/cloud/projects/${encodeURIComponent(name)}/manifest`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(projectData),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      showToast(t("savedToServer"), "success");
      onClose();
    } catch (err) {
      showToast(
        `${t("saveError")}: ${err instanceof Error ? err.message : String(err)}`,
        "error",
      );
    }
  }, [onClose, t]);

  const handleSaveAsLocal = useCallback(() => {
    try {
      // TODO: Implement .wefc export
      const blob = new Blob(["placeholder wefc content"], { type: "application/zip" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "project.wefc";
      a.click();
      URL.revokeObjectURL(url);

      showToast(t("savedLocally"), "success");
      onClose();
    } catch (err) {
      showToast(
        `${t("saveError")}: ${err instanceof Error ? err.message : String(err)}`,
        "error",
      );
    }
  }, [onClose, t]);

  const handleClose = useCallback(() => {
    // TODO: Reset project state
    onClose();
    showToast(t("closed"), "info");
  }, [onClose, t]);

  if (!open) return null;

  const handleContentClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div className="backstage-overlay">
      <div className="backstage-sidebar">
        <button className="backstage-back" onClick={onClose}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          <span>{t("file")}</span>
        </button>
        <div className="backstage-items">
          {/* Nieuw */}
          <MenuItem
            icon={ICONS.new}
            label={t("new")}
            shortcut="Ctrl+N"
            onClick={handleNew}
          />

          {/* Openen */}
          <MenuItem
            icon={ICONS.open}
            label={t("open")}
            shortcut="Ctrl+O"
            onClick={() => setOpenExpanded((v) => !v)}
          />
          {openExpanded && (
            <>
              {isLoggedIn && (
                <SubMenuItem
                  icon={ICONS.server}
                  label={t("fromServer")}
                  onClick={handleOpenServer}
                />
              )}
              <SubMenuItem
                icon={ICONS.file}
                label={t("localFile")}
                onClick={handleOpenLocal}
              />
            </>
          )}

          {/* Opslaan */}
          <MenuItem
            icon={ICONS.save}
            label={t("save")}
            shortcut="Ctrl+S"
            onClick={handleSave}
          />

          {/* Opslaan als */}
          <MenuItem
            icon={ICONS.saveAs}
            label={t("saveAs")}
            shortcut="Ctrl+Shift+S"
            onClick={() => setSaveAsExpanded((v) => !v)}
          />
          {saveAsExpanded && (
            <>
              {isLoggedIn && (
                <SubMenuItem
                  icon={ICONS.server}
                  label={t("toServer")}
                  onClick={handleSaveAsServer}
                />
              )}
              <SubMenuItem
                icon={ICONS.file}
                label={t("localExport")}
                onClick={handleSaveAsLocal}
              />
            </>
          )}

          <Divider />

          {/* Sluiten */}
          <MenuItem
            icon={ICONS.close}
            label={t("close")}
            onClick={handleClose}
          />

          <Divider />

          {/* Voorkeuren */}
          <MenuItem
            icon={ICONS.preferences}
            label={t("preferences")}
            shortcut="Ctrl+,"
            onClick={() => actionAndClose(onOpenSettings)}
          />

          <Divider />

          {/* Over */}
          <MenuItem
            icon={ICONS.about}
            label={t("about")}
            active={activePanel === "about"}
            onClick={() => setActivePanel("about")}
          />

          <Divider />

          {/* Afsluiten */}
          <MenuItem
            icon={ICONS.exit}
            label={t("exit")}
            shortcut="Alt+F4"
            onClick={() => {
              onClose();
              // Web mode — no-op for exit
            }}
          />
        </div>
      </div>
      <div className="backstage-content" onClick={handleContentClick}>
        {activePanel === "about" && <AboutPanel />}
      </div>

      {/* Hidden file input for local open */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".wefc"
        onChange={handleFileSelected}
        style={{ display: "none" }}
      />
    </div>
  );
}

// ── About Panel ────────────────────────────────────────────

function AboutPanel() {
  const { t } = useTranslation("backstage");
  return (
    <div className="bs-about-panel">
      <h2 className="bs-about-title">{t("aboutPanel.title")}</h2>
      <div className="bs-about-app">
        <div className="bs-about-logo">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--theme-accent)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M3 21h18M5 21V7l8-4v18M19 21V11l-6-4" />
          </svg>
        </div>
        <div className="bs-about-app-info">
          <h1 className="bs-about-app-name">{t("aboutPanel.appName")}</h1>
          <p className="bs-about-version">{t("aboutPanel.version")} 0.1.0</p>
        </div>
      </div>
      <p className="bs-about-tagline">{t("aboutPanel.tagline")}</p>
      <p className="bs-about-description">{t("aboutPanel.description")}</p>
      <div className="bs-about-company">
        <h3 className="bs-about-company-name">{t("aboutPanel.companyName")}</h3>
        <p className="bs-about-company-desc">{t("aboutPanel.companyDescription")}</p>
      </div>
      <div className="bs-about-links">
        <a href="https://open-aec.com" className="bs-about-link" target="_blank" rel="noreferrer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10A15.3 15.3 0 0112 2z" />
          </svg>
          {t("aboutPanel.website")}
        </a>
        <a href="https://github.com/3bm-bouwkunde/openaec-bim-validator" className="bs-about-link" target="_blank" rel="noreferrer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 00-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0020 4.77 5.07 5.07 0 0019.91 1S18.73.65 16 2.48a13.38 13.38 0 00-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 005 4.77a5.44 5.44 0 00-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 009 18.13V22" />
          </svg>
          {t("aboutPanel.github")}
        </a>
      </div>
      <div className="bs-about-footer">
        <p className="bs-about-copyright">{t("aboutPanel.copyright")}</p>
      </div>
    </div>
  );
}
