import { useEffect } from "react";

interface ShortcutHandlers {
  onOpenIfc?: () => void;
  onSettings?: () => void;
  onValidate?: () => void;
  onExportBcf?: () => void;
  onEscape?: () => void;
  onSave?: () => void;
  onSaveAs?: () => void;
  onOpen?: () => void;
}

export function useKeyboardShortcuts({
  onOpenIfc,
  onSettings,
  onValidate,
  onExportBcf,
  onEscape,
  onSave,
  onSaveAs,
  onOpen,
}: ShortcutHandlers): void {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Skip if user is typing in an input/textarea
      const tag = (e.target as HTMLElement).tagName;
      const isInput = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";

      if (e.key === "Escape") {
        onEscape?.();
        return;
      }

      if (isInput) return;

      // Ctrl+S → Save
      if (e.ctrlKey && !e.shiftKey && e.key === "s") {
        e.preventDefault();
        onSave?.();
        return;
      }

      // Ctrl+Shift+S → Save As
      if (e.ctrlKey && e.shiftKey && e.key === "S") {
        e.preventDefault();
        onSaveAs?.();
        return;
      }

      // Ctrl+O → Open
      if (e.ctrlKey && !e.shiftKey && e.key === "o") {
        e.preventDefault();
        onOpen?.();
        return;
      }

      // Ctrl+, → Settings
      if (e.ctrlKey && e.key === ",") {
        e.preventDefault();
        onSettings?.();
        return;
      }

      // Ctrl+Shift+V → Validate
      if (e.ctrlKey && e.shiftKey && e.key === "V") {
        e.preventDefault();
        onValidate?.();
        return;
      }

      // Ctrl+B → Export BCF
      if (e.ctrlKey && !e.shiftKey && e.key === "b") {
        e.preventDefault();
        onExportBcf?.();
        return;
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onOpenIfc, onSettings, onValidate, onExportBcf, onEscape, onSave, onSaveAs, onOpen]);
}
