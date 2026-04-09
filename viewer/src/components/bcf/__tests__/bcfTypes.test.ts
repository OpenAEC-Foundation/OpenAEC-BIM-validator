/**
 * Tests for BCF type helper functions.
 */

import { describe, it, expect } from "vitest";

import {
  severityToIssueType,
  severityToPriority,
  DEFAULT_STATUSES,
  DEFAULT_PRIORITIES,
  DEFAULT_TYPES,
} from "../../../types/bcf";

describe("severityToIssueType", () => {
  it("maps error to Error", () => {
    expect(severityToIssueType("error")).toBe("Error");
  });

  it("maps warning to Warning", () => {
    expect(severityToIssueType("warning")).toBe("Warning");
  });

  it("maps info to Info", () => {
    expect(severityToIssueType("info")).toBe("Info");
  });

  it("maps unknown severity to Error", () => {
    expect(severityToIssueType("unknown")).toBe("Error");
    expect(severityToIssueType("")).toBe("Error");
  });
});

describe("severityToPriority", () => {
  it("maps error to High", () => {
    expect(severityToPriority("error")).toBe("High");
  });

  it("maps warning to Normal", () => {
    expect(severityToPriority("warning")).toBe("Normal");
  });

  it("maps info to Low", () => {
    expect(severityToPriority("info")).toBe("Low");
  });

  it("maps unknown severity to Normal", () => {
    expect(severityToPriority("unknown")).toBe("Normal");
    expect(severityToPriority("")).toBe("Normal");
  });
});

describe("default constants", () => {
  it("has correct default statuses", () => {
    expect(DEFAULT_STATUSES).toEqual(["Open", "In Progress", "Closed"]);
  });

  it("has correct default priorities", () => {
    expect(DEFAULT_PRIORITIES).toEqual(["Critical", "High", "Normal", "Low"]);
  });

  it("has correct default types", () => {
    expect(DEFAULT_TYPES).toEqual([
      "Error",
      "Warning",
      "Info",
      "Clash",
      "Comment",
      "Request",
    ]);
  });
});
