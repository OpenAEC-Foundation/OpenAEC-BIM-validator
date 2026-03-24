/**
 * BcfIssueQueue — displays the local BCF issue queue with management actions.
 */

import { useStore } from "../../store";
import type { BcfIssue } from "../../types/bcfIssue";

function statusLabel(state: BcfIssue["pushState"]): string {
  switch (state) {
    case "queued": return "";
    case "pushing": return "Bezig...";
    case "pushed": return "Gepusht";
    case "failed": return "Mislukt";
  }
}

function statusClass(state: BcfIssue["pushState"]): string {
  switch (state) {
    case "queued": return "";
    case "pushing": return "bcf-issue--pushing";
    case "pushed": return "bcf-issue--pushed";
    case "failed": return "bcf-issue--failed";
  }
}

export function BcfIssueQueue() {
  const issues = useStore((s) => s.bcfIssues);
  const removeIssue = useStore((s) => s.bcfRemoveIssue);
  const clearIssues = useStore((s) => s.bcfClearIssues);

  if (issues.length === 0) {
    return (
      <div className="bcf-queue bcf-queue--empty">
        <p className="bcf-queue__empty-text">
          Geen BCF issues. Maak ze aan vanuit de validatieresultaten via de
          <strong> +BCF</strong> knoppen of de <strong>Alle failures → BCF</strong> knop.
        </p>
      </div>
    );
  }

  const queuedCount = issues.filter((i) => i.pushState === "queued").length;

  return (
    <div className="bcf-queue">
      <div className="bcf-queue__header">
        <span className="bcf-queue__count">{issues.length} issue{issues.length !== 1 ? "s" : ""}</span>
        {queuedCount > 0 && (
          <button
            type="button"
            className="bcf-panel__btn bcf-panel__btn--danger bcf-panel__btn--sm"
            onClick={clearIssues}
          >
            Wis alles
          </button>
        )}
      </div>
      <div className="bcf-queue__list">
        {issues.map((issue) => (
          <div key={issue.id} className={`bcf-issue ${statusClass(issue.pushState)}`}>
            <div className="bcf-issue__info">
              <span className="bcf-issue__title" title={issue.title}>
                {issue.title}
              </span>
              <span className="bcf-issue__source">
                {issue.source.elementGlobalId
                  ? `Element`
                  : issue.source.requirementDescription
                    ? `Requirement`
                    : `Specificatie`}
              </span>
            </div>
            <div className="bcf-issue__actions">
              {issue.pushState !== "queued" && (
                <span className={`bcf-issue__status bcf-issue__status--${issue.pushState}`}>
                  {statusLabel(issue.pushState)}
                </span>
              )}
              {issue.pushState === "queued" && (
                <button
                  type="button"
                  className="bcf-issue__remove"
                  onClick={() => removeIssue(issue.id)}
                  title="Verwijder issue"
                  aria-label="Verwijder issue"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
