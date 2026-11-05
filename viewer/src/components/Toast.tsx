/**
 * Toast — Simple notification component with auto-dismiss.
 *
 * Listens for "toast" custom events and displays notifications
 * with theme-token styling. Auto-dismisses after 3 seconds.
 */

import { Toast as BlueprintToast } from "@openaec/ui-react";
import { useState, useEffect, useCallback } from "react";

import "./Toast.css";

/** Toast notification data */
export interface ToastMessage {
  id: string;
  text: string;
  type?: "success" | "error" | "info";
}

/** Dispatch a toast notification from anywhere */
export function showToast(text: string, type: ToastMessage["type"] = "success"): void {
  window.dispatchEvent(
    new CustomEvent("toast", {
      detail: { id: crypto.randomUUID(), text, type },
    })
  );
}


export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    const handleToast = (e: Event) => {
      const detail = (e as CustomEvent<ToastMessage>).detail;
      setToasts((prev) => [...prev, detail]);


    };

    window.addEventListener("toast", handleToast);
    return () => window.removeEventListener("toast", handleToast);
  }, [removeToast]);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <BlueprintToast key={toast.id} tone={toast.type ?? "success"} title={toast.text} onClose={() => removeToast(toast.id)} />
      ))}
    </div>
  );
}
