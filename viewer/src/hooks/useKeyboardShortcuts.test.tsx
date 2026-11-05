import { fireEvent, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useKeyboardShortcuts } from "./useKeyboardShortcuts";
describe("shortcuts with native dialogs", () => {
  it("leaves Escape and application shortcuts to the open modal", () => {
    const onEscape = vi.fn(), onSave = vi.fn();
    const view = renderHook(() => useKeyboardShortcuts({ onEscape, onSave }));
    const dialog = document.createElement("dialog"); dialog.open = true;
    const button = document.createElement("button"); dialog.append(button); document.body.append(dialog);
    fireEvent.keyDown(button, { key: "Escape" });
    fireEvent.keyDown(button, { key: "s", ctrlKey: true });
    expect(onEscape).not.toHaveBeenCalled(); expect(onSave).not.toHaveBeenCalled();
    dialog.remove();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onEscape).toHaveBeenCalledOnce();
    view.unmount();
  });
});
