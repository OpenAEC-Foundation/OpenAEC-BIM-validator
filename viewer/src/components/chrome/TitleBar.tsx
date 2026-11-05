import { IconButton, Button as OaButton } from "@openaec/ui-react";
import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "../../stores/authStore";
import "./TitleBar.css";

interface TitleBarProps {
  onSettingsClick?: () => void;
  onFeedbackClick?: () => void;
  onHelpClick?: () => void;
  onUploadClick?: () => void;
}

export default function TitleBar({
  onSettingsClick,
  onFeedbackClick,
  onHelpClick,
  onUploadClick,
}: TitleBarProps) {
  const { t } = useTranslation();

  return (
    <div className="titlebar">
      <div className="titlebar-left">
        <div className="titlebar-icon">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--oa-accent)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M3 21h18M5 21V7l8-4v18M19 21V11l-6-4" />
          </svg>
        </div>

        <div className="titlebar-quick-access">
          <IconButton icon="file.open" label={t("open")} keys="Ctrl+O" onClick={onUploadClick} />
          <IconButton icon="ui.settings" label={t("preferences")} onClick={onSettingsClick} />
          <IconButton icon="ui.help" label="Help" keys="?" onClick={onHelpClick} />
        </div>
      </div>

      <span className="titlebar-title">
        {t("appName")}
      </span>

      <div className="titlebar-controls">
        <UserBadge />
        <OaButton
          kind="quiet" className="send-feedback-btn"
          onClick={onFeedbackClick}
        >
          {t("sendFeedback")}
        </OaButton>
      </div>
    </div>
  );
}

function UserBadge() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const login = useAuthStore((s) => s.login);
  const logout = useAuthStore((s) => s.logout);

  const [menuOpen, setMenuOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Check auth on mount
    useAuthStore.getState().checkAuth();
  }, []);

  useEffect(() => {
    if (!menuOpen) return;
    function close(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [menuOpen]);

  if (!user) {
    return (
      <OaButton
        kind="primary" className="titlebar-login-btn"
        onClick={() => login()}
      >
        {t("login")}
      </OaButton>
    );
  }

  const initial = (user.display_name || user.username).charAt(0).toUpperCase();

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <OaButton
        className="titlebar-avatar"
        onClick={() => setMenuOpen((v) => !v)}
        title={user.display_name || user.username}
      >
        {initial}
      </OaButton>
      {menuOpen && (
        <div className="titlebar-user-menu">
          <div className="titlebar-user-menu-name">
            {user.display_name || user.username}
          </div>
          <OaButton kind="quiet"
            className="titlebar-user-menu-item"
            onClick={() => {
              setMenuOpen(false);
              window.open("https://auth.open-aec.com/if/user/", "_blank");
            }}
          >
            SSO
          </OaButton>
          <OaButton kind="quiet"
            className="titlebar-user-menu-item"
            onClick={() => {
              setMenuOpen(false);
              logout();
            }}
          >
            {t("logout")}
          </OaButton>
        </div>
      )}
    </div>
  );
}
