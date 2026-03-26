/**
 * Client-side BCF issue — lives in the local queue before being
 * exported as ZIP or pushed to the BCF Platform.
 */

import type { TopicMapping } from "../lib/validationToBcf";

/** Push state for a queued BCF issue */
export type BcfIssuePushState = "queued" | "pushing" | "pushed" | "failed";

/** Source metadata: where did this issue originate from? */
export interface BcfIssueSource {
  specificationName: string;
  requirementDescription?: string;
  elementGlobalId?: string;
}

/** A queued BCF issue ready to be saved or pushed */
export interface BcfIssue {
  /** Client-generated UUID */
  id: string;
  /** ISO timestamp when this issue was created */
  createdAt: string;
  /** Short display title for the queue list */
  title: string;
  /** Which validation result generated this issue */
  source: BcfIssueSource;
  /** The BCF topic/viewpoint/comment data */
  mapping: TopicMapping;
  /** Current push state */
  pushState: BcfIssuePushState;
  /** Error message if pushState is 'failed' */
  pushError?: string;
  /** Remote topic GUID after successful push */
  remoteTopicGuid?: string;
  /** PNG data URL of captured viewpoint screenshot */
  screenshot?: string;
}

/** Helper to create a BcfIssue from a TopicMapping */
export function createBcfIssue(
  title: string,
  source: BcfIssueSource,
  mapping: TopicMapping,
): BcfIssue {
  return {
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    title,
    source,
    mapping,
    pushState: "queued",
  };
}
