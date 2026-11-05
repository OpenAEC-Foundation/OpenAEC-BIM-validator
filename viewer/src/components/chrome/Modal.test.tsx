import { beforeAll, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import Modal from "./Modal";
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () { this.open = true; };
  HTMLDialogElement.prototype.close = function () { this.open = false; };
});
describe("Blueprint modal integration", () => {
  it("exposes a named native dialog and lets Escape cancellation close only that dialog", () => {
    const onClose = vi.fn();
    const view = render(<Modal open title="Import" onClose={onClose}><p>Contents</p></Modal>);
    const dialog = screen.getByRole("dialog", { name: "Import" });
    expect(dialog.tagName).toBe("DIALOG");
    expect(dialog).toHaveAttribute("open");
    fireEvent(dialog, new Event("cancel", { cancelable: true }));
    expect(onClose).toHaveBeenCalledOnce();
    view.rerender(<Modal open={false} title="Import" onClose={onClose}><p>Contents</p></Modal>);
    expect(dialog).not.toHaveAttribute("open");
  });
});
