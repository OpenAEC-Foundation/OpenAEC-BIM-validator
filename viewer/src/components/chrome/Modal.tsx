import { Dialog, IconButton } from "@openaec/ui-react";
import type { CSSProperties, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import "./Modal.css";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  width?: number;
  height?: number | string;
  className?: string;
  children: ReactNode;
  footer?: ReactNode;
}

export default function Modal({ open, onClose, title, width = 480, height, className, children, footer }: ModalProps) {
  const { t } = useTranslation("common");
  const style = { "--bim-modal-width": `${width}px`, "--bim-modal-height": typeof height === "number" ? `${height}px` : height ?? "auto" } as CSSProperties;
  return <div className="bim-modal-host" style={style}>
    <Dialog open={open} title={title} onClose={onClose} actions={footer}>
      <div className="bim-modal-close"><IconButton icon="ui.close" label={t("close")} onClick={onClose} /></div>
      <div className={`modal-body ${className ?? ""}`}>{children}</div>
    </Dialog>
  </div>;
}
