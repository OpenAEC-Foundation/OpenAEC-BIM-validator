import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ViewCube } from "./ViewCube";
import { ViewNavigation } from "./ViewNavigation";
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));

describe("orientation controls", () => {
  it("supports pointer and keyboard activation without exposing rear faces", () => {
    const onNavigate = vi.fn();
    render(<ViewCube cameraQuaternion={[0, 0, 0, 1]} onNavigate={onNavigate} />);
    const front = screen.getByRole("button", { name: "viewer.front" });
    fireEvent.click(front);
    fireEvent.keyDown(front, { key: "Enter" });
    fireEvent.keyDown(front, { key: " " });
    expect(onNavigate.mock.calls).toEqual([["front"], ["front"], ["front"]]);
    expect(screen.queryByRole("button", { name: "viewer.back" })).not.toBeInTheDocument();
  });

  it("offers hidden standard views and separate fit, home and projection actions", async () => {
    const engine = {
      getCameraQuaternion: () => [0, 0, 0, 1] as [number, number, number, number],
      getProjection: () => "Perspective" as const,
      setProjection: vi.fn(async () => {}), navigateToFace: vi.fn(async () => {}),
      resetView: vi.fn(async () => {}), fitToAllModels: vi.fn(),
    };
    const view = render(<ViewNavigation engine={engine} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "back" } });
    expect(engine.navigateToFace).toHaveBeenCalledWith("back");
    fireEvent.click(screen.getByRole("button", { name: "viewer.fit" }));
    fireEvent.click(screen.getByRole("button", { name: "viewer.home" }));
    fireEvent.click(screen.getByRole("button", { name: "viewer.toggleProjection" }));
    expect(engine.fitToAllModels).toHaveBeenCalledOnce();
    expect(engine.resetView).toHaveBeenCalledOnce();
    expect(engine.setProjection).toHaveBeenCalledWith("Orthographic");
    view.unmount();
  });
});
