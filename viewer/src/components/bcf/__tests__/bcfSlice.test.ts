/**
 * Tests for bcfSlice — BCF issue CRUD, filtering, sorting, stats.
 */

import { describe, it, expect, beforeEach } from "vitest";

import { useStore } from "../../../store";
import type { BcfIssue, BcfComment, BcfViewpoint } from "../../../types/bcf";

/** Create a minimal test viewpoint */
function createTestViewpoint(guid?: string): BcfViewpoint {
  return {
    guid: guid ?? crypto.randomUUID(),
    camera: {
      position: { x: 0, y: 0, z: 10 },
      direction: { x: 0, y: 0, z: -1 },
      up: { x: 0, y: 1, z: 0 },
      type: "perspective",
      fieldOfView: 60,
    },
    screenshotDataUrl: "",
    components: {
      selection: [],
      visibility: { defaultVisibility: true, exceptions: [] },
      coloring: [],
    },
  };
}

/** Create a minimal test issue */
function createTestIssue(overrides: Partial<BcfIssue> = {}): BcfIssue {
  const now = new Date().toISOString();
  return {
    guid: crypto.randomUUID(),
    title: "Test Issue",
    description: "Test description",
    type: "Error",
    status: "Open",
    priority: "Normal",
    assignedTo: "",
    creationDate: now,
    modifiedDate: now,
    creationAuthor: "Test",
    labels: [],
    viewpoint: createTestViewpoint(),
    comments: [],
    failedGlobalIds: [],
    index: 0,
    ...overrides,
  };
}

describe("bcfSlice", () => {
  beforeEach(() => {
    // Reset store state fully
    useStore.setState({
      bcfIssues: [],
      activeBcfIssueId: null,
      bcfFilter: "all",
      bcfSortBy: "date",
      bcfSortDirection: "desc",
    });
  });

  describe("CRUD", () => {
    it("adds an issue", () => {
      const issue = createTestIssue();
      useStore.getState().addBcfIssue(issue);

      expect(useStore.getState().bcfIssues).toHaveLength(1);
      expect(useStore.getState().bcfIssues[0]?.guid).toBe(issue.guid);
    });

    it("updates an issue", () => {
      const issue = createTestIssue();
      // Set a past date so modifiedDate will differ after update
      issue.modifiedDate = "2026-01-01T00:00:00.000Z";
      useStore.getState().addBcfIssue(issue);

      useStore.getState().updateBcfIssue(issue.guid, { status: "Closed" });

      const updated = useStore.getState().bcfIssues[0];
      expect(updated?.status).toBe("Closed");
      expect(updated?.modifiedDate).not.toBe("2026-01-01T00:00:00.000Z");
    });

    it("deletes an issue", () => {
      const issue = createTestIssue();
      useStore.getState().addBcfIssue(issue);
      useStore.getState().deleteBcfIssue(issue.guid);

      expect(useStore.getState().bcfIssues).toHaveLength(0);
    });

    it("clears active issue when deleting it", () => {
      const issue = createTestIssue();
      useStore.getState().addBcfIssue(issue);
      useStore.getState().setActiveBcfIssue(issue.guid);

      useStore.getState().deleteBcfIssue(issue.guid);
      expect(useStore.getState().activeBcfIssueId).toBeNull();
    });

    it("keeps active issue when deleting a different one", () => {
      const issue1 = createTestIssue();
      const issue2 = createTestIssue({ title: "Other" });
      useStore.getState().addBcfIssue(issue1);
      useStore.getState().addBcfIssue(issue2);
      useStore.getState().setActiveBcfIssue(issue1.guid);

      useStore.getState().deleteBcfIssue(issue2.guid);
      expect(useStore.getState().activeBcfIssueId).toBe(issue1.guid);
    });

    it("adds a comment to an issue", () => {
      const issue = createTestIssue();
      useStore.getState().addBcfIssue(issue);

      const comment: BcfComment = {
        guid: crypto.randomUUID(),
        author: "Tester",
        date: new Date().toISOString(),
        comment: "Test comment",
      };

      useStore.getState().addBcfComment(issue.guid, comment);

      const updated = useStore.getState().bcfIssues[0];
      expect(updated?.comments).toHaveLength(1);
      expect(updated?.comments[0]?.comment).toBe("Test comment");
    });

    it("clears all issues", () => {
      useStore.getState().addBcfIssue(createTestIssue());
      useStore.getState().addBcfIssue(createTestIssue());
      useStore.getState().setActiveBcfIssue(
        useStore.getState().bcfIssues[0]?.guid ?? null
      );

      useStore.getState().clearAllBcfIssues();

      expect(useStore.getState().bcfIssues).toHaveLength(0);
      expect(useStore.getState().activeBcfIssueId).toBeNull();
    });
  });

  describe("filtering", () => {
    it("returns all issues when filter is 'all'", () => {
      useStore.getState().addBcfIssue(createTestIssue({ status: "Open" }));
      useStore.getState().addBcfIssue(createTestIssue({ status: "Closed" }));
      useStore.setState({ bcfFilter: "all" });

      const filtered = useStore.getState().getFilteredBcfIssues();
      expect(filtered).toHaveLength(2);
    });

    it("filters by status", () => {
      useStore.getState().addBcfIssue(createTestIssue({ status: "Open" }));
      useStore.getState().addBcfIssue(createTestIssue({ status: "Closed" }));
      useStore.getState().addBcfIssue(createTestIssue({ status: "Open" }));
      useStore.setState({ bcfFilter: "Open" });

      const filtered = useStore.getState().getFilteredBcfIssues();
      expect(filtered).toHaveLength(2);
      expect(filtered.every((i) => i.status === "Open")).toBe(true);
    });
  });

  describe("sorting", () => {
    it("sorts by priority", () => {
      useStore.getState().addBcfIssue(createTestIssue({ priority: "Low" }));
      useStore.getState().addBcfIssue(createTestIssue({ priority: "Critical" }));
      useStore.getState().addBcfIssue(createTestIssue({ priority: "High" }));
      useStore.setState({ bcfSortBy: "priority", bcfSortDirection: "asc" });

      const sorted = useStore.getState().getFilteredBcfIssues();
      expect(sorted[0]?.priority).toBe("Critical");
      expect(sorted[1]?.priority).toBe("High");
      expect(sorted[2]?.priority).toBe("Low");
    });

    it("sorts by status ascending", () => {
      useStore.getState().addBcfIssue(createTestIssue({ status: "Closed" }));
      useStore.getState().addBcfIssue(createTestIssue({ status: "Open" }));
      useStore.getState().addBcfIssue(createTestIssue({ status: "In Progress" }));
      useStore.getState().setBcfSortBy("status");
      useStore.setState({ bcfSortDirection: "asc" });

      const sorted = useStore.getState().getFilteredBcfIssues();
      expect(sorted[0]?.status).toBe("Open");
      expect(sorted[1]?.status).toBe("In Progress");
      expect(sorted[2]?.status).toBe("Closed");
    });

    it("toggles sort direction", () => {
      useStore.setState({ bcfSortDirection: "asc" });
      useStore.getState().toggleBcfSortDirection();
      expect(useStore.getState().bcfSortDirection).toBe("desc");

      useStore.getState().toggleBcfSortDirection();
      expect(useStore.getState().bcfSortDirection).toBe("asc");
    });
  });

  describe("stats", () => {
    it("returns correct stats", () => {
      useStore.getState().addBcfIssue(createTestIssue({ status: "Open" }));
      useStore.getState().addBcfIssue(createTestIssue({ status: "Open" }));
      useStore
        .getState()
        .addBcfIssue(createTestIssue({ status: "In Progress" }));
      useStore.getState().addBcfIssue(createTestIssue({ status: "Closed" }));

      const stats = useStore.getState().getBcfStats();
      expect(stats.open).toBe(2);
      expect(stats.inProgress).toBe(1);
      expect(stats.closed).toBe(1);
      expect(stats.total).toBe(4);
    });

    it("returns zero stats when empty", () => {
      const stats = useStore.getState().getBcfStats();
      expect(stats.open).toBe(0);
      expect(stats.inProgress).toBe(0);
      expect(stats.closed).toBe(0);
      expect(stats.total).toBe(0);
    });
  });
});
