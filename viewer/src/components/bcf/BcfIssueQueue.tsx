/**
 * BcfIssueQueue — displays the local BCF issue queue with thumbnails
 * and expandable detail panes.
 *
 * Collapsed: 48px row with 40x40 thumbnail, title, source badge, status.
 * Expanded: metadata table, larger thumbnail, description, remove button.
 */

import { useState } from "react";
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

function sourceLabel(issue: BcfIssue): string {
  if (issue.source.elementGlobalId) return "Element";
  if (issue.source.requirementDescription) return "Requirement";
  return "Specificatie";
}

/** Placeholder SVG for issues without screenshot */
function ThumbnailPlaceholder({ size }: { size: number }) {
  return (
    <div
      className="bcf-issue__thumb-placeholder"
      style={{ width: size, height: size }}
    >
      <svg
        width={size * 0.5}
        height={size * 0.5}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <circle cx="8.5" cy="8.5" r="1.5" />
        <polyline points="21 15 16 10 5 21" />
      </svg>
    </div>
  );
}

function IssueDetail({ issue }: { issue: BcfIssue }) {
  const removeIssue = useStore((s) => s.bcfRemoveIssue);
  const topic = issue.mapping.topic;
  const selectionCount = issue.mapping.viewpoint.components?.selection?.length ?? 0;

  const rows: Array<{ label: string; value: string }> = [
    { label: "Type", value: topic.topic_type ?? "IDS Validation" },
    { label: "Priority", value: topic.priority ?? "Normal" },
    { label: "Status", value: topic.topic_status ?? "Open" },
  ];

  if (topic.assigned_to) {
    rows.push({ label: "Assigned To", value: topic.assigned_to });
  }
  if (topic.labels?.length) {
    rows.push({ label: "Labels", value: topic.labels.join(", ") });
  }
  if (topic.stage) {
    rows.push({ label: "Stage", value: topic.stage });
  }
  if (topic.due_date) {
    rows.push({ label: "Deadline", value: topic.due_date });
  }
  if (selectionCount > 0) {
    rows.push({ label: "Elementen", value: String(selectionCount) });
  }

  return (
    <div className="bcf-issue__detail">
      <div className="bcf-issue__detail-top">
        {/* Larger thumbnail */}
        <div className="bcf-issue__detail-thumb-wrap">
          {issue.screenshot ? (
            <img
              className="bcf-issue__detail-thumb"
              src={issue.screenshot}
              alt="Viewpoint screenshot"
            />
          ) : (
            <ThumbnailPlaceholder size={120} />
          )}
        </div>

        {/* Metadata table */}
        <div className="bcf-issue__detail-meta">
          {rows.map((row) => (
            <div key={row.label} className="bcf-issue__detail-row">
              <span className="bcf-issue__detail-label">{row.label}</span>
              <span className="bcf-issue__detail-value">{row.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Description */}
      {topic.description && (
        <div className="bcf-issue__detail-desc">
          {topic.description}
        </div>
      )}

      {/* Source info */}
      <div className="bcf-issue__detail-source">
        <span className="bcf-issue__detail-label">Spec</span>
        <span className="bcf-issue__detail-value">
          {issue.source.specificationName}
        </span>
        {issue.source.requirementDescription && (
          <>
            <span className="bcf-issue__detail-label">Req</span>
            <span className="bcf-issue__detail-value">
              {issue.source.requirementDescription}
            </span>
          </>
        )}
        {issue.source.elementGlobalId && (
          <>
            <span className="bcf-issue__detail-label">Element</span>
            <span className="bcf-issue__detail-value bcf-issue__detail-value--mono">
              {issue.source.elementGlobalId}
            </span>
          </>
        )}
      </div>

      {/* Actions */}
      {issue.pushState === "queued" && (
        <button
          type="button"
          className="bcf-panel__btn bcf-panel__btn--danger bcf-panel__btn--sm"
          onClick={(e) => {
            e.stopPropagation();
            removeIssue(issue.id);
          }}
          style={{ alignSelf: "flex-start", marginTop: "var(--spacing-xs)" }}
        >
          Verwijder issue
        </button>
      )}
    </div>
  );
}

export function BcfIssueQueue() {
  const issues = useStore((s) => s.bcfIssues);
  const clearIssues = useStore((s) => s.bcfClearIssues);

  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

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
        <span className="bcf-queue__count">
          {issues.length} issue{issues.length !== 1 ? "s" : ""}
        </span>
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
        {issues.map((issue) => {
          const isExpanded = expandedId === issue.id;
          return (
            <div
              key={issue.id}
              className={`bcf-issue ${statusClass(issue.pushState)} ${isExpanded ? "bcf-issue--expanded" : ""}`}
            >
              {/* Collapsed row */}
              <div
                className="bcf-issue__row"
                onClick={() => toggleExpand(issue.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleExpand(issue.id);
                  }
                }}
              >
                {/* Thumbnail */}
                <div className="bcf-issue__thumb-wrap">
                  {issue.screenshot ? (
                    <img
                      className="bcf-issue__thumb"
                      src={issue.screenshot}
                      alt=""
                    />
                  ) : (
                    <ThumbnailPlaceholder size={40} />
                  )}
                </div>

                {/* Title + source */}
                <div className="bcf-issue__info">
                  <span className="bcf-issue__title" title={issue.title}>
                    {issue.title}
                  </span>
                  <span className="bcf-issue__source">
                    {sourceLabel(issue)}
                  </span>
                </div>

                {/* Status + expand indicator */}
                <div className="bcf-issue__actions">
                  {issue.pushState !== "queued" && (
                    <span className={`bcf-issue__status bcf-issue__status--${issue.pushState}`}>
                      {statusLabel(issue.pushState)}
                    </span>
                  )}
                  <span className={`bcf-issue__chevron ${isExpanded ? "bcf-issue__chevron--open" : ""}`}>
                    <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M4.646 5.646a.5.5 0 01.708 0L8 8.293l2.646-2.647a.5.5 0 01.708.708l-3 3a.5.5 0 01-.708 0l-3-3a.5.5 0 010-.708z" />
                    </svg>
                  </span>
                </div>
              </div>

              {/* Expandable detail */}
              {isExpanded && <IssueDetail issue={issue} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
