import { Button as OaButton } from "@openaec/ui-react";
/**
 * FailedElements Component
 *
 * Table/list showing failed elements with their details.
 * - Displays GlobalId, element_type (IFC Class), element_name
 * - Shows failure messages for each element
 * - Handles elements with null GlobalId
 * - 'Show more' functionality when many elements
 */

import { useState, useCallback } from 'react';
import type { ElementResult } from '../types/validation';

/** Props for the FailedElements component */
export interface FailedElementsProps {
  /** Array of element results to display (can include both pass and fail) */
  elements: ElementResult[];
  /** Only show failed elements (default: true) */
  onlyFailed?: boolean;
  /** Maximum elements to show before "Show more" (default: 10) */
  initialVisibleCount?: number;
  /** Title for the section (default: "Failed Elements") */
  title?: string;
  /** Compact mode for embedding in other components */
  compact?: boolean;
}

/** Maximum elements to show by default */
const DEFAULT_VISIBLE_COUNT = 10;

/**
 * Format GlobalId for display
 */
function formatGlobalId(globalId: string | null): string {
  if (!globalId) {
    return 'N/A';
  }
  return globalId;
}

/**
 * Format element type (IFC Class) for display
 */
function formatElementType(elementType: string): string {
  if (!elementType) {
    return 'Unknown';
  }
  // Remove 'Ifc' prefix for cleaner display while keeping in title
  return elementType;
}

/**
 * Format element name for display
 */
function formatElementName(elementName: string | null): string {
  if (!elementName) {
    return '(unnamed)';
  }
  return elementName;
}

/**
 * SingleElementRow component for displaying a single failed element
 */
function SingleElementRow({
  element,
  compact,
}: {
  element: ElementResult;
  compact?: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const hasMessages = element.messages && element.messages.length > 0;
  const multipleMessages = element.messages && element.messages.length > 1;

  const toggleExpanded = useCallback(() => {
    if (hasMessages) {
      setIsExpanded(prev => !prev);
    }
  }, [hasMessages]);

  return (
    <div
      className={`failed-element-row ${isExpanded ? 'failed-element-row--expanded' : ''} ${compact ? 'failed-element-row--compact' : ''}`}
    >
      <OaButton
        type="button"
        className={`failed-element-main ${hasMessages ? 'failed-element-main--clickable' : ''}`}
        onClick={toggleExpanded}
        aria-expanded={hasMessages ? isExpanded : undefined}
        disabled={!hasMessages}
      >
        {/* Status indicator */}
        <span className="failed-element-status" aria-label="Failed">
          <span aria-hidden="true">✗</span>
        </span>

        {/* IFC Class */}
        <span className="failed-element-type" title={element.element_type}>
          {formatElementType(element.element_type)}
        </span>

        {/* Element Name */}
        <span className="failed-element-name" title={element.element_name || 'unnamed'}>
          {formatElementName(element.element_name)}
        </span>

        {/* GlobalId */}
        <span
          className="failed-element-global-id"
          title={element.global_id || 'No GlobalId'}
        >
          {formatGlobalId(element.global_id)}
        </span>

        {/* Message count indicator */}
        {hasMessages && (
          <span className="failed-element-message-count" aria-label={`${element.messages.length} message${element.messages.length !== 1 ? 's' : ''}`}>
            {multipleMessages ? (
              <>
                <span className="message-count-badge">{element.messages.length}</span>
                <span className="expand-indicator" aria-hidden="true">
                  {isExpanded ? '▼' : '▶'}
                </span>
              </>
            ) : (
              <span className="expand-indicator" aria-hidden="true">
                {isExpanded ? '▼' : '▶'}
              </span>
            )}
          </span>
        )}
      </OaButton>

      {/* Messages section */}
      {hasMessages && isExpanded && (
        <div className="failed-element-messages">
          <ul className="messages-list">
            {element.messages.map((message, idx) => (
              <li key={idx} className="message-item">
                {message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/**
 * FailedElements component displaying a list of failed elements
 */
export function FailedElements({
  elements,
  onlyFailed = true,
  initialVisibleCount = DEFAULT_VISIBLE_COUNT,
  title = 'Failed Elements',
  compact = false,
}: FailedElementsProps) {
  const [showAll, setShowAll] = useState(false);

  // Filter elements if onlyFailed is true
  const filteredElements = onlyFailed
    ? elements.filter(e => e.status === 'fail')
    : elements;

  // Calculate visible elements
  const visibleElements = showAll
    ? filteredElements
    : filteredElements.slice(0, initialVisibleCount);

  const remainingCount = filteredElements.length - visibleElements.length;
  const hasMore = remainingCount > 0;

  const handleShowMore = useCallback(() => {
    setShowAll(true);
  }, []);

  const handleShowLess = useCallback(() => {
    setShowAll(false);
  }, []);

  // Empty state
  if (filteredElements.length === 0) {
    return (
      <div className={`failed-elements failed-elements--empty ${compact ? 'failed-elements--compact' : ''}`}>
        <p className="empty-message">
          {onlyFailed ? 'No failed elements to display.' : 'No elements to display.'}
        </p>
        <style>{failedElementsStyles}</style>
      </div>
    );
  }

  return (
    <div
      className={`failed-elements ${compact ? 'failed-elements--compact' : ''}`}
      role="region"
      aria-label={title}
    >
      {/* Header */}
      {!compact && (
        <div className="failed-elements-header">
          <h3 className="failed-elements-title">{title}</h3>
          <span className="failed-elements-count" aria-label={`${filteredElements.length} elements`}>
            {filteredElements.length} element{filteredElements.length !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      {/* Table header for non-compact mode */}
      {!compact && (
        <div className="failed-elements-table-header" role="row" aria-hidden="true">
          <span className="table-header-cell table-header-status"></span>
          <span className="table-header-cell table-header-type">IFC Class</span>
          <span className="table-header-cell table-header-name">Name</span>
          <span className="table-header-cell table-header-global-id">GlobalId</span>
          <span className="table-header-cell table-header-messages"></span>
        </div>
      )}

      {/* Elements list */}
      <div className="failed-elements-list" role="list">
        {visibleElements.map((element, index) => (
          <SingleElementRow
            key={element.global_id || `element-${index}`}
            element={element}
            compact={compact}
          />
        ))}
      </div>

      {/* Show more/less buttons */}
      {hasMore && !showAll && (
        <OaButton
          type="button"
          className="show-more-btn"
          onClick={handleShowMore}
        >
          Show {remainingCount} more element{remainingCount !== 1 ? 's' : ''}...
        </OaButton>
      )}

      {showAll && filteredElements.length > initialVisibleCount && (
        <OaButton
          type="button"
          className="show-less-btn"
          onClick={handleShowLess}
        >
          Show less
        </OaButton>
      )}

      <style>{failedElementsStyles}</style>
    </div>
  );
}

/** Styles for the FailedElements component */
const failedElementsStyles = `
  .failed-elements {
    background-color: var(--oa-panel);
    border-radius: var(--oa-radius-medium);
    border: 1px solid var(--oa-border);
    overflow: hidden;
  }

  .failed-elements--empty {
    padding: var(--oa-space-2xl);
    text-align: center;
  }

  .failed-elements--compact {
    border: none;
    background-color: transparent;
  }

  .empty-message {
    color: var(--oa-text-secondary);
    font-size: var(--oa-size-body);
    margin: 0;
  }

  /* Header */
  .failed-elements-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--oa-space-lg);
    background-color: rgba(219, 76, 64, 0.1);
    border-bottom: 1px solid var(--oa-border);
  }

  .failed-elements-title {
    margin: 0;
    font-size: var(--oa-size-body);
    font-weight: 600;
    color: var(--oa-error);
  }

  .failed-elements-count {
    font-size: var(--oa-size-body);
    color: var(--oa-text-secondary);
    font-variant-numeric: tabular-nums;
  }

  /* Table header */
  .failed-elements-table-header {
    display: flex;
    align-items: center;
    padding: var(--oa-space-sm) var(--oa-space-lg);
    background-color: var(--oa-panel);
    border-bottom: 1px solid var(--oa-border);
    font-size: var(--oa-size-label);
    font-weight: 600;
    color: var(--oa-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .table-header-cell {
    flex-shrink: 0;
  }

  .table-header-status {
    width: 32px;
  }

  .table-header-type {
    width: 140px;
  }

  .table-header-name {
    flex: 1;
    min-width: 120px;
  }

  .table-header-global-id {
    width: 220px;
  }

  .table-header-messages {
    width: 48px;
  }

  /* Elements list */
  .failed-elements-list {
    display: flex;
    flex-direction: column;
  }

  /* Single element row */
  .failed-element-row {
    border-bottom: 1px solid var(--oa-border);
  }

  .failed-element-row:last-child {
    border-bottom: none;
  }

  .failed-element-row--expanded {
    background-color: rgba(219, 76, 64, 0.05);
  }

  .failed-element-main {
    display: flex;
    align-items: center;
    width: 100%;
    padding: var(--oa-space-sm) var(--oa-space-lg);
    background: none;
    border: none;
    font-family: inherit;
    font-size: var(--oa-size-body);
    text-align: left;
    color: var(--oa-text);
    cursor: default;
    transition: background-color var(--transition-fast);
  }

  .failed-element-main--clickable {
    cursor: pointer;
  }

  .failed-element-main--clickable:hover {
    background-color: var(--oa-hover);
  }

  .failed-element-main--clickable:focus-visible {
    outline: 2px solid var(--oa-accent);
    outline-offset: -2px;
  }

  .failed-element-main:disabled {
    cursor: default;
  }

  .failed-element-row--compact .failed-element-main {
    padding: var(--oa-space-xs) var(--oa-space-sm);
  }

  /* Status indicator */
  .failed-element-status {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    min-width: 24px;
    margin-right: var(--oa-space-sm);
    border-radius: var(--oa-radius-full);
    background-color: rgba(219, 76, 64, 0.2);
    color: var(--oa-error);
    font-size: var(--oa-size-label);
    font-weight: 700;
  }

  /* Element type (IFC Class) */
  .failed-element-type {
    width: 140px;
    min-width: 100px;
    font-weight: 500;
    color: var(--oa-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Element name */
  .failed-element-name {
    flex: 1;
    min-width: 80px;
    color: var(--oa-text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* GlobalId */
  .failed-element-global-id {
    width: 220px;
    min-width: 140px;
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, monospace;
    font-size: var(--oa-size-label);
    color: var(--oa-text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-align: left;
  }

  /* Message count indicator */
  .failed-element-message-count {
    display: flex;
    align-items: center;
    gap: var(--oa-space-xs);
    width: 48px;
    min-width: 48px;
    justify-content: flex-end;
    color: var(--oa-text-secondary);
    font-size: var(--oa-size-label);
  }

  .message-count-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 18px;
    height: 18px;
    padding: 0 var(--oa-space-xs);
    background-color: rgba(219, 76, 64, 0.2);
    color: var(--oa-error);
    border-radius: var(--oa-radius-full);
    font-size: var(--oa-size-label);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .expand-indicator {
    font-size: 10px;
    color: var(--oa-text-secondary);
    transition: transform var(--transition-fast);
  }

  /* Messages section */
  .failed-element-messages {
    padding: var(--oa-space-sm) var(--oa-space-lg);
    padding-left: calc(var(--oa-space-lg) + 32px);
    background-color: rgba(219, 76, 64, 0.05);
    border-top: 1px solid var(--oa-border);
  }

  .messages-list {
    margin: 0;
    padding: 0 0 0 var(--oa-space-lg);
    list-style-type: disc;
  }

  .message-item {
    font-size: var(--oa-size-label);
    color: var(--oa-error);
    line-height: 1.5;
    padding: var(--oa-space-xs) 0;
  }

  .message-item:first-child {
    padding-top: 0;
  }

  .message-item:last-child {
    padding-bottom: 0;
  }

  /* Show more/less buttons */
  .show-more-btn,
  .show-less-btn {
    display: block;
    width: 100%;
    padding: var(--oa-space-lg);
    background-color: var(--oa-panel);
    border: none;
    border-top: 1px dashed var(--oa-border);
    color: var(--oa-accent);
    font-family: inherit;
    font-size: var(--oa-size-body);
    font-weight: 500;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .show-more-btn:hover,
  .show-less-btn:hover {
    background-color: var(--oa-hover);
  }

  .show-more-btn:focus-visible,
  .show-less-btn:focus-visible {
    outline: 2px solid var(--oa-accent);
    outline-offset: -2px;
  }

  /* Responsive adjustments */
  @media (max-width: 768px) {
    .failed-elements-table-header {
      display: none;
    }

    .failed-element-main {
      flex-wrap: wrap;
      gap: var(--oa-space-xs);
    }

    .failed-element-status {
      order: 0;
    }

    .failed-element-type {
      order: 1;
      width: auto;
      min-width: unset;
      flex: 0 0 auto;
    }

    .failed-element-message-count {
      order: 2;
      width: auto;
      min-width: unset;
      margin-left: auto;
    }

    .failed-element-name {
      order: 3;
      flex: 0 0 100%;
      padding-left: calc(24px + var(--oa-space-sm));
      margin-top: var(--oa-space-xs);
    }

    .failed-element-global-id {
      order: 4;
      flex: 0 0 100%;
      width: auto;
      min-width: unset;
      padding-left: calc(24px + var(--oa-space-sm));
    }

    .failed-element-messages {
      padding-left: var(--oa-space-lg);
    }
  }

  @media (max-width: 480px) {
    .failed-elements-header {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--oa-space-xs);
    }

    .failed-element-main {
      padding: var(--oa-space-sm);
    }

    .failed-element-type {
      font-size: var(--oa-size-label);
    }

    .failed-element-global-id {
      font-size: 10px;
    }
  }

  /* Print styles */
  @media print {
    .failed-elements {
      border: 1px solid #ccc;
    }

    .show-more-btn,
    .show-less-btn {
      display: none;
    }

    .failed-element-messages {
      break-inside: avoid;
    }
  }

  /* High contrast mode */
  @media (prefers-contrast: high) {
    .failed-element-status {
      border: 2px solid currentColor;
    }

    .message-count-badge {
      border: 1px solid currentColor;
    }
  }

  /* Reduced motion */
  @media (prefers-reduced-motion: reduce) {
    .expand-indicator,
    .failed-element-main,
    .show-more-btn,
    .show-less-btn {
      transition: none;
    }
  }
`;

export default FailedElements;
