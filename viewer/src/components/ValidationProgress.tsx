/**
 * ValidationProgress Component
 *
 * Progress indicator that shows during validation polling.
 * - Shows spinner animation
 * - Displays progress message from job status
 * - Shows elapsed time since validation started
 * - Different visual states for pending/processing
 */

import { useState, useEffect, useCallback } from 'react';
import type { JobStatus } from '../types/validation';

/** Props for the ValidationProgress component */
export interface ValidationProgressProps {
  /** Current job status */
  status: JobStatus;
  /** Progress message from the API (e.g., "Processing specification 3 of 13") */
  progressMessage?: string | null;
  /** Timestamp when the job was created */
  createdAt?: string;
  /** Timestamp when the job started processing */
  startedAt?: string | null;
  /** Callback to cancel validation (optional) */
  onCancel?: () => void;
}

/**
 * Format elapsed time in human-readable format
 */
function formatElapsedTime(seconds: number): string {
  if (seconds < 60) {
    return `${Math.floor(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

/**
 * Get status message based on job status
 */
function getStatusMessage(status: JobStatus): string {
  switch (status) {
    case 'pending':
      return 'Waiting in queue...';
    case 'processing':
      return 'Validating...';
    case 'completed':
      return 'Validation completed';
    case 'failed':
      return 'Validation failed';
    default:
      return 'Processing...';
  }
}

/**
 * Get status icon based on job status
 */
function getStatusIcon(status: JobStatus): string {
  switch (status) {
    case 'pending':
      return '⏳';
    case 'processing':
      return '⚙️';
    case 'completed':
      return '✅';
    case 'failed':
      return '❌';
    default:
      return '⏳';
  }
}

/**
 * ValidationProgress component showing validation status with spinner and elapsed time
 */
export function ValidationProgress({
  status,
  progressMessage,
  createdAt,
  startedAt,
  onCancel,
}: ValidationProgressProps) {
  const [elapsedTime, setElapsedTime] = useState<number>(0);

  /**
   * Calculate elapsed time from start timestamp
   */
  const calculateElapsedTime = useCallback(() => {
    // Use startedAt if processing, otherwise use createdAt
    const referenceTime = startedAt || createdAt;
    if (!referenceTime) return 0;

    const startTime = new Date(referenceTime).getTime();
    const now = Date.now();
    return (now - startTime) / 1000; // Convert to seconds
  }, [createdAt, startedAt]);

  /**
   * Update elapsed time every second while in progress
   */
  useEffect(() => {
    // Only update elapsed time while job is in progress
    if (status === 'completed' || status === 'failed') {
      return;
    }

    // Initial calculation
    setElapsedTime(calculateElapsedTime());

    // Update every second
    const intervalId = setInterval(() => {
      setElapsedTime(calculateElapsedTime());
    }, 1000);

    // Cleanup on unmount or when status changes
    return () => clearInterval(intervalId);
  }, [status, calculateElapsedTime]);

  // Determine if job is in progress (show spinner)
  const isInProgress = status === 'pending' || status === 'processing';

  // Determine CSS classes
  const containerClasses = [
    'validation-progress',
    `validation-progress--${status}`,
  ].join(' ');

  return (
    <div className={containerClasses} role="status" aria-live="polite">
      {/* Spinner and icon */}
      <div className="progress-indicator">
        {isInProgress ? (
          <div className="progress-spinner" aria-hidden="true">
            <div className="spinner-ring" />
          </div>
        ) : (
          <span className="progress-icon" aria-hidden="true">
            {getStatusIcon(status)}
          </span>
        )}
      </div>

      {/* Status content */}
      <div className="progress-content">
        {/* Status message */}
        <div className="progress-status">
          <span className="status-label">{getStatusMessage(status)}</span>
          {elapsedTime > 0 && isInProgress && (
            <span className="elapsed-time">
              {formatElapsedTime(elapsedTime)}
            </span>
          )}
        </div>

        {/* Progress message from API */}
        {progressMessage && (
          <div className="progress-message">{progressMessage}</div>
        )}

        {/* Additional status indicators */}
        {status === 'pending' && (
          <div className="progress-hint">
            Your validation will start shortly...
          </div>
        )}
      </div>

      {/* Cancel button (only if callback provided and in progress) */}
      {isInProgress && onCancel && (
        <button
          type="button"
          className="progress-cancel-btn"
          onClick={onCancel}
          aria-label="Cancel validation"
        >
          Cancel
        </button>
      )}

      {/* Styles */}
      <style>{`
        .validation-progress {
          display: flex;
          align-items: flex-start;
          gap: var(--spacing-md);
          padding: var(--spacing-lg);
          background-color: var(--color-surface);
          border-radius: var(--radius-lg);
          border: 1px solid var(--color-border);
        }

        .validation-progress--pending {
          border-color: var(--color-warning);
          background-color: rgba(239, 189, 117, 0.1);
        }

        .validation-progress--processing {
          border-color: var(--color-primary);
          background-color: rgba(68, 182, 168, 0.1);
        }

        .validation-progress--completed {
          border-color: var(--color-success);
          background-color: rgba(68, 182, 168, 0.15);
        }

        .validation-progress--failed {
          border-color: var(--color-error);
          background-color: rgba(219, 76, 64, 0.1);
        }

        /* Progress indicator (spinner or icon) */
        .progress-indicator {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 48px;
          height: 48px;
          min-width: 48px;
        }

        /* Spinner animation */
        .progress-spinner {
          position: relative;
          width: 40px;
          height: 40px;
        }

        .spinner-ring {
          position: absolute;
          width: 100%;
          height: 100%;
          border: 4px solid var(--color-border);
          border-top-color: var(--color-primary);
          border-radius: var(--radius-full);
          animation: spin 1s linear infinite;
        }

        .validation-progress--pending .spinner-ring {
          border-top-color: var(--color-warning);
        }

        @keyframes spin {
          0% {
            transform: rotate(0deg);
          }
          100% {
            transform: rotate(360deg);
          }
        }

        /* Status icon (for completed/failed states) */
        .progress-icon {
          font-size: var(--font-size-2xl);
          line-height: 1;
        }

        /* Content area */
        .progress-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: var(--spacing-xs);
          min-width: 0;
        }

        /* Status line with label and elapsed time */
        .progress-status {
          display: flex;
          align-items: center;
          gap: var(--spacing-md);
          flex-wrap: wrap;
        }

        .status-label {
          font-size: var(--font-size-lg);
          font-weight: 600;
          color: var(--color-text);
        }

        .validation-progress--pending .status-label {
          color: var(--color-warning-dark, #c99a40);
        }

        .validation-progress--processing .status-label {
          color: var(--color-primary);
        }

        .validation-progress--completed .status-label {
          color: var(--color-success);
        }

        .validation-progress--failed .status-label {
          color: var(--color-error);
        }

        /* Elapsed time */
        .elapsed-time {
          font-size: var(--font-size-sm);
          color: var(--color-text-secondary);
          padding: var(--spacing-xs) var(--spacing-sm);
          background-color: var(--color-background);
          border-radius: var(--radius-sm);
          font-variant-numeric: tabular-nums;
        }

        /* Progress message from API */
        .progress-message {
          font-size: var(--font-size-base);
          color: var(--color-text);
          padding: var(--spacing-sm) var(--spacing-md);
          background-color: var(--color-background);
          border-radius: var(--radius-sm);
          border-left: 3px solid var(--color-primary);
        }

        .validation-progress--pending .progress-message {
          border-left-color: var(--color-warning);
        }

        /* Hint text */
        .progress-hint {
          font-size: var(--font-size-sm);
          color: var(--color-text-secondary);
          font-style: italic;
        }

        /* Cancel button */
        .progress-cancel-btn {
          padding: var(--spacing-sm) var(--spacing-md);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          background-color: var(--color-surface);
          color: var(--color-text-secondary);
          font-size: var(--font-size-sm);
          font-weight: 500;
          cursor: pointer;
          transition: all var(--transition-fast);
          white-space: nowrap;
        }

        .progress-cancel-btn:hover {
          border-color: var(--color-error);
          color: var(--color-error);
          background-color: rgba(219, 76, 64, 0.1);
        }

        .progress-cancel-btn:focus-visible {
          outline: 2px solid var(--color-primary);
          outline-offset: 2px;
        }

        /* Responsive adjustments */
        @media (max-width: 480px) {
          .validation-progress {
            flex-direction: column;
            align-items: stretch;
            text-align: center;
          }

          .progress-indicator {
            align-self: center;
          }

          .progress-status {
            justify-content: center;
          }

          .progress-message {
            border-left: none;
            border-top: 3px solid var(--color-primary);
          }

          .validation-progress--pending .progress-message {
            border-top-color: var(--color-warning);
          }

          .progress-cancel-btn {
            align-self: center;
          }
        }

        /* Reduced motion preference */
        @media (prefers-reduced-motion: reduce) {
          .spinner-ring {
            animation-duration: 2s;
          }
        }
      `}</style>
    </div>
  );
}

export default ValidationProgress;
