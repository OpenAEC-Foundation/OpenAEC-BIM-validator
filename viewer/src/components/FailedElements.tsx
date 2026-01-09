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
      <button
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
      </button>

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
        <button
          type="button"
          className="show-more-btn"
          onClick={handleShowMore}
        >
          Show {remainingCount} more element{remainingCount !== 1 ? 's' : ''}...
        </button>
      )}

      {showAll && filteredElements.length > initialVisibleCount && (
        <button
          type="button"
          className="show-less-btn"
          onClick={handleShowLess}
        >
          Show less
        </button>
      )}

      <style>{failedElementsStyles}</style>
    </div>
  );
}

/** Styles for the FailedElements component */
const failedElementsStyles = `
  .failed-elements {
    background-color: var(--color-surface);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
    overflow: hidden;
  }

  .failed-elements--empty {
    padding: var(--spacing-xl);
    text-align: center;
  }

  .failed-elements--compact {
    border: none;
    background-color: transparent;
  }

  .empty-message {
    color: var(--color-text-secondary);
    font-size: var(--font-size-sm);
    margin: 0;
  }

  /* Header */
  .failed-elements-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md);
    background-color: rgba(219, 76, 64, 0.1);
    border-bottom: 1px solid var(--color-border);
  }

  .failed-elements-title {
    margin: 0;
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--color-error);
  }

  .failed-elements-count {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    font-variant-numeric: tabular-nums;
  }

  /* Table header */
  .failed-elements-table-header {
    display: flex;
    align-items: center;
    padding: var(--spacing-sm) var(--spacing-md);
    background-color: var(--color-background);
    border-bottom: 1px solid var(--color-border);
    font-size: var(--font-size-xs);
    font-weight: 600;
    color: var(--color-text-secondary);
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
    border-bottom: 1px solid var(--color-border);
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
    padding: var(--spacing-sm) var(--spacing-md);
    background: none;
    border: none;
    font-family: inherit;
    font-size: var(--font-size-sm);
    text-align: left;
    color: var(--color-text);
    cursor: default;
    transition: background-color var(--transition-fast);
  }

  .failed-element-main--clickable {
    cursor: pointer;
  }

  .failed-element-main--clickable:hover {
    background-color: var(--color-hover);
  }

  .failed-element-main--clickable:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
  }

  .failed-element-main:disabled {
    cursor: default;
  }

  .failed-element-row--compact .failed-element-main {
    padding: var(--spacing-xs) var(--spacing-sm);
  }

  /* Status indicator */
  .failed-element-status {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    min-width: 24px;
    margin-right: var(--spacing-sm);
    border-radius: var(--radius-full);
    background-color: rgba(219, 76, 64, 0.2);
    color: var(--color-error);
    font-size: var(--font-size-xs);
    font-weight: 700;
  }

  /* Element type (IFC Class) */
  .failed-element-type {
    width: 140px;
    min-width: 100px;
    font-weight: 500;
    color: var(--color-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Element name */
  .failed-element-name {
    flex: 1;
    min-width: 80px;
    color: var(--color-text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* GlobalId */
  .failed-element-global-id {
    width: 220px;
    min-width: 140px;
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, monospace;
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-align: left;
  }

  /* Message count indicator */
  .failed-element-message-count {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    width: 48px;
    min-width: 48px;
    justify-content: flex-end;
    color: var(--color-text-secondary);
    font-size: var(--font-size-xs);
  }

  .message-count-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 18px;
    height: 18px;
    padding: 0 var(--spacing-xs);
    background-color: rgba(219, 76, 64, 0.2);
    color: var(--color-error);
    border-radius: var(--radius-full);
    font-size: var(--font-size-xs);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .expand-indicator {
    font-size: 10px;
    color: var(--color-text-secondary);
    transition: transform var(--transition-fast);
  }

  /* Messages section */
  .failed-element-messages {
    padding: var(--spacing-sm) var(--spacing-md);
    padding-left: calc(var(--spacing-md) + 32px);
    background-color: rgba(219, 76, 64, 0.05);
    border-top: 1px solid var(--color-border);
  }

  .messages-list {
    margin: 0;
    padding: 0 0 0 var(--spacing-md);
    list-style-type: disc;
  }

  .message-item {
    font-size: var(--font-size-xs);
    color: var(--color-error);
    line-height: 1.5;
    padding: var(--spacing-xs) 0;
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
    padding: var(--spacing-md);
    background-color: var(--color-surface);
    border: none;
    border-top: 1px dashed var(--color-border);
    color: var(--color-primary);
    font-family: inherit;
    font-size: var(--font-size-sm);
    font-weight: 500;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .show-more-btn:hover,
  .show-less-btn:hover {
    background-color: var(--color-hover);
  }

  .show-more-btn:focus-visible,
  .show-less-btn:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
  }

  /* Responsive adjustments */
  @media (max-width: 768px) {
    .failed-elements-table-header {
      display: none;
    }

    .failed-element-main {
      flex-wrap: wrap;
      gap: var(--spacing-xs);
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
      padding-left: calc(24px + var(--spacing-sm));
      margin-top: var(--spacing-xs);
    }

    .failed-element-global-id {
      order: 4;
      flex: 0 0 100%;
      width: auto;
      min-width: unset;
      padding-left: calc(24px + var(--spacing-sm));
    }

    .failed-element-messages {
      padding-left: var(--spacing-md);
    }
  }

  @media (max-width: 480px) {
    .failed-elements-header {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--spacing-xs);
    }

    .failed-element-main {
      padding: var(--spacing-sm);
    }

    .failed-element-type {
      font-size: var(--font-size-xs);
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
