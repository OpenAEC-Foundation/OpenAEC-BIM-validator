/** Tests for the current BCF queue used by the viewer and platform export. */
import { beforeEach, describe, expect, it } from "vitest";
import { useStore } from "../../../store";
import { createBcfIssue } from "../../../types/bcfIssue";

function issue(title = "Missing property") {
  return createBcfIssue(title, { specificationName: "Wall properties" }, {
    topic: { title, description: "Required property is absent", topic_status: "Open" },
    viewpoint: { components: { selection: [{ ifc_guid: "wall-1" }] } },
    comment: { comment: "Check the source model" },
  });
}

describe("BCF issue queue", () => {
  beforeEach(() => useStore.getState().bcfClearIssues());
  it("adds an issue with its viewpoint and topic", () => {
    const value = issue();
    useStore.getState().bcfAddIssue(value);
    expect(useStore.getState().bcfIssues).toEqual([value]);
  });
  it("adds multiple issues without discarding existing ones", () => {
    const first = issue();
    const rest = [issue("Second"), issue("Third")];
    useStore.getState().bcfAddIssue(first);
    useStore.getState().bcfAddIssues(rest);
    expect(useStore.getState().bcfIssues).toEqual([first, ...rest]);
  });
  it("imports unique topic IDs without overwriting an existing local issue", () => {
    const first = issue(); const second = issue("Second");
    useStore.getState().bcfAddIssue(first);
    const added = useStore.getState().bcfImportIssues([{ ...first, title: "Remote overwrite" }, second, second]);
    expect(added).toBe(1);
    expect(useStore.getState().bcfIssues).toEqual([first, second]);
  });
  it("updates only the identified issue and preserves the viewpoint", () => {
    const first = issue();
    const second = issue("Other");
    useStore.getState().bcfAddIssues([first, second]);
    useStore.getState().bcfUpdateIssue(first.id, { pushState: "pushed", remoteTopicGuid: "remote-1" });
    expect(useStore.getState().bcfIssues).toEqual([
      { ...first, pushState: "pushed", remoteTopicGuid: "remote-1" }, second,
    ]);
  });
  it("removes only the identified issue", () => {
    const first = issue();
    const second = issue("Other");
    useStore.getState().bcfAddIssues([first, second]);
    useStore.getState().bcfRemoveIssue(first.id);
    expect(useStore.getState().bcfIssues).toEqual([second]);
  });
  it("ignores updates and removals for unknown IDs", () => {
    const value = issue();
    useStore.getState().bcfAddIssue(value);
    useStore.getState().bcfUpdateIssue("unknown", { title: "Changed" });
    useStore.getState().bcfRemoveIssue("unknown");
    expect(useStore.getState().bcfIssues).toEqual([value]);
  });
  it("clears the queue", () => {
    useStore.getState().bcfAddIssues([issue(), issue("Other")]);
    useStore.getState().bcfClearIssues();
    expect(useStore.getState().bcfIssues).toEqual([]);
  });
});
