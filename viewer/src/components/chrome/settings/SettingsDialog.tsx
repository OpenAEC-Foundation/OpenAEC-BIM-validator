import { useState, useEffect, useRef, type CSSProperties } from "react";
import { useTranslation } from "react-i18next";
import { LANGUAGES, changeLanguage } from "../../../i18n/config";
import { getSetting, setSetting, applyTheme } from "../../../utils/settingsStore";
import Modal from "../Modal";
import ThemedSelect from "../ThemedSelect";
import "../ThemedSelect.css";
import "./SettingsDialog.css";

const THEME_OPTIONS = [
  { value: "light", labelKey: "appearance.light", swatches: ["#FAFAF9", "#D97706", "#36363E", "#E7E5E4"] },
  { value: "forge", labelKey: "appearance.forge", swatches: ["#36363E", "#D97706", "#FAFAF9", "#44444C"] },
  { value: "openaec", labelKey: "appearance.dark", swatches: ["#27272A", "#D97706", "#FAFAF9", "#1C1917"] },
  { value: "blueprint", labelKey: "appearance.blueprint", swatches: ["#0F1B2D", "#60A5FA", "#F1F5F9", "#1E293B"] },
  { value: "contrast", labelKey: "appearance.contrast", swatches: ["#000000", "#FFD700", "#FFFFFF", "#333333"] },
];

const TAB_IDS = ["general", "appearance", "about"] as const;

interface SettingsDialogProps {
  open: boolean;
  onClose: () => void;
  theme: string;
  onThemeChange: (theme: string) => void;
}

export default function SettingsDialog({
  open,
  onClose,
  theme,
  onThemeChange,
}: SettingsDialogProps) {
  const { t } = useTranslation("settings");
  const { t: tCommon } = useTranslation("common");
  const [activeTab, setActiveTab] = useState("general");

  const [draftTheme, setDraftTheme] = useState(theme);
  const [draftLang, setDraftLang] = useState("auto");
  const [confirmResetOpen, setConfirmResetOpen] = useState(false);

  const originalTheme = useRef(theme);
  const originalLang = useRef("");

  useEffect(() => {
    if (open) {
      originalTheme.current = theme;
      setDraftTheme(theme);
      const lang = getSetting("language", "auto");
      originalLang.current = lang;
      setDraftLang(lang);
    }
  }, [open, theme]);

  const handleCancel = () => {
    setDraftTheme(originalTheme.current);
    setDraftLang(originalLang.current);
    onClose();
  };

  const handleSave = () => {
    onThemeChange(draftTheme);
    applyTheme(draftTheme);
    setSetting("theme", draftTheme);
    setSetting("language", draftLang);
    changeLanguage(draftLang);
    onClose();
  };

  const handleReset = () => {
    setConfirmResetOpen(true);
  };

  const handleConfirmReset = () => {
    setDraftTheme("light");
    setDraftLang("auto");
    setConfirmResetOpen(false);
  };

  const footer = (
    <>
      <button className="settings-btn settings-btn-secondary" onClick={handleReset}>
        {t("resetToDefaults")}
      </button>
      <div className="settings-footer-right">
        <button className="settings-btn settings-btn-secondary" onClick={handleCancel}>
          {tCommon("cancel")}
        </button>
        <button className="settings-btn settings-btn-primary" onClick={handleSave}>
          {tCommon("save")}
        </button>
      </div>
    </>
  );

  return (
    <>
      <Modal open={open} onClose={handleCancel} title={t("title")} width={560} height={440} className="settings-dialog" footer={footer}>
        <div className="settings-body">
          <div className="settings-sidebar">
            {TAB_IDS.map((id) => (
              <button
                key={id}
                className={`settings-tab${activeTab === id ? " active" : ""}`}
                onClick={() => setActiveTab(id)}
              >
                {t(`tabs.${id}`)}
              </button>
            ))}
          </div>

          <div className="settings-content">
            {activeTab === "general" && (
              <GeneralTabContent lang={draftLang} onLangChange={setDraftLang} />
            )}
            {activeTab === "appearance" && (
              <AppearanceTabContent theme={draftTheme} onThemeSelect={setDraftTheme} />
            )}
            {activeTab === "about" && <AboutTabContent />}
          </div>
        </div>
      </Modal>

      <Modal
        open={confirmResetOpen}
        onClose={() => setConfirmResetOpen(false)}
        title={t("resetToDefaults")}
        width={340}
        footer={
          <>
            <button className="settings-btn settings-btn-secondary" onClick={() => setConfirmResetOpen(false)}>
              {tCommon("cancel")}
            </button>
            <button className="settings-btn settings-btn-primary" onClick={handleConfirmReset}>
              {t("resetToDefaults")}
            </button>
          </>
        }
      >
        <div style={{ padding: 12, fontSize: 12 }}>{t("resetConfirm")}</div>
      </Modal>
    </>
  );
}

function GeneralTabContent({
  lang,
  onLangChange,
}: {
  lang: string;
  onLangChange: (value: string) => void;
}) {
  const { t } = useTranslation("settings");

  return (
    <div className="settings-section">
      <h3>{t("general.application")}</h3>
      <div className="settings-row">
        <span className="settings-label">{t("general.language")}</span>
        <ThemedSelect
          value={lang}
          options={LANGUAGES.map((l) => ({ value: l.code, label: l.name }))}
          onChange={onLangChange}
          style={{ width: 180 }}
        />
      </div>
    </div>
  );
}

function AppearanceTabContent({
  theme,
  onThemeSelect,
}: {
  theme: string;
  onThemeSelect: (value: string) => void;
}) {
  const { t } = useTranslation("settings");
  return (
    <div className="settings-section">
      <h3>{t("appearance.theme")}</h3>
      <ThemeDropdown theme={theme} onThemeSelect={onThemeSelect} />
    </div>
  );
}

function ThemeDropdown({
  theme,
  onThemeSelect,
}: {
  theme: string;
  onThemeSelect: (value: string) => void;
}) {
  const { t } = useTranslation("settings");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const selected = THEME_OPTIONS.find((o) => o.value === theme) ?? THEME_OPTIONS[0]!;

  const swatchRow = (swatches: string[]) => (
    <div className="theme-dropdown-swatches">
      {swatches.map((color, i) => (
        <span key={i} className="theme-dropdown-swatch" style={{ backgroundColor: color } as CSSProperties} />
      ))}
    </div>
  );

  return (
    <div className="theme-dropdown" ref={ref}>
      <button className="theme-dropdown-trigger" onClick={() => setOpen(!open)}>
        {swatchRow(selected.swatches)}
        <span className="theme-dropdown-label">{t(selected.labelKey)}</span>
        <svg className="theme-dropdown-chevron" width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M2.5 4L5 6.5L7.5 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div className="theme-dropdown-menu">
          {THEME_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={`theme-dropdown-item${theme === opt.value ? " active" : ""}`}
              onClick={() => { onThemeSelect(opt.value); setOpen(false); }}
            >
              {swatchRow(opt.swatches)}
              <span className="theme-dropdown-label">{t(opt.labelKey)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function AboutTabContent() {
  const { t } = useTranslation("settings");
  return (
    <div className="settings-section">
      <h3>{t("about.appName")}</h3>
      <div style={{ fontSize: 11, lineHeight: 1.8 }}>
        <p><strong>{t("about.version")}:</strong> 0.1.0</p>
        <p><strong>{t("about.framework")}:</strong> React + TypeScript + That Open Engine</p>
        <p><strong>{t("about.license")}:</strong> MIT</p>
        <p style={{ marginTop: 8, color: "var(--theme-dialog-content-secondary)" }}>
          {t("about.description")}
        </p>
      </div>
    </div>
  );
}
