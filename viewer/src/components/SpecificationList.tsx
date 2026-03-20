/**
 * SpecificationList Component
 *
 * Expandable list of specifications with pass/fail badges.
 * - Shows all specifications from validation result
 * - Pass/fail badge for each specification
 * - Expandable/collapsible sections
 * - Shows failed count in badge
 * - Nested requirements display with element details
 */

import { useState, useCallback } from 'react';
import type { SpecificationResult, RequirementResult, ElementResult } from '../types/validation';

/** Props for the SpecificationList component */
export interface SpecificationListProps {
  /** Array of specification results to display */
  specifications: SpecificationResult[];
  /** Whether to initially expand failed specifications */
  autoExpandFailed?: boolean;
  /** Callback when a user clicks an element row (GlobalId) */
  onElementSelect?: (globalId: string) => void;
  /** Callback to create a BCF issue from a failed specification */
  onCreateBcfFromSpec?: (spec: SpecificationResult) => void;
  /** Callback to create a BCF issue from a failed element */
  onCreateBcfFromElement?: (element: ElementResult, specName: string) => void;
}

/** Props for a single specification item */
interface SpecificationItemProps {
  /** The specification result data */
  specification: SpecificationResult;
  /** Whether this item is initially expanded */
  initiallyExpanded?: boolean;
  /** Callback when an element is clicked */
  onElementSelect?: (globalId: string) => void;
  /** Callback to create BCF from this specification */
  onCreateBcfFromSpec?: (spec: SpecificationResult) => void;
  /** Callback to create BCF from a failed element */
  onCreateBcfFromElement?: (element: ElementResult, specName: string) => void;
}

/** Props for a single requirement item */
interface RequirementItemProps {
  /** The requirement result data */
  requirement: RequirementResult;
  /** Index for unique key generation */
  index: number;
  /** Specification name for BCF context */
  specName: string;
  /** Callback when an element is clicked */
  onElementSelect?: (globalId: string) => void;
  /** Callback to create BCF from a failed element */
  onCreateBcfFromElement?: (element: ElementResult, specName: string) => void;
}

/** Maximum elements to show before "Show more" */
const MAX_VISIBLE_ELEMENTS = 5;

/**
 * Get severity icon and color class
 */
function getSeverityInfo(severity: string): { icon: string; className: string } {
  switch (severity) {
    case 'error':
      return { icon: '🔴', className: 'severity--error' };
    case 'warning':
      return { icon: '🟡', className: 'severity--warning' };
    case 'info':
      return { icon: '🔵', className: 'severity--info' };
    default:
      return { icon: '⚪', className: 'severity--default' };
  }
}

/**
 * Format element display name
 */
function formatElementName(element: ElementResult): string {
  const parts: string[] = [];

  if (element.element_type) {
    parts.push(element.element_type);
  }

  if (element.element_name) {
    parts.push(element.element_name);
  }

  if (parts.length === 0) {
    return 'Unknown Element';
  }

  return parts.join(': ');
}

/**
 * Format GlobalId for display (truncate if needed)
 */
function formatGlobalId(globalId: string | null): string {
  if (!globalId) {
    return 'N/A';
  }
  return globalId;
}

/** Props for a single element item */
interface ElementItemProps {
  element: ElementResult;
  specName: string;
  onSelect?: (globalId: string) => void;
  onCreateBcf?: (element: ElementResult, specName: string) => void;
}

/**
 * ElementItem component for displaying a single element.
 * Clickable when onSelect is provided and the element has a GlobalId.
 */
function ElementItem({ element, specName, onSelect, onCreateBcf }: ElementItemProps) {
  const isPassed = element.status === 'pass';
  const isClickable = !!onSelect && !!element.global_id;
  const canCreateBcf = !isPassed && !!onCreateBcf && !!element.global_id;

  const handleClick = () => {
    if (isClickable && element.global_id) {
      onSelect(element.global_id);
    }
  };

  const handleBcfClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (canCreateBcf) {
      onCreateBcf(element, specName);
    }
  };

  return (
    <div
      className={`element-item ${isPassed ? 'element-item--pass' : 'element-item--fail'}${isClickable ? ' element-item--clickable' : ''}`}
      onClick={handleClick}
      role={isClickable ? "button" : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={isClickable ? (e) => { if (e.key === 'Enter' || e.key === ' ') handleClick(); } : undefined}
    >
      <div className="element-header">
        <span className="element-status-icon" aria-hidden="true">
          {isPassed ? '✓' : '✗'}
        </span>
        <span className="element-name" title={formatElementName(element)}>
          {formatElementName(element)}
        </span>
        <span className="element-global-id" title={element.global_id || 'No GlobalId'}>
          ({formatGlobalId(element.global_id)})
        </span>
        {canCreateBcf && (
          <button
            type="button"
            className="element-bcf-btn"
            onClick={handleBcfClick}
            title="BCF issue aanmaken"
          >
            +BCF
          </button>
        )}
      </div>
      {element.messages.length > 0 && (
        <ul className="element-messages">
          {element.messages.map((message, idx) => (
            <li key={idx} className="element-message">
              {message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * RequirementItem component for displaying a single requirement
 */
function RequirementItem({ requirement, index, specName, onElementSelect, onCreateBcfFromElement }: RequirementItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showAllElements, setShowAllElements] = useState(false);

  const isPassed = requirement.status === 'pass';
  const hasFailedElements = requirement.failed_elements > 0;
  const failedElements = requirement.elements.filter(e => e.status === 'fail');
  const passedElements = requirement.elements.filter(e => e.status === 'pass');

  // Determine which elements to show (prioritize failed)
  const elementsToShow = showAllElements
    ? requirement.elements
    : [...failedElements, ...passedElements].slice(0, MAX_VISIBLE_ELEMENTS);

  const remainingCount = requirement.elements.length - elementsToShow.length;

  const toggleExpanded = useCallback(() => {
    setIsExpanded(prev => !prev);
  }, []);

  const handleShowMore = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setShowAllElements(true);
  }, []);

  return (
    <div className={`requirement-item ${isPassed ? 'requirement-item--pass' : 'requirement-item--fail'}`}>
      <button
        type="button"
        className="requirement-header"
        onClick={toggleExpanded}
        aria-expanded={isExpanded}
        aria-controls={`requirement-content-${index}`}
      >
        <span className="requirement-expand-icon" aria-hidden="true">
          {isExpanded ? '▼' : '▶'}
        </span>
        <span className={`requirement-status-badge ${isPassed ? 'badge--pass' : 'badge--fail'}`}>
          {isPassed ? '✓' : '✗'}
        </span>
        <span className="requirement-description">
          {requirement.requirement_description}
        </span>
        {hasFailedElements && (
          <span className="requirement-failed-count" aria-label={`${requirement.failed_elements} failed elements`}>
            [{requirement.failed_elements}]
          </span>
        )}
      </button>

      {isExpanded && (
        <div id={`requirement-content-${index}`} className="requirement-content">
          <div className="requirement-stats">
            <span className="stat">
              <span className="stat-label">Total:</span>
              <span className="stat-value">{requirement.total_elements}</span>
            </span>
            <span className="stat stat--pass">
              <span className="stat-label">Passed:</span>
              <span className="stat-value">{requirement.total_elements - requirement.failed_elements}</span>
            </span>
            <span className="stat stat--fail">
              <span className="stat-label">Failed:</span>
              <span className="stat-value">{requirement.failed_elements}</span>
            </span>
          </div>

          {elementsToShow.length > 0 && (
            <div className="elements-list">
              {elementsToShow.map((element, idx) => (
                <ElementItem
                  key={element.global_id || `element-${idx}`}
                  element={element}
                  specName={specName}
                  onSelect={onElementSelect}
                  onCreateBcf={onCreateBcfFromElement}
                />
              ))}

              {!showAllElements && remainingCount > 0 && (
                <button
                  type="button"
                  className="show-more-btn"
                  onClick={handleShowMore}
                >
                  Show {remainingCount} more element{remainingCount !== 1 ? 's' : ''}...
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * SpecificationItem component for displaying a single specification
 */
function SpecificationItem({ specification, initiallyExpanded = false, onElementSelect, onCreateBcfFromSpec, onCreateBcfFromElement }: SpecificationItemProps) {
  const [isExpanded, setIsExpanded] = useState(initiallyExpanded);

  const isPassed = specification.status === 'pass';
  const severityInfo = getSeverityInfo(specification.severity);
  const hasFailedRequirements = specification.failed_requirements > 0;
  const canCreateBcf = !isPassed && !!onCreateBcfFromSpec;

  const toggleExpanded = useCallback(() => {
    setIsExpanded(prev => !prev);
  }, []);

  const handleBcfClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (canCreateBcf) {
      onCreateBcfFromSpec(specification);
    }
  }, [canCreateBcf, onCreateBcfFromSpec, specification]);

  return (
    <div className={`specification-item ${isPassed ? 'specification-item--pass' : 'specification-item--fail'}`}>
      <button
        type="button"
        className="specification-header"
        onClick={toggleExpanded}
        aria-expanded={isExpanded}
        aria-controls={`spec-content-${specification.specification_name}`}
      >
        <span className="specification-expand-icon" aria-hidden="true">
          {isExpanded ? '▼' : '▶'}
        </span>
        <span className={`specification-status-badge ${isPassed ? 'badge--pass' : 'badge--fail'}`}>
          {isPassed ? '✓' : '✗'}
        </span>
        <span className={`specification-severity ${severityInfo.className}`} aria-label={`Severity: ${specification.severity}`}>
          <span aria-hidden="true">{severityInfo.icon}</span>
        </span>
        <span className="specification-name" title={specification.specification_name}>
          {specification.specification_name}
        </span>
        {canCreateBcf && (
          <button
            type="button"
            className="specification-bcf-btn"
            onClick={handleBcfClick}
            title="BCF issue aanmaken voor deze specificatie"
          >
            +BCF
          </button>
        )}
        {hasFailedRequirements && (
          <span className="specification-failed-badge" aria-label={`${specification.failed_requirements} failed requirements`}>
            [{specification.failed_requirements}]
          </span>
        )}
      </button>

      {isExpanded && (
        <div id={`spec-content-${specification.specification_name}`} className="specification-content">
          <div className="specification-stats">
            <span className="stat">
              <span className="stat-label">Requirements:</span>
              <span className="stat-value">{specification.total_requirements}</span>
            </span>
            <span className="stat stat--pass">
              <span className="stat-label">Passed:</span>
              <span className="stat-value">{specification.total_requirements - specification.failed_requirements}</span>
            </span>
            <span className="stat stat--fail">
              <span className="stat-label">Failed:</span>
              <span className="stat-value">{specification.failed_requirements}</span>
            </span>
          </div>

          <div className="requirements-list">
            {specification.requirements.map((requirement, idx) => (
              <RequirementItem
                key={`${specification.specification_name}-req-${idx}`}
                requirement={requirement}
                index={idx}
                specName={specification.specification_name}
                onElementSelect={onElementSelect}
                onCreateBcfFromElement={onCreateBcfFromElement}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * SpecificationList component displaying all validation specifications
 */
export function SpecificationList({ specifications, autoExpandFailed = true, onElementSelect, onCreateBcfFromSpec, onCreateBcfFromElement }: SpecificationListProps) {
  if (specifications.length === 0) {
    return (
      <div className="specification-list specification-list--empty">
        <p className="empty-message">No specifications to display.</p>
        <style>{specificationListStyles}</style>
      </div>
    );
  }

  // Sort specifications: failed first, then passed
  const sortedSpecifications = [...specifications].sort((a, b) => {
    if (a.status === 'fail' && b.status === 'pass') return -1;
    if (a.status === 'pass' && b.status === 'fail') return 1;
    return 0;
  });

  return (
    <div className="specification-list" role="list" aria-label="Validation Specifications">
      {sortedSpecifications.map((spec) => (
        <SpecificationItem
          key={spec.specification_name}
          specification={spec}
          initiallyExpanded={autoExpandFailed && spec.status === 'fail'}
          onElementSelect={onElementSelect}
          onCreateBcfFromSpec={onCreateBcfFromSpec}
          onCreateBcfFromElement={onCreateBcfFromElement}
        />
      ))}
      <style>{specificationListStyles}</style>
    </div>
  );
}

/** Styles for the SpecificationList component */
const specificationListStyles = `
  .specification-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .specification-list--empty {
    padding: var(--spacing-xl);
    text-align: center;
    background-color: var(--color-surface);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
  }

  .empty-message {
    color: var(--color-text-secondary);
    font-size: var(--font-size-base);
    margin: 0;
  }

  /* Specification Item */
  .specification-item {
    background-color: var(--color-surface);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
    overflow: hidden;
  }

  .specification-item--pass {
    border-left: 4px solid var(--color-success);
  }

  .specification-item--fail {
    border-left: 4px solid var(--color-error);
  }

  .specification-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    width: 100%;
    padding: var(--spacing-md);
    background: none;
    border: none;
    cursor: pointer;
    font-family: inherit;
    font-size: var(--font-size-base);
    text-align: left;
    color: var(--color-text);
    transition: background-color var(--transition-fast);
  }

  .specification-header:hover {
    background-color: var(--color-hover);
  }

  .specification-header:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
  }

  .specification-expand-icon {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    min-width: 12px;
    transition: transform var(--transition-fast);
  }

  .specification-status-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    min-width: 24px;
    border-radius: var(--radius-full);
    font-size: var(--font-size-sm);
    font-weight: 700;
  }

  .badge--pass {
    background-color: rgba(68, 182, 168, 0.2);
    color: var(--color-success);
  }

  .badge--fail {
    background-color: rgba(219, 76, 64, 0.2);
    color: var(--color-error);
  }

  .specification-severity {
    display: flex;
    align-items: center;
    font-size: var(--font-size-sm);
  }

  .severity--error {
    color: var(--color-error);
  }

  .severity--warning {
    color: var(--color-warning);
  }

  .severity--info {
    color: var(--color-primary);
  }

  .specification-name {
    flex: 1;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .specification-failed-badge {
    padding: var(--spacing-xs) var(--spacing-sm);
    background-color: rgba(219, 76, 64, 0.15);
    color: var(--color-error);
    border-radius: var(--radius-sm);
    font-size: var(--font-size-sm);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .specification-content {
    padding: 0 var(--spacing-md) var(--spacing-md);
    border-top: 1px solid var(--color-border);
  }

  .specification-stats,
  .requirement-stats {
    display: flex;
    gap: var(--spacing-lg);
    padding: var(--spacing-sm) 0;
    font-size: var(--font-size-sm);
  }

  .stat {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
  }

  .stat-label {
    color: var(--color-text-secondary);
  }

  .stat-value {
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .stat--pass .stat-value {
    color: var(--color-success);
  }

  .stat--fail .stat-value {
    color: var(--color-error);
  }

  /* Requirements List */
  .requirements-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    margin-top: var(--spacing-sm);
    padding-left: var(--spacing-md);
    border-left: 2px solid var(--color-border);
  }

  .requirement-item {
    background-color: var(--color-background);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border);
    overflow: hidden;
  }

  .requirement-item--pass {
    border-left: 3px solid var(--color-success);
  }

  .requirement-item--fail {
    border-left: 3px solid var(--color-error);
  }

  .requirement-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    background: none;
    border: none;
    cursor: pointer;
    font-family: inherit;
    font-size: var(--font-size-sm);
    text-align: left;
    color: var(--color-text);
    transition: background-color var(--transition-fast);
  }

  .requirement-header:hover {
    background-color: var(--color-hover);
  }

  .requirement-header:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
  }

  .requirement-expand-icon {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    min-width: 10px;
  }

  .requirement-status-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    min-width: 20px;
    border-radius: var(--radius-full);
    font-size: var(--font-size-xs);
    font-weight: 700;
  }

  .requirement-description {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .requirement-failed-count {
    padding: 2px var(--spacing-xs);
    background-color: rgba(219, 76, 64, 0.15);
    color: var(--color-error);
    border-radius: var(--radius-sm);
    font-size: var(--font-size-xs);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .requirement-content {
    padding: var(--spacing-sm) var(--spacing-md);
    border-top: 1px solid var(--color-border);
  }

  /* Elements List */
  .elements-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    margin-top: var(--spacing-sm);
  }

  .element-item {
    padding: var(--spacing-sm);
    background-color: var(--color-surface);
    border-radius: var(--radius-sm);
    border-left: 2px solid var(--color-border);
  }

  .element-item--pass {
    border-left-color: var(--color-success);
  }

  .element-item--fail {
    border-left-color: var(--color-error);
    background-color: rgba(219, 76, 64, 0.05);
  }

  .element-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: var(--font-size-sm);
  }

  .element-status-icon {
    font-weight: 700;
    font-size: var(--font-size-xs);
  }

  .element-item--pass .element-status-icon {
    color: var(--color-success);
  }

  .element-item--fail .element-status-icon {
    color: var(--color-error);
  }

  .element-name {
    font-weight: 500;
    color: var(--color-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
  }

  .element-global-id {
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Consolas, monospace;
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    flex-shrink: 0;
  }

  .element-messages {
    margin: var(--spacing-xs) 0 0;
    padding-left: var(--spacing-lg);
    list-style: disc;
  }

  .element-message {
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    line-height: 1.4;
  }

  .element-item--fail .element-message {
    color: var(--color-error);
  }

  .element-item--clickable {
    cursor: pointer;
    transition: background-color var(--transition-fast),
                border-left-color var(--transition-fast);
  }

  .element-item--clickable:hover {
    background-color: var(--color-hover);
    border-left-color: var(--color-primary);
  }

  .element-item--clickable:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
  }

  /* BCF buttons */
  .specification-bcf-btn,
  .element-bcf-btn {
    font-size: 0.6875rem;
    padding: 1px 6px;
    border-radius: 3px;
    border: 1px solid var(--magic-violet, #350E35);
    background: transparent;
    color: var(--magic-violet, #350E35);
    cursor: pointer;
    font-weight: 600;
    font-family: inherit;
    white-space: nowrap;
    flex-shrink: 0;
    transition: all var(--transition-fast);
  }

  .specification-bcf-btn:hover,
  .element-bcf-btn:hover {
    background-color: var(--magic-violet, #350E35);
    color: #fff;
  }

  .element-bcf-btn {
    opacity: 0;
  }

  .element-item--fail:hover .element-bcf-btn {
    opacity: 1;
  }

  .show-more-btn {
    display: block;
    width: 100%;
    padding: var(--spacing-sm);
    background-color: var(--color-surface);
    border: 1px dashed var(--color-border);
    border-radius: var(--radius-sm);
    color: var(--color-primary);
    font-size: var(--font-size-sm);
    font-weight: 500;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .show-more-btn:hover {
    background-color: var(--color-hover);
    border-color: var(--color-primary);
  }

  .show-more-btn:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  /* Responsive adjustments */
  @media (max-width: 600px) {
    .specification-header,
    .requirement-header {
      flex-wrap: wrap;
    }

    .specification-name,
    .requirement-description {
      flex-basis: 100%;
      order: 10;
      margin-top: var(--spacing-xs);
      white-space: normal;
    }

    .specification-stats,
    .requirement-stats {
      flex-wrap: wrap;
      gap: var(--spacing-md);
    }

    .requirements-list {
      padding-left: var(--spacing-sm);
    }

    .element-header {
      flex-wrap: wrap;
    }

    .element-name {
      flex-basis: 100%;
      order: 10;
    }

    .element-global-id {
      flex-basis: 100%;
      order: 11;
      margin-top: var(--spacing-xs);
    }
  }

  @media (max-width: 400px) {
    .specification-header {
      padding: var(--spacing-sm);
    }

    .specification-content {
      padding: var(--spacing-sm);
    }
  }
`;

export default SpecificationList;
