import { useState } from "react";
import { Tabs, Button } from "@openaec/ui-react";
import { useTranslation } from "react-i18next";
import HomeTab from "./HomeTab";
import ViewTab from "./ViewTab";
import "./Ribbon.css";

const TABS = ["home", "view"] as const;
type TabId = (typeof TABS)[number];

interface RibbonProps {
  onFileTabClick?: () => void;
  onUploadIfc?: () => void;
  onRemoveModel?: () => void;
  onOptimize?: () => void;
  onValidate?: () => void;
  onResetValidation?: () => void;
  onExportBcf?: () => void;
  onSyncPlatform?: () => void;
  onBcfLogin?: () => void;
  onBcfPush?: () => void;
  onCloudSave?: () => void;
  onCloudOpen?: () => void;
  onSave?: () => void;
  onSaveAs?: () => void;
  onOpen?: () => void;
  onZoomFit?: () => void;
  onResetView?: () => void;
  onAddSectionX?: () => void;
  onAddSectionY?: () => void;
  onAddSectionZ?: () => void;
  onRemoveSections?: () => void;
  hasModel?: boolean;
  isValidating?: boolean;
  bcfConnected?: boolean;
  bcfHasQueuedIssues?: boolean;
  cloudEnabled?: boolean;
  leftPanelVisible?: boolean;
  rightPanelVisible?: boolean;
  onToggleLeftPanel?: () => void;
  onToggleRightPanel?: () => void;
}

export default function Ribbon({
  onFileTabClick,
  onUploadIfc,
  onRemoveModel,
  onOptimize,
  onValidate,
  onResetValidation,
  onExportBcf,
  onSyncPlatform,
  onBcfLogin,
  onBcfPush,
  onCloudSave,
  onCloudOpen,
  onSave,
  onSaveAs,
  onOpen,
  onZoomFit,
  onResetView,
  onAddSectionX,
  onAddSectionY,
  onAddSectionZ,
  onRemoveSections,
  hasModel,
  isValidating,
  bcfConnected,
  bcfHasQueuedIssues,
  cloudEnabled,
  leftPanelVisible,
  rightPanelVisible,
  onToggleLeftPanel,
  onToggleRightPanel,
}: RibbonProps) {
  const { t } = useTranslation("ribbon");
  const [activeTab, setActiveTab] = useState<TabId>("home");
  const renderContent = (tab: TabId) => {
    switch (tab) {
      case "home":
        return (
          <HomeTab
            onUploadIfc={onUploadIfc}
            onOptimize={onOptimize}
            onRemoveModel={onRemoveModel}
            onValidate={onValidate}
            onResetValidation={onResetValidation}
            onExportBcf={onExportBcf}
            onSyncPlatform={onSyncPlatform}
            onBcfLogin={onBcfLogin}
            onBcfPush={onBcfPush}
            onCloudSave={onCloudSave}
            onCloudOpen={onCloudOpen}
            onSave={onSave}
            onSaveAs={onSaveAs}
            onOpen={onOpen}
            hasModel={hasModel}
            isValidating={isValidating}
            bcfConnected={bcfConnected}
            bcfHasQueuedIssues={bcfHasQueuedIssues}
            cloudEnabled={cloudEnabled}
          />
        );
      case "view":
        return (
          <ViewTab
            leftPanelVisible={leftPanelVisible}
            rightPanelVisible={rightPanelVisible}
            onToggleLeftPanel={onToggleLeftPanel}
            onToggleRightPanel={onToggleRightPanel}
            onZoomFit={onZoomFit}
            onResetView={onResetView}
            onAddSectionX={onAddSectionX}
            onAddSectionY={onAddSectionY}
            onAddSectionZ={onAddSectionZ}
            onRemoveSections={onRemoveSections}
          />
        );
    }
  };

  return <div className="ribbon-container">
    <div className="ribbon-tabs">
      <Button kind="quiet" onClick={onFileTabClick}>{t("tabs.file")}</Button>
      <Tabs label={t("tabs.home")} tabs={TABS.map(id => ({ id, label: t(`tabs.${id}`) }))}
        active={activeTab} onSelect={id => setActiveTab(id as TabId)} />
    </div>
    <div className="ribbon-content-wrapper" role="tabpanel" aria-label={t(`tabs.${activeTab}`)}>
      <div className="ribbon-content-panel">{renderContent(activeTab)}</div>
    </div>
  </div>;
}
