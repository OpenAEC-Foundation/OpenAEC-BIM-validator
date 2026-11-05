import { Button as OaButton } from "@openaec/ui-react";
/**
 * ErrorDisplay Component
 *
 * Error message component for displaying upload errors, validation errors,
 * and network errors. Includes retry button functionality.
 */

/** Error type for categorizing different error sources */
export type ErrorType = 'upload' | 'validation' | 'network' | 'generic';

/** Props for the ErrorDisplay component */
export interface ErrorDisplayProps {
  /** Error message to display */
  message: string;
  /** Type of error for appropriate styling and icon */
  type?: ErrorType;
  /** Additional error details (optional) */
  details?: string | null;
  /** Callback when retry button is clicked */
  onRetry?: () => void;
  /** Callback when dismiss button is clicked */
  onDismiss?: () => void;
  /** Custom retry button text */
  retryLabel?: string;
  /** Whether to show the error in a compact format */
  compact?: boolean;
}

/**
 * Get icon based on error type
 */
function getErrorIcon(type: ErrorType): string {
  switch (type) {
    case 'upload':
      return '📁';
    case 'validation':
      return '⚠️';
    case 'network':
      return '🌐';
    case 'generic':
    default:
      return '❌';
  }
}

/**
 * Get title based on error type
 */
function getErrorTitle(type: ErrorType): string {
  switch (type) {
    case 'upload':
      return 'Upload Error';
    case 'validation':
      return 'Validation Error';
    case 'network':
      return 'Network Error';
    case 'generic':
    default:
      return 'Error';
  }
}

/**
 * Get helpful hint based on error type
 */
function getErrorHint(type: ErrorType): string | null {
  switch (type) {
    case 'upload':
      return 'Please check the file and try again.';
    case 'validation':
      return 'There was a problem validating your file.';
    case 'network':
      return 'Please check your connection and try again.';
    case 'generic':
    default:
      return null;
  }
}

/**
 * ErrorDisplay component showing error messages with retry functionality
 */
export function ErrorDisplay({
  message,
  type = 'generic',
  details,
  onRetry,
  onDismiss,
  retryLabel = 'Try Again',
  compact = false,
}: ErrorDisplayProps) {
  const containerClasses = [
    'error-display',
    `error-display--${type}`,
    compact ? 'error-display--compact' : '',
  ]
    .filter(Boolean)
    .join(' ');

  const hint = getErrorHint(type);

  return (
    <div
      className={containerClasses}
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      {/* Error icon */}
      <div className="error-icon-container">
        <span className="error-icon" aria-hidden="true">
          {getErrorIcon(type)}
        </span>
      </div>

      {/* Error content */}
      <div className="error-content">
        {/* Error title */}
        {!compact && (
          <h3 className="error-title">{getErrorTitle(type)}</h3>
        )}

        {/* Error message */}
        <p className="error-message">{message}</p>

        {/* Error details (if provided) */}
        {details && (
          <details className="error-details">
            <summary className="error-details-summary">
              Show technical details
            </summary>
            <pre className="error-details-content">{details}</pre>
          </details>
        )}

        {/* Hint text */}
        {!compact && hint && (
          <p className="error-hint">{hint}</p>
        )}

        {/* Action buttons */}
        {(onRetry || onDismiss) && (
          <div className="error-actions">
            {onRetry && (
              <OaButton
                type="button"
                className="error-retry-btn"
                onClick={onRetry}
                aria-label={`${retryLabel} - ${getErrorTitle(type)}`}
              >
                <span className="retry-icon" aria-hidden="true">
                  ↻
                </span>
                {retryLabel}
              </OaButton>
            )}
            {onDismiss && (
              <OaButton
                type="button"
                className="error-dismiss-btn"
                onClick={onDismiss}
                aria-label="Dismiss error"
              >
                Dismiss
              </OaButton>
            )}
          </div>
        )}
      </div>

      {/* Close button (always visible if onDismiss provided) */}
      {onDismiss && !compact && (
        <OaButton kind="quiet"
          type="button"
          className="error-close-btn"
          onClick={onDismiss}
          aria-label="Close error message"
        >
          ✕
        </OaButton>
      )}

      {/* Styles */}
      <style>{`
        .error-display {
          display: flex;
          align-items: flex-start;
          gap: var(--oa-space-lg);
          padding: var(--oa-space-xl);
          background-color: rgba(219, 76, 64, 0.1);
          border: 1px solid var(--oa-error);
          border-radius: var(--oa-radius-large);
          border-left: 4px solid var(--oa-error);
          position: relative;
        }

        .error-display--compact {
          padding: var(--oa-space-lg);
          align-items: center;
        }

        /* Error type variations */
        .error-display--upload {
          border-color: var(--oa-error);
          border-left-color: var(--oa-error);
          background-color: rgba(219, 76, 64, 0.08);
        }

        .error-display--validation {
          border-color: var(--oa-warning);
          border-left-color: var(--oa-warning);
          background-color: rgba(239, 189, 117, 0.15);
        }

        .error-display--network {
          border-color: var(--oa-error);
          border-left-color: var(--oa-error);
          background-color: rgba(219, 76, 64, 0.08);
        }

        .error-display--generic {
          border-color: var(--oa-error);
          border-left-color: var(--oa-error);
          background-color: rgba(219, 76, 64, 0.08);
        }

        /* Icon container */
        .error-icon-container {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 48px;
          height: 48px;
          min-width: 48px;
          background-color: var(--oa-panel);
          border-radius: var(--oa-radius-full);
          border: 2px solid var(--oa-error);
        }

        .error-display--validation .error-icon-container {
          border-color: var(--oa-warning);
        }

        .error-display--compact .error-icon-container {
          width: 36px;
          height: 36px;
          min-width: 36px;
        }

        .error-icon {
          font-size: var(--oa-size-dialog-heading);
          line-height: 1;
        }

        .error-display--compact .error-icon {
          font-size: var(--oa-size-panel-heading);
        }

        /* Content area */
        .error-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: var(--oa-space-sm);
          min-width: 0;
        }

        .error-display--compact .error-content {
          gap: var(--oa-space-xs);
        }

        /* Title */
        .error-title {
          margin: 0;
          font-size: var(--oa-size-panel-heading);
          font-weight: 600;
          color: var(--oa-error);
        }

        .error-display--validation .error-title {
          color: var(--oa-warning, #c99a40);
        }

        /* Message */
        .error-message {
          margin: 0;
          font-size: var(--oa-size-body);
          color: var(--oa-text);
          line-height: 1.5;
        }

        .error-display--compact .error-message {
          font-size: var(--oa-size-body);
        }

        /* Details (expandable) */
        .error-details {
          margin-top: var(--oa-space-xs);
        }

        .error-details-summary {
          font-size: var(--oa-size-body);
          color: var(--oa-text-secondary);
          cursor: pointer;
          user-select: none;
        }

        .error-details-summary:hover {
          color: var(--oa-text);
        }

        .error-details-content {
          margin: var(--oa-space-sm) 0 0 0;
          padding: var(--oa-space-lg);
          background-color: var(--oa-panel);
          border-radius: var(--oa-radius-small);
          font-size: var(--oa-size-label);
          font-family: monospace;
          color: var(--oa-text-secondary);
          overflow-x: auto;
          white-space: pre-wrap;
          word-break: break-word;
          max-height: 150px;
          overflow-y: auto;
        }

        /* Hint text */
        .error-hint {
          margin: 0;
          font-size: var(--oa-size-body);
          color: var(--oa-text-secondary);
          font-style: italic;
        }

        /* Action buttons */
        .error-actions {
          display: flex;
          gap: var(--oa-space-sm);
          margin-top: var(--oa-space-sm);
          flex-wrap: wrap;
        }

        .error-display--compact .error-actions {
          margin-top: 0;
          margin-left: auto;
        }

        /* Retry button */
        .error-retry-btn {
          display: inline-flex;
          align-items: center;
          gap: var(--oa-space-xs);
          padding: var(--oa-space-sm) var(--oa-space-xl);
          border: none;
          border-radius: var(--oa-radius-medium);
          background-color: var(--oa-error);
          color: var(--oa-text-on-accent);
          font-size: var(--oa-size-body);
          font-weight: 600;
          cursor: pointer;
          transition: all var(--transition-fast);
          min-height: 40px;
        }

        .error-retry-btn:hover {
          background-color: #c43830;
          transform: translateY(-1px);
        }

        .error-retry-btn:active {
          transform: translateY(0);
        }

        .error-retry-btn:focus-visible {
          outline: 2px solid var(--oa-error);
          outline-offset: 2px;
        }

        .retry-icon {
          font-size: var(--oa-size-panel-heading);
          display: inline-block;
          transition: transform var(--transition-fast);
        }

        .error-retry-btn:hover .retry-icon {
          transform: rotate(-45deg);
        }

        /* Dismiss button */
        .error-dismiss-btn {
          display: inline-flex;
          align-items: center;
          padding: var(--oa-space-sm) var(--oa-space-xl);
          border: 1px solid var(--oa-border);
          border-radius: var(--oa-radius-medium);
          background-color: var(--oa-panel);
          color: var(--oa-text-secondary);
          font-size: var(--oa-size-body);
          font-weight: 500;
          cursor: pointer;
          transition: all var(--transition-fast);
          min-height: 40px;
        }

        .error-dismiss-btn:hover {
          border-color: var(--oa-text-secondary);
          color: var(--oa-text);
        }

        .error-dismiss-btn:focus-visible {
          outline: 2px solid var(--oa-accent);
          outline-offset: 2px;
        }

        /* Close button (top-right corner) */
        .error-close-btn {
          position: absolute;
          top: var(--oa-space-sm);
          right: var(--oa-space-sm);
          display: flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
          padding: 0;
          border: none;
          border-radius: var(--oa-radius-full);
          background-color: transparent;
          color: var(--oa-text-secondary);
          font-size: var(--oa-size-body);
          cursor: pointer;
          transition: all var(--transition-fast);
        }

        .error-close-btn:hover {
          background-color: rgba(219, 76, 64, 0.2);
          color: var(--oa-error);
        }

        .error-close-btn:focus-visible {
          outline: 2px solid var(--oa-error);
          outline-offset: 2px;
        }

        /* Responsive adjustments */
        @media (max-width: 480px) {
          .error-display {
            flex-direction: column;
            align-items: stretch;
            padding: var(--oa-space-lg);
          }

          .error-display--compact {
            flex-direction: row;
            flex-wrap: wrap;
          }

          .error-icon-container {
            align-self: center;
            margin-bottom: var(--oa-space-sm);
          }

          .error-display--compact .error-icon-container {
            align-self: flex-start;
            margin-bottom: 0;
          }

          .error-content {
            text-align: center;
          }

          .error-display--compact .error-content {
            text-align: left;
          }

          .error-actions {
            justify-content: center;
          }

          .error-display--compact .error-actions {
            width: 100%;
            margin-top: var(--oa-space-sm);
            margin-left: 0;
          }

          .error-close-btn {
            position: static;
            align-self: flex-end;
            margin-bottom: var(--oa-space-sm);
          }
        }

        /* Touch device adjustments */
        @media (hover: none) and (pointer: coarse) {
          .error-retry-btn,
          .error-dismiss-btn {
            min-height: 44px;
            padding: var(--oa-space-lg) var(--oa-space-xl);
          }

          .error-close-btn {
            width: 44px;
            height: 44px;
          }
        }

        /* Reduced motion preference */
        @media (prefers-reduced-motion: reduce) {
          .error-retry-btn:hover {
            transform: none;
          }

          .error-retry-btn:hover .retry-icon {
            transform: none;
          }
        }

        /* High contrast mode */
        @media (prefers-contrast: high) {
          .error-display {
            border-width: 2px;
            border-left-width: 6px;
          }

          .error-retry-btn {
            border: 2px solid currentColor;
          }
        }
      `}</style>
    </div>
  );
}

export default ErrorDisplay;
