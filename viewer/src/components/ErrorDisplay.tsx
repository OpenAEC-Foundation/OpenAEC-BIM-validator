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
              <button
                type="button"
                className="error-retry-btn"
                onClick={onRetry}
                aria-label={`${retryLabel} - ${getErrorTitle(type)}`}
              >
                <span className="retry-icon" aria-hidden="true">
                  ↻
                </span>
                {retryLabel}
              </button>
            )}
            {onDismiss && (
              <button
                type="button"
                className="error-dismiss-btn"
                onClick={onDismiss}
                aria-label="Dismiss error"
              >
                Dismiss
              </button>
            )}
          </div>
        )}
      </div>

      {/* Close button (always visible if onDismiss provided) */}
      {onDismiss && !compact && (
        <button
          type="button"
          className="error-close-btn"
          onClick={onDismiss}
          aria-label="Close error message"
        >
          ✕
        </button>
      )}

      {/* Styles */}
      <style>{`
        .error-display {
          display: flex;
          align-items: flex-start;
          gap: var(--spacing-md);
          padding: var(--spacing-lg);
          background-color: rgba(219, 76, 64, 0.1);
          border: 1px solid var(--color-error);
          border-radius: var(--radius-lg);
          border-left: 4px solid var(--color-error);
          position: relative;
        }

        .error-display--compact {
          padding: var(--spacing-md);
          align-items: center;
        }

        /* Error type variations */
        .error-display--upload {
          border-color: var(--color-error);
          border-left-color: var(--color-error);
          background-color: rgba(219, 76, 64, 0.08);
        }

        .error-display--validation {
          border-color: var(--color-warning);
          border-left-color: var(--color-warning);
          background-color: rgba(239, 189, 117, 0.15);
        }

        .error-display--network {
          border-color: var(--color-error);
          border-left-color: var(--color-error);
          background-color: rgba(219, 76, 64, 0.08);
        }

        .error-display--generic {
          border-color: var(--color-error);
          border-left-color: var(--color-error);
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
          background-color: var(--color-background);
          border-radius: var(--radius-full);
          border: 2px solid var(--color-error);
        }

        .error-display--validation .error-icon-container {
          border-color: var(--color-warning);
        }

        .error-display--compact .error-icon-container {
          width: 36px;
          height: 36px;
          min-width: 36px;
        }

        .error-icon {
          font-size: var(--font-size-xl);
          line-height: 1;
        }

        .error-display--compact .error-icon {
          font-size: var(--font-size-lg);
        }

        /* Content area */
        .error-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: var(--spacing-sm);
          min-width: 0;
        }

        .error-display--compact .error-content {
          gap: var(--spacing-xs);
        }

        /* Title */
        .error-title {
          margin: 0;
          font-size: var(--font-size-lg);
          font-weight: 600;
          color: var(--color-error);
        }

        .error-display--validation .error-title {
          color: var(--color-warning-dark, #c99a40);
        }

        /* Message */
        .error-message {
          margin: 0;
          font-size: var(--font-size-base);
          color: var(--color-text);
          line-height: 1.5;
        }

        .error-display--compact .error-message {
          font-size: var(--font-size-sm);
        }

        /* Details (expandable) */
        .error-details {
          margin-top: var(--spacing-xs);
        }

        .error-details-summary {
          font-size: var(--font-size-sm);
          color: var(--color-text-secondary);
          cursor: pointer;
          user-select: none;
        }

        .error-details-summary:hover {
          color: var(--color-text);
        }

        .error-details-content {
          margin: var(--spacing-sm) 0 0 0;
          padding: var(--spacing-md);
          background-color: var(--color-background);
          border-radius: var(--radius-sm);
          font-size: var(--font-size-xs);
          font-family: monospace;
          color: var(--color-text-secondary);
          overflow-x: auto;
          white-space: pre-wrap;
          word-break: break-word;
          max-height: 150px;
          overflow-y: auto;
        }

        /* Hint text */
        .error-hint {
          margin: 0;
          font-size: var(--font-size-sm);
          color: var(--color-text-secondary);
          font-style: italic;
        }

        /* Action buttons */
        .error-actions {
          display: flex;
          gap: var(--spacing-sm);
          margin-top: var(--spacing-sm);
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
          gap: var(--spacing-xs);
          padding: var(--spacing-sm) var(--spacing-lg);
          border: none;
          border-radius: var(--radius-md);
          background-color: var(--color-error);
          color: var(--color-text-light);
          font-size: var(--font-size-sm);
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
          outline: 2px solid var(--color-error);
          outline-offset: 2px;
        }

        .retry-icon {
          font-size: var(--font-size-lg);
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
          padding: var(--spacing-sm) var(--spacing-lg);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          background-color: var(--color-surface);
          color: var(--color-text-secondary);
          font-size: var(--font-size-sm);
          font-weight: 500;
          cursor: pointer;
          transition: all var(--transition-fast);
          min-height: 40px;
        }

        .error-dismiss-btn:hover {
          border-color: var(--color-text-secondary);
          color: var(--color-text);
        }

        .error-dismiss-btn:focus-visible {
          outline: 2px solid var(--color-primary);
          outline-offset: 2px;
        }

        /* Close button (top-right corner) */
        .error-close-btn {
          position: absolute;
          top: var(--spacing-sm);
          right: var(--spacing-sm);
          display: flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
          padding: 0;
          border: none;
          border-radius: var(--radius-full);
          background-color: transparent;
          color: var(--color-text-secondary);
          font-size: var(--font-size-base);
          cursor: pointer;
          transition: all var(--transition-fast);
        }

        .error-close-btn:hover {
          background-color: rgba(219, 76, 64, 0.2);
          color: var(--color-error);
        }

        .error-close-btn:focus-visible {
          outline: 2px solid var(--color-error);
          outline-offset: 2px;
        }

        /* Responsive adjustments */
        @media (max-width: 480px) {
          .error-display {
            flex-direction: column;
            align-items: stretch;
            padding: var(--spacing-md);
          }

          .error-display--compact {
            flex-direction: row;
            flex-wrap: wrap;
          }

          .error-icon-container {
            align-self: center;
            margin-bottom: var(--spacing-sm);
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
            margin-top: var(--spacing-sm);
            margin-left: 0;
          }

          .error-close-btn {
            position: static;
            align-self: flex-end;
            margin-bottom: var(--spacing-sm);
          }
        }

        /* Touch device adjustments */
        @media (hover: none) and (pointer: coarse) {
          .error-retry-btn,
          .error-dismiss-btn {
            min-height: 44px;
            padding: var(--spacing-md) var(--spacing-lg);
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
