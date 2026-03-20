/**
 * ResultsSummary Component
 *
 * Summary card showing validation results overview.
 * - Total specifications count
 * - Passed specifications (green)
 * - Failed specifications (red)
 * - Download JSON button
 * - File names and timestamp
 */

import type { ValidationResult } from '../types/validation';

/** Props for the ResultsSummary component */
export interface ResultsSummaryProps {
  /** Validation result data */
  result: ValidationResult;
  /** Callback to download results as JSON */
  onDownloadJson?: () => void;
  /** Callback to download results as BCF 2.1 .bcfzip */
  onDownloadBcf?: () => void;
}

/**
 * Format timestamp for display
 */
function formatTimestamp(isoTimestamp: string): string {
  try {
    const date = new Date(isoTimestamp);
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoTimestamp;
  }
}

/**
 * Format file size for display
 */
function formatElementCount(count: number): string {
  if (count >= 1000000) {
    return `${(count / 1000000).toFixed(1)}M`;
  }
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  return count.toString();
}

/**
 * ResultsSummary component displaying validation overview with statistics
 */
export function ResultsSummary({ result, onDownloadJson, onDownloadBcf }: ResultsSummaryProps) {
  const {
    success,
    ifc_file_name,
    ids_file_name,
    total_specifications,
    failed_specifications,
    total_elements_validated,
    validation_timestamp,
  } = result;

  const passedSpecifications = total_specifications - failed_specifications;

  // Determine overall status styling
  const statusClass = success ? 'results-summary--success' : 'results-summary--failure';

  return (
    <div className={`results-summary ${statusClass}`} role="region" aria-label="Validation Results Summary">
      {/* Header with title and download button */}
      <div className="summary-header">
        <div className="summary-title">
          <span className="summary-icon" aria-hidden="true">
            {success ? '✅' : '❌'}
          </span>
          <h2 className="summary-heading">
            {success ? 'Validation Passed' : 'Validation Failed'}
          </h2>
        </div>
        <div className="summary-actions">
          {onDownloadBcf && (
            <button
              type="button"
              className="download-btn"
              onClick={onDownloadBcf}
              aria-label="Download results as BCF"
            >
              <span className="download-icon" aria-hidden="true">⬇</span>
              <span className="download-text">BCF</span>
            </button>
          )}
          {onDownloadJson && (
            <button
              type="button"
              className="download-btn"
              onClick={onDownloadJson}
              aria-label="Download results as JSON"
            >
              <span className="download-icon" aria-hidden="true">⬇</span>
              <span className="download-text">JSON</span>
            </button>
          )}
        </div>
      </div>

      {/* Statistics cards */}
      <div className="summary-stats">
        <div className="stat-card stat-card--total">
          <span className="stat-value">{total_specifications}</span>
          <span className="stat-label">Total</span>
        </div>
        <div className="stat-card stat-card--passed">
          <span className="stat-value">{passedSpecifications}</span>
          <span className="stat-label">Passed</span>
        </div>
        <div className="stat-card stat-card--failed">
          <span className="stat-value">{failed_specifications}</span>
          <span className="stat-label">Failed</span>
        </div>
      </div>

      {/* File information */}
      <div className="summary-details">
        <div className="detail-row">
          <span className="detail-label">IFC File:</span>
          <span className="detail-value" title={ifc_file_name}>{ifc_file_name}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">IDS File:</span>
          <span className="detail-value" title={ids_file_name}>{ids_file_name}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Elements Validated:</span>
          <span className="detail-value">{formatElementCount(total_elements_validated)}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Completed:</span>
          <span className="detail-value">{formatTimestamp(validation_timestamp)}</span>
        </div>
      </div>

      {/* Styles */}
      <style>{`
        .results-summary {
          background-color: var(--color-surface);
          border-radius: var(--radius-lg);
          border: 1px solid var(--color-border);
          padding: var(--spacing-lg);
          box-shadow: var(--shadow-sm);
        }

        .results-summary--success {
          border-color: var(--color-success);
          border-left: 4px solid var(--color-success);
        }

        .results-summary--failure {
          border-color: var(--color-error);
          border-left: 4px solid var(--color-error);
        }

        /* Header */
        .summary-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: var(--spacing-lg);
          flex-wrap: wrap;
          gap: var(--spacing-md);
        }

        .summary-title {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
        }

        .summary-icon {
          font-size: var(--font-size-2xl);
          line-height: 1;
        }

        .summary-heading {
          margin: 0;
          font-size: var(--font-size-xl);
          font-weight: 600;
          color: var(--color-text);
        }

        .results-summary--success .summary-heading {
          color: var(--color-success);
        }

        .results-summary--failure .summary-heading {
          color: var(--color-error);
        }

        .summary-actions {
          display: flex;
          gap: var(--spacing-sm);
        }

        /* Download button */
        .download-btn {
          display: flex;
          align-items: center;
          gap: var(--spacing-xs);
          padding: var(--spacing-sm) var(--spacing-md);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          background-color: var(--color-background);
          color: var(--color-text);
          font-size: var(--font-size-sm);
          font-weight: 500;
          cursor: pointer;
          transition: all var(--transition-fast);
        }

        .download-btn:hover {
          border-color: var(--color-primary);
          background-color: var(--color-hover);
          color: var(--color-primary);
        }

        .download-btn:focus-visible {
          outline: 2px solid var(--color-primary);
          outline-offset: 2px;
        }

        .download-icon {
          font-size: var(--font-size-base);
        }

        /* Statistics cards */
        .summary-stats {
          display: flex;
          gap: var(--spacing-md);
          margin-bottom: var(--spacing-lg);
        }

        .stat-card {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: var(--spacing-md) var(--spacing-sm);
          border-radius: var(--radius-md);
          background-color: var(--color-background);
          border: 1px solid var(--color-border);
          min-width: 80px;
        }

        .stat-value {
          font-size: var(--font-size-2xl);
          font-weight: 700;
          line-height: 1.2;
          font-variant-numeric: tabular-nums;
        }

        .stat-label {
          font-size: var(--font-size-sm);
          color: var(--color-text-secondary);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .stat-card--total {
          border-color: var(--color-border);
        }

        .stat-card--total .stat-value {
          color: var(--color-text);
        }

        .stat-card--passed {
          border-color: var(--color-success);
          background-color: rgba(68, 182, 168, 0.1);
        }

        .stat-card--passed .stat-value {
          color: var(--color-success);
        }

        .stat-card--failed {
          border-color: var(--color-error);
          background-color: rgba(219, 76, 64, 0.1);
        }

        .stat-card--failed .stat-value {
          color: var(--color-error);
        }

        /* Details section */
        .summary-details {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-sm);
          padding-top: var(--spacing-md);
          border-top: 1px solid var(--color-border);
        }

        .detail-row {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          font-size: var(--font-size-sm);
        }

        .detail-label {
          color: var(--color-text-secondary);
          min-width: 140px;
          flex-shrink: 0;
        }

        .detail-value {
          color: var(--color-text);
          font-weight: 500;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        /* Responsive adjustments */
        @media (max-width: 600px) {
          .summary-header {
            flex-direction: column;
            align-items: stretch;
          }

          .summary-title {
            justify-content: center;
          }

          .download-btn {
            align-self: center;
          }

          .summary-stats {
            flex-direction: column;
          }

          .stat-card {
            flex-direction: row;
            justify-content: space-between;
            padding: var(--spacing-md);
          }

          .stat-value {
            font-size: var(--font-size-xl);
          }

          .stat-label {
            order: -1;
          }

          .detail-row {
            flex-direction: column;
            align-items: flex-start;
            gap: var(--spacing-xs);
          }

          .detail-label {
            min-width: unset;
          }

          .detail-value {
            white-space: normal;
            word-break: break-all;
          }
        }

        @media (max-width: 400px) {
          .results-summary {
            padding: var(--spacing-md);
          }

          .summary-heading {
            font-size: var(--font-size-lg);
          }
        }
      `}</style>
    </div>
  );
}

export default ResultsSummary;
