import { useTranslation } from "react-i18next";
import RibbonGroup from "./RibbonGroup";
import RibbonButton from "./RibbonButton";
import RibbonButtonStack from "./RibbonButtonStack";
import {
  panelLeftIcon,
  panelRightIcon,
  zoomFitIcon,
  resetCameraIcon,
  resetViewIcon,
  sectionPlaneIcon,
  removeSectionIcon,
} from "./icons";

interface ViewTabProps {
  leftPanelVisible?: boolean;
  rightPanelVisible?: boolean;
  onToggleLeftPanel?: () => void;
  onToggleRightPanel?: () => void;
  onZoomFit?: () => void;
  onResetCamera?: () => void;
  onResetView?: () => void;
  onAddSectionX?: () => void;
  onAddSectionY?: () => void;
  onAddSectionZ?: () => void;
  onRemoveSections?: () => void;
}

export default function ViewTab({
  leftPanelVisible,
  rightPanelVisible,
  onToggleLeftPanel,
  onToggleRightPanel,
  onZoomFit,
  onResetCamera,
  onResetView,
  onAddSectionX,
  onAddSectionY,
  onAddSectionZ,
  onRemoveSections,
}: ViewTabProps) {
  const { t } = useTranslation("ribbon");

  return (
    <div className="ribbon-content">
      <div className="ribbon-groups">
        <RibbonGroup label={t("view.panels")}>
          <RibbonButtonStack>
            <RibbonButton
              icon={panelLeftIcon}
              label={t("view.models")}
              size="small"
              active={leftPanelVisible}
              onClick={onToggleLeftPanel}
            />
            <RibbonButton
              icon={panelRightIcon}
              label={t("view.validation")}
              size="small"
              active={rightPanelVisible}
              onClick={onToggleRightPanel}
            />
          </RibbonButtonStack>
        </RibbonGroup>

        <RibbonGroup label={t("view.viewer")}>
          <RibbonButton
            icon={zoomFitIcon}
            label={t("view.zoomFit")}
            onClick={onZoomFit}
          />
          <RibbonButtonStack>
            <RibbonButton
              icon={resetCameraIcon}
              label={t("view.resetCamera")}
              size="small"
              onClick={onResetCamera}
            />
            <RibbonButton
              icon={resetViewIcon}
              label={t("view.resetView")}
              size="small"
              onClick={onResetView}
            />
          </RibbonButtonStack>
        </RibbonGroup>

        <RibbonGroup label={t("view.sections")}>
          <RibbonButtonStack>
            <RibbonButton
              icon={sectionPlaneIcon}
              label={t("view.sectionX")}
              size="small"
              onClick={onAddSectionX}
            />
            <RibbonButton
              icon={sectionPlaneIcon}
              label={t("view.sectionY")}
              size="small"
              onClick={onAddSectionY}
            />
            <RibbonButton
              icon={sectionPlaneIcon}
              label={t("view.sectionZ")}
              size="small"
              onClick={onAddSectionZ}
            />
          </RibbonButtonStack>
          <RibbonButton
            icon={removeSectionIcon}
            label={t("view.removeSections")}
            onClick={onRemoveSections}
          />
        </RibbonGroup>
      </div>
    </div>
  );
}
