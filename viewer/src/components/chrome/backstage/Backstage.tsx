import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "../../../stores/authStore";
import { useStore } from "../../../store";
import type { IProjectStorage } from "../../../services/ProjectStorage";
import ProjectList from "../../projects/ProjectList";
import "./Backstage.css";

const ICONS = {
  projects: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18M5 21V7l8-4v18M19 21V11l-6-4"/></svg>',
  open: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>',
  exportBcf: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/><path d="M12 18v-6"/><path d="M9 15l3 3 3-3"/></svg>',
  preferences: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>',
  feedback: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>',
  about: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  account: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
  logout: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
  bcfPlatform: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
  cloud: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 10h-1.26A8 8 0 109 20h9a5 5 0 000-10z"/></svg>',
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

function Divider() {
  return <div className="backstage-divider" />;
}

interface BackstageProps {
  open: boolean;
  initialPanel?: string;
  onClose: () => void;
  onOpenLocal: () => void;
  onExportBcf: () => void;
  onCloudOpen?: () => void;
  onOpenSettings: () => void;
  onOpenFeedback: () => void;
  cloudEnabled?: boolean;
  projectStorage?: IProjectStorage;
  onOpenProject?: (projectId: string) => void;
}

export default function Backstage({
  open,
  initialPanel,
  onClose,
  onOpenLocal,
  onExportBcf,
  onCloudOpen,
  onOpenSettings,
  onOpenFeedback,
  cloudEnabled,
  projectStorage,
  onOpenProject,
}: BackstageProps) {
  const { t } = useTranslation("backstage");
  const [activePanel, setActivePanel] = useState<string>("none");
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
            icon={ICONS.open}
            label={t("open")}
            shortcut="Ctrl+O"
            onClick={() => actionAndClose(onOpenLocal)}
          />

          <MenuItem
            icon={ICONS.exportBcf}
            label={t("exportBcf")}
            shortcut="Ctrl+B"
            onClick={() => actionAndClose(onExportBcf)}
          />

          {cloudEnabled && (
            <MenuItem
              icon={ICONS.cloud}
              label={t("cloud")}
              onClick={() => actionAndClose(onCloudOpen)}
            />
          )}

          <Divider />

          <MenuItem
            icon={ICONS.bcfPlatform}
            label={t("bcfPlatform")}
            active={activePanel === "bcf-platform"}
            onClick={() => setActivePanel("bcf-platform")}
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
        {activePanel === "bcf-platform" && <BcfPlatformPanel />}
      </div>
    </div>
  );
}

// ── BCF Platform Panel ─────────────────────────────────────

function BcfPlatformPanel() {
  const { t } = useTranslation("backstage");
  const bcfAuth = useStore((s) => s.bcfAuth);
  const bcfPhase = useStore((s) => s.bcfPhase);
  const bcfPlatformUrl = useStore((s) => s.bcfPlatformUrl);
  const bcfProjects = useStore((s) => s.bcfProjects);
  const bcfSelectedProjectId = useStore((s) => s.bcfSelectedProjectId);
  const bcfError = useStore((s) => s.bcfError);
  const bcfOidcAvailable = useStore((s) => s.bcfOidcAvailable);
  const bcfSetPlatformUrl = useStore((s) => s.bcfSetPlatformUrl);
  const bcfLoginOidc = useStore((s) => s.bcfLoginOidc);
  const bcfConnectApiKey = useStore((s) => s.bcfConnectApiKey);
  const bcfLogout = useStore((s) => s.bcfLogout);
  const bcfRefreshProjects = useStore((s) => s.bcfRefreshProjects);
  const bcfSelectProject = useStore((s) => s.bcfSelectProject);
  const bcfCreateProject = useStore((s) => s.bcfCreateProject);

  const isAuthenticated = bcfAuth.method !== "none";
  const isConnecting = bcfPhase === "connecting";

  const [showApiKey, setShowApiKey] = useState(false);
  const [apiKeyUrl, setApiKeyUrl] = useState(bcfPlatformUrl || "");
  const [apiKey, setApiKey] = useState("");
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");
  const [creating, setCreating] = useState(false);

  const handleApiKeyConnect = (e: React.FormEvent) => {
    e.preventDefault();
    if (apiKeyUrl.trim() && apiKey.trim()) {
      void bcfConnectApiKey(apiKeyUrl.trim(), apiKey.trim());
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    setCreating(true);
    const project = await bcfCreateProject({
      name: newProjectName.trim(),
      description: newProjectDesc.trim() || undefined,
    });
    setCreating(false);
    if (project) {
      setNewProjectName("");
      setNewProjectDesc("");
      setShowCreateProject(false);
    }
  };

  return (
    <div className="bs-platform-panel">
      <h2 className="bs-platform-title">{t("bcfPlatformPanel.title")}</h2>
      <p className="bs-platform-desc">{t("bcfPlatformPanel.description")}</p>

      {/* Connection status */}
      {isAuthenticated && (
        <div className="bs-platform-status bs-platform-status--connected">
          <span className="bs-platform-status-dot" />
          {bcfAuth.user
            ? `${t("bcfPlatformPanel.loggedInAs")} ${bcfAuth.user.name}`
            : t("bcfPlatformPanel.connectedApiKey")}
        </div>
      )}

      {/* Not authenticated: login options */}
      {!isAuthenticated && (
        <div className="bs-platform-section">
          <div className="bs-platform-field">
            <label className="bs-platform-label">Platform URL</label>
            <input
              className="bs-platform-input"
              type="url"
              placeholder="https://bcf.openaec.com"
              value={apiKeyUrl}
              onChange={(e) => {
                setApiKeyUrl(e.target.value);
                bcfSetPlatformUrl(e.target.value);
              }}
              disabled={isConnecting}
            />
          </div>

          {bcfOidcAvailable && (
            <button
              className="bs-platform-btn bs-platform-btn--primary"
              onClick={() => void bcfLoginOidc()}
              disabled={isConnecting}
            >
              {t("bcfPlatformPanel.loginOidc")}
            </button>
          )}

          {!showApiKey ? (
            <button
              className="bs-platform-btn bs-platform-btn--secondary"
              onClick={() => setShowApiKey(true)}
            >
              {bcfOidcAvailable
                ? t("bcfPlatformPanel.orApiKey")
                : t("bcfPlatformPanel.connectApiKey")}
            </button>
          ) : (
            <form onSubmit={handleApiKeyConnect} className="bs-platform-section">
              <div className="bs-platform-field">
                <label className="bs-platform-label">API Key</label>
                <input
                  className="bs-platform-input"
                  type="password"
                  placeholder="bcfk_..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  disabled={isConnecting}
                />
              </div>
              <button
                type="submit"
                className="bs-platform-btn bs-platform-btn--primary"
                disabled={!apiKeyUrl.trim() || !apiKey.trim() || isConnecting}
              >
                {isConnecting ? t("bcfPlatformPanel.connecting") : t("bcfPlatformPanel.connect")}
              </button>
            </form>
          )}
        </div>
      )}

      {/* Authenticated: project selector */}
      {isAuthenticated && (
        <div className="bs-platform-section">
          <h3 className="bs-platform-subtitle">{t("bcfPlatformPanel.project")}</h3>
          <div className="bs-platform-row">
            <select
              className="bs-platform-select"
              value={bcfSelectedProjectId ?? ""}
              onChange={(e) => bcfSelectProject(e.target.value || null)}
            >
              <option value="">{t("bcfPlatformPanel.selectProject")}</option>
              {bcfProjects.map((p) => (
                <option key={p.project_id} value={p.project_id}>
                  {p.name}
                </option>
              ))}
            </select>
            <button
              className="bs-platform-btn bs-platform-btn--icon"
              onClick={() => void bcfRefreshProjects()}
              title={t("bcfPlatformPanel.refresh")}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="23 4 23 10 17 10" />
                <polyline points="1 20 1 14 7 14" />
                <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
              </svg>
            </button>
          </div>

          {/* Create project */}
          {!showCreateProject ? (
            <button
              className="bs-platform-btn bs-platform-btn--secondary"
              onClick={() => setShowCreateProject(true)}
            >
              + {t("bcfPlatformPanel.newProject")}
            </button>
          ) : (
            <form onSubmit={handleCreateProject} className="bs-platform-create-form">
              <div className="bs-platform-field">
                <label className="bs-platform-label">{t("bcfPlatformPanel.projectName")}</label>
                <input
                  className="bs-platform-input"
                  type="text"
                  placeholder="Mijn BIM project"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  disabled={creating}
                  autoFocus
                />
              </div>
              <div className="bs-platform-field">
                <label className="bs-platform-label">{t("bcfPlatformPanel.projectDesc")}</label>
                <input
                  className="bs-platform-input"
                  type="text"
                  placeholder="IDS validatie resultaten"
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  disabled={creating}
                />
              </div>
              <div className="bs-platform-row">
                <button
                  type="submit"
                  className="bs-platform-btn bs-platform-btn--primary"
                  disabled={!newProjectName.trim() || creating}
                >
                  {creating ? t("bcfPlatformPanel.creating") : t("bcfPlatformPanel.create")}
                </button>
                <button
                  type="button"
                  className="bs-platform-btn bs-platform-btn--secondary"
                  onClick={() => setShowCreateProject(false)}
                  disabled={creating}
                >
                  {t("bcfPlatformPanel.cancel")}
                </button>
              </div>
            </form>
          )}

          {/* Platform link */}
          {bcfSelectedProjectId && bcfPlatformUrl && (
            <a
              className="bs-platform-link"
              href={`${bcfPlatformUrl}/projects/${bcfSelectedProjectId}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {t("bcfPlatformPanel.openOnPlatform")} →
            </a>
          )}

          {/* Logout */}
          <button
            className="bs-platform-btn bs-platform-btn--danger"
            onClick={() => void bcfLogout()}
          >
            {bcfAuth.method === "oidc"
              ? t("bcfPlatformPanel.logout")
              : t("bcfPlatformPanel.disconnect")}
          </button>
        </div>
      )}

      {/* Error */}
      {bcfError && (
        <div className="bs-platform-status bs-platform-status--error">
          <span className="bs-platform-status-dot" />
          {bcfError}
        </div>
      )}
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
