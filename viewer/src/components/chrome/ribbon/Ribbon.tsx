import { useState, useRef, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import RibbonTab from "./RibbonTab";
import HomeTab from "./HomeTab";
import ViewTab from "./ViewTab";
import "./Ribbon.css";

const TABS = ["home", "view"] as const;
type TabId = (typeof TABS)[number];

interface RibbonProps {
  onFileTabClick?: () => void;
  onUploadIfc?: () => void;
  onRemoveModel?: () => void;
  onValidate?: () => void;
  onResetValidation?: () => void;
  onExportBcf?: () => void;
  onSyncPlatform?: () => void;
  onBcfLogin?: () => void;
  onBcfPush?: () => void;
  onCloudSave?: () => void;
  onCloudOpen?: () => void;
  onZoomFit?: () => void;
  onResetCamera?: () => void;
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
  onValidate,
  onResetValidation,
  onExportBcf,
  onSyncPlatform,
  onBcfLogin,
  onBcfPush,
  onCloudSave,
  onCloudOpen,
  onZoomFit,
  onResetCamera,
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
  const { t, i18n } = useTranslation("ribbon");
  const [activeTab, setActiveTab] = useState<TabId>("home");
  const [prevTab, setPrevTab] = useState<TabId | null>(null);
  const [animating, setAnimating] = useState(false);
  const [direction, setDirection] = useState<"left" | "right">("right");
  const tabsRef = useRef<HTMLDivElement>(null);
  const borderRef = useRef<HTMLDivElement>(null);
  const gapRef = useRef<HTMLDivElement>(null);

  const updateHighlight = useCallback(() => {
    const tabsEl = tabsRef.current;
    const borderEl = borderRef.current;
    const gapEl = gapRef.current;
    if (!tabsEl || !borderEl || !gapEl) return;

    const activeEl = tabsEl.querySelector(".ribbon-tab.active") as HTMLElement | null;
    if (!activeEl) {
      borderEl.style.opacity = "0";
      gapEl.style.opacity = "0";
      return;
    }

    const tabsRect = tabsEl.getBoundingClientRect();
    const activeRect = activeEl.getBoundingClientRect();
    const left = activeRect.left - tabsRect.left;
    const top = activeRect.top - tabsRect.top;
    const width = activeRect.width;
    const height = activeRect.height;

    borderEl.style.opacity = "1";
    borderEl.style.left = `${left}px`;
    borderEl.style.top = `${top}px`;
    borderEl.style.width = `${width}px`;
    borderEl.style.height = `${height}px`;

    gapEl.style.opacity = "1";
    gapEl.style.left = `${left + 1}px`;
    gapEl.style.width = `${width - 2}px`;
  }, []);

  const switchTab = useCallback((newTab: TabId) => {
    if (newTab === activeTab) return;
    const oldIndex = TABS.indexOf(activeTab);
    const newIndex = TABS.indexOf(newTab);
    setDirection(newIndex > oldIndex ? "right" : "left");
    setPrevTab(activeTab);
    setActiveTab(newTab);
    setAnimating(true);
  }, [activeTab]);

  useEffect(() => {
    updateHighlight();
    requestAnimationFrame(updateHighlight);
  }, [activeTab, i18n.language, updateHighlight]);

  useEffect(() => {
    window.addEventListener("resize", updateHighlight);
    return () => window.removeEventListener("resize", updateHighlight);
  }, [updateHighlight]);

  useEffect(() => {
    if (!animating) return;
    const timer = setTimeout(() => {
      setAnimating(false);
      setPrevTab(null);
    }, 250);
    return () => clearTimeout(timer);
  }, [animating]);

  const renderContent = (tab: TabId) => {
    switch (tab) {
      case "home":
        return (
          <HomeTab
            onUploadIfc={onUploadIfc}
            onRemoveModel={onRemoveModel}
            onValidate={onValidate}
            onResetValidation={onResetValidation}
            onExportBcf={onExportBcf}
            onSyncPlatform={onSyncPlatform}
            onBcfLogin={onBcfLogin}
            onBcfPush={onBcfPush}
            onCloudSave={onCloudSave}
            onCloudOpen={onCloudOpen}
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
            onResetCamera={onResetCamera}
          />
        );
    }
  };

  return (
    <div className="ribbon-container">
      <div className="ribbon-tabs" ref={tabsRef}>
        <RibbonTab
          label={t("tabs.file")}
          isFileTab
          onClick={() => onFileTabClick?.()}
        />
        {TABS.map((tab) => (
          <RibbonTab
            key={tab}
            label={t(`tabs.${tab}`)}
            isActive={activeTab === tab}
            onClick={() => switchTab(tab)}
          />
        ))}
        <div className="ribbon-tab-border" ref={borderRef} />
        <div className="ribbon-tab-gap" ref={gapRef} />
      </div>

      <div className="ribbon-content-wrapper">
        {animating && prevTab && (
          <div
            className={`ribbon-content-panel ribbon-panel-exit-${direction}`}
            key={`prev-${prevTab}`}
          >
            {renderContent(prevTab)}
          </div>
        )}
        <div
          className={`ribbon-content-panel${animating ? ` ribbon-panel-enter-${direction}` : ""}`}
          key={`active-${activeTab}`}
        >
          {renderContent(activeTab)}
        </div>
      </div>
    </div>
  );
}
