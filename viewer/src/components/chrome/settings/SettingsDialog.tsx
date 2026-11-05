import { Tabs, Button as OaButton } from "@openaec/ui-react";
import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { LANGUAGES, changeLanguage } from "../../../i18n/config";
import { getSetting, setSetting, applyTheme } from "../../../utils/settingsStore";
import Modal from "../Modal";
import ThemedSelect from "../ThemedSelect";
import "./SettingsDialog.css";
import { APP_VERSION } from "../../../version";

const THEME_OPTIONS = [
  { value: "light", labelKey: "appearance.light" },
  { value: "dark", labelKey: "appearance.dark" },
  { value: "blueprint", labelKey: "appearance.blueprint" },
  { value: "high-contrast-dark", labelKey: "appearance.contrastDark" },
  { value: "high-contrast-light", labelKey: "appearance.contrastLight" },
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
      <OaButton className="settings-btn settings-btn-secondary" onClick={handleReset}>
        {t("resetToDefaults")}
      </OaButton>
      <div className="settings-footer-right">
        <OaButton className="settings-btn settings-btn-secondary" onClick={handleCancel}>
          {tCommon("cancel")}
        </OaButton>
        <OaButton kind="primary" className="settings-btn" onClick={handleSave}>
          {tCommon("save")}
        </OaButton>
      </div>
    </>
  );

  return (
    <>
      <Modal open={open} onClose={handleCancel} title={t("title")} width={560} height={440} className="settings-dialog" footer={footer}>
        <div className="settings-body">
          <Tabs label={t("title")} tabs={TAB_IDS.map(id => ({ id, label: t(`tabs.${id}`) }))} active={activeTab} onSelect={setActiveTab} />

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
            <OaButton className="settings-btn settings-btn-secondary" onClick={() => setConfirmResetOpen(false)}>
              {tCommon("cancel")}
            </OaButton>
            <OaButton kind="primary" className="settings-btn" onClick={handleConfirmReset}>
              {t("resetToDefaults")}
            </OaButton>
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

        <ThemedSelect
          label={t("general.language")}
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
  return <ThemedSelect label={t("appearance.theme")} value={theme}
    options={THEME_OPTIONS.map(option => ({ value: option.value, label: t(option.labelKey) }))}
    onChange={onThemeSelect} />;
}

function AboutTabContent() {
  const { t } = useTranslation("settings");
  return (
    <div className="settings-section">
      <h3>{t("about.appName")}</h3>
      <div style={{ fontSize: 11, lineHeight: 1.8 }}>
        <p><strong>{t("about.version")}:</strong> {APP_VERSION}</p>
        <p><strong>{t("about.framework")}:</strong> React + TypeScript + That Open Engine</p>
        <p><strong>{t("about.license")}:</strong> MIT</p>
        <p style={{ marginTop: 8, color: "var(--oa-text-secondary)" }}>
          {t("about.description")}
        </p>
      </div>
    </div>
  );
}
