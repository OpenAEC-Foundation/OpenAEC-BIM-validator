import { useTranslation } from "react-i18next";
import RibbonGroup from "./RibbonGroup";
import RibbonButton from "./RibbonButton";
import RibbonButtonStack from "./RibbonButtonStack";
import {
  uploadIcon,
  removeIcon,
  validateIcon,
  idsStandardIcon,
  resetIcon,
  bcfExportIcon,
  syncIcon,
  pushIcon,
  loginIcon,
  cloudSaveIcon,
  cloudOpenIcon,
} from "./icons";

interface HomeTabProps {
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
  hasModel?: boolean;
  isValidating?: boolean;
  bcfConnected?: boolean;
  bcfHasQueuedIssues?: boolean;
  cloudEnabled?: boolean;
}

export default function HomeTab({
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
  hasModel,
  isValidating,
  bcfConnected,
  bcfHasQueuedIssues,
  cloudEnabled,
}: HomeTabProps) {
  const { t } = useTranslation("ribbon");

  return (
    <div className="ribbon-content">
      <div className="ribbon-groups">
        <RibbonGroup label={t("home.models")}>
          <RibbonButton
            icon={uploadIcon}
            label={t("home.upload")}
            onClick={onUploadIfc}
          />
          <RibbonButtonStack>
            <RibbonButton
              icon={removeIcon}
              label={t("home.removeModel")}
              size="small"
              onClick={onRemoveModel}
              disabled={!hasModel}
            />
          </RibbonButtonStack>
        </RibbonGroup>

        <RibbonGroup label={t("home.validation")}>
          <RibbonButton
            icon={validateIcon}
            label={t("home.validate")}
            onClick={onValidate}
            disabled={!hasModel || isValidating}
          />
          <RibbonButtonStack>
            <RibbonButton
              icon={idsStandardIcon}
              label={t("home.idsSelect")}
              size="small"
            />
            <RibbonButton
              icon={resetIcon}
              label={t("home.reset")}
              size="small"
              onClick={onResetValidation}
            />
          </RibbonButtonStack>
        </RibbonGroup>

        <RibbonGroup label={t("home.bcf")}>
          <RibbonButton
            icon={bcfExportIcon}
            label={t("home.exportBcf")}
            onClick={onExportBcf}
          />
          <RibbonButtonStack>
            <RibbonButton
              icon={syncIcon}
              label={t("home.syncPlatform")}
              size="small"
              onClick={onSyncPlatform}
            />
            {bcfConnected ? (
              <RibbonButton
                icon={pushIcon}
                label={t("home.pushPlatform")}
                size="small"
                onClick={onBcfPush}
                disabled={!bcfHasQueuedIssues}
              />
            ) : (
              <RibbonButton
                icon={loginIcon}
                label={t("home.bcfLogin")}
                size="small"
                onClick={onBcfLogin}
              />
            )}
            {cloudEnabled && (
              <>
                <RibbonButton
                  icon={cloudSaveIcon}
                  label={t("home.cloudSave")}
                  size="small"
                  onClick={onCloudSave}
                />
                <RibbonButton
                  icon={cloudOpenIcon}
                  label={t("home.cloudOpen")}
                  size="small"
                  onClick={onCloudOpen}
                />
              </>
            )}
          </RibbonButtonStack>
        </RibbonGroup>
      </div>
    </div>
  );
}
