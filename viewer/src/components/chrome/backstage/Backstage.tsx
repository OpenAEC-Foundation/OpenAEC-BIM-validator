import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "../../../stores/authStore";
import type { IProjectStorage } from "../../../services/ProjectStorage";
import ProjectList from "../../projects/ProjectList";
import "./Backstage.css";

const ICONS = {
  projects: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18M5 21V7l8-4v18M19 21V11l-6-4"/></svg>',
  save: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>',
  saveAs: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v6"/><polyline points="15 21 15 13 7 13 7 21"/><polyline points="7 3 7 8 13 8"/><path d="M19 16v6"/><path d="M16 19h6"/></svg>',
  open: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>',
  local: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
  exportBcf: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/><path d="M12 18v-6"/><path d="M9 15l3 3 3-3"/></svg>',
  preferences: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>',
  feedback: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>',
  about: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  account: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
  logout: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
  cloud: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 10h-1.26A8 8 0 109 20h9a5 5 0 000-10z"/></svg>',
};

function MenuItem({
  icon,
  label,
  shortcut,
  active,
  onClick,
  expanded,
  children,
}: {
  icon: string;
  label: string;
  shortcut?: string;
  active?: boolean;
  onClick: () => void;
  expanded?: boolean;
  children?: React.ReactNode;
}) {
  const hasChildren = !!children;
  return (
    <>
      <button
        className={`backstage-item${active ? " active" : ""}${hasChildren ? " has-submenu" : ""}${expanded ? " expanded" : ""}`}
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
        {hasChildren && (
          <span className="backstage-item-chevron">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points={expanded ? "6 9 12 15 18 9" : "9 6 15 12 9 18"} />
            </svg>
          </span>
        )}
      </button>
      {expanded && children && (
        <div className="backstage-submenu">{children}</div>
      )}
    </>
  );
}

function SubMenuItem({
  icon,
  label,
  onClick,
}: {
  icon: string;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className="backstage-subitem" onClick={onClick}>
      <span
        className="backstage-subitem-icon"
        dangerouslySetInnerHTML={{ __html: icon }}
      />
      <span className="backstage-subitem-label">{label}</span>
    </button>
  );
}

function Divider() {
  return <div className="backstage-divider" />;
}

interface BackstageProps {
  open: boolean;
  initialPanel?: string;
  onClose: () => void;
  onSave?: () => void;
  onSaveAsLocal?: () => void;
  onSaveAsCloud?: () => void;
  onOpenLocal: () => void;
  onOpenCloud?: () => void;
  onExportBcf: () => void;
  onCloudOpen?: () => void;
  onOpenSettings: () => void;
  onOpenFeedback: () => void;
  cloudEnabled?: boolean;
  hasModel?: boolean;
  projectStorage?: IProjectStorage;
  onOpenProject?: (projectId: string) => void;
}

export default function Backstage({
  open,
  initialPanel,
  onClose,
  onSave,
  onSaveAsLocal,
  onSaveAsCloud,
  onOpenLocal,
  onOpenCloud,
  onExportBcf,
  onCloudOpen,
  onOpenSettings,
  onOpenFeedback,
  cloudEnabled,
  hasModel,
  projectStorage,
  onOpenProject,
}: BackstageProps) {
  const { t } = useTranslation("backstage");
  const [activePanel, setActivePanel] = useState<string>("none");
  const [expandedMenu, setExpandedMenu] = useState<string | null>(null);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

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
      setExpandedMenu(null);
      return;
    }
    // Open to specific panel if requested
    if (initialPanel) {
      setActivePanel(initialPanel);
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose, initialPanel]);

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
          {projectStorage && (
            <MenuItem
              icon={ICONS.projects}
              label={t("projects", "Projecten")}
              active={activePanel === "projects"}
              onClick={() => setActivePanel("projects")}
            />
          )}

          <MenuItem
            icon={ICONS.save}
            label={t("save")}
            shortcut="Ctrl+S"
            onClick={() => actionAndClose(onSave)}
          />

          <MenuItem
            icon={ICONS.saveAs}
            label={t("saveAs")}
            shortcut="Ctrl+Shift+S"
            expanded={expandedMenu === "saveAs"}
            onClick={() =>
              setExpandedMenu(expandedMenu === "saveAs" ? null : "saveAs")
            }
          >
            <SubMenuItem
              icon={ICONS.local}
              label={t("local")}
              onClick={() => actionAndClose(onSaveAsLocal)}
            />
            {cloudEnabled && (
              <SubMenuItem
                icon={ICONS.cloud}
                label={t("cloudStorage")}
                onClick={() => actionAndClose(onSaveAsCloud)}
              />
            )}
          </MenuItem>

          <MenuItem
            icon={ICONS.open}
            label={t("open")}
            shortcut="Ctrl+O"
            expanded={expandedMenu === "open"}
            onClick={() =>
              setExpandedMenu(expandedMenu === "open" ? null : "open")
            }
          >
            <SubMenuItem
              icon={ICONS.local}
              label={t("local")}
              onClick={() => actionAndClose(onOpenLocal)}
            />
            {cloudEnabled && (
              <SubMenuItem
                icon={ICONS.cloud}
                label={t("cloudStorage")}
                onClick={() => actionAndClose(onOpenCloud)}
              />
            )}
          </MenuItem>

          <MenuItem
            icon={ICONS.exportBcf}
            label={t("exportBcf")}
            shortcut="Ctrl+B"
            onClick={() => actionAndClose(onExportBcf)}
          />

          <Divider />

          <MenuItem
            icon={ICONS.preferences}
            label={t("preferences")}
            shortcut="Ctrl+,"
            onClick={() => actionAndClose(onOpenSettings)}
          />

          <MenuItem
            icon={ICONS.feedback}
            label={t("feedback")}
            onClick={() => actionAndClose(onOpenFeedback)}
          />

          <Divider />

          <MenuItem
            icon={ICONS.about}
            label={t("about")}
            active={activePanel === "about"}
            onClick={() => setActivePanel("about")}
          />

          {user && (
            <>
              <Divider />
              <MenuItem
                icon={ICONS.account}
                label={user.display_name || user.username}
                onClick={() => {}}
              />
              <MenuItem
                icon={ICONS.logout}
                label={t("logout")}
                onClick={() => {
                  onClose();
                  logout();
                }}
              />
            </>
          )}
        </div>
      </div>
      <div className="backstage-content" onClick={handleContentClick}>
        {activePanel === "projects" && projectStorage && onOpenProject && (
          <ProjectList
            storage={projectStorage}
            onOpenProject={(id) => {
              onClose();
              onOpenProject(id);
            }}
          />
        )}
        {activePanel === "about" && <AboutPanel />}
      </div>
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
