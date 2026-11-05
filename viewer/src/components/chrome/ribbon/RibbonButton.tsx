import { Icon, Button as OaButton } from "@openaec/ui-react";
interface RibbonButtonProps {
  icon: string;
  label: string;
  title?: string;
  size?: "large" | "small" | "medium";
  active?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}

export default function RibbonButton({
  icon,
  label,
  title,
  size = "large",
  active,
  disabled,
  onClick,
}: RibbonButtonProps) {
  return (
    <OaButton
      kind="quiet"
      aria-pressed={active}
      className={`ribbon-btn${size === "small" ? " small" : ""}${size === "medium" ? " medium" : ""}${active ? " active" : ""}`}
      title={title || label}
      disabled={disabled}
      onClick={onClick}
    >
      <span className="ribbon-btn-icon"><Icon id={icon} size={size === "small" ? 16 : 24} /></span>
      <span className="ribbon-btn-label">{label}</span>
    </OaButton>
  );
}
