/**
 * App Component
 *
 * Main application component that orchestrates the IFC validation flow:
 * - File upload (IFC file selection)
 * - IDS standard selection or custom IDS file upload
 * - Validation submission to backend API
 * - Polling for job status every 2 seconds
 * - Display of validation results or errors
 */

import { useState, useEffect, useCallback, useRef } from 'react';

// Components
import FileUpload from './components/FileUpload';
import IdsSelector, { type IdsSelection } from './components/IdsSelector';
import ValidationProgress from './components/ValidationProgress';
import ErrorDisplay from './components/ErrorDisplay';
import ResultsSummary from './components/ResultsSummary';
import SpecificationList from './components/SpecificationList';

// API client
import {
  submitValidation,
  pollJobStatus,
  isJobFinished,
  isJobSuccessful,
  isJobFailed,
  ApiError,
} from './api/client';

// Types
import type { JobStatusResponse, ValidationResult } from './types/validation';

/** Polling interval in milliseconds */
const POLLING_INTERVAL = 2000;

/** Application state phases */
type AppPhase = 'idle' | 'submitting' | 'polling' | 'completed' | 'error';

/**
 * Main App component
 */
export function App() {
  // File state
  const [ifcFile, setIfcFile] = useState<File | null>(null);
  const [idsSelection, setIdsSelection] = useState<IdsSelection | null>({
    type: 'standard',
    standard: 'nl-bim',
  });

  // Job state
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);

  // Result state
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);

  // Error state
  const [error, setError] = useState<{ message: string; details?: string } | null>(null);

  // App phase
  const [phase, setPhase] = useState<AppPhase>('idle');

  // Polling interval ref (to clean up on unmount)
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /**
   * Clean up polling interval
   */
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  /**
   * Handle IFC file selection
   */
  const handleIfcFileSelect = useCallback((file: File) => {
    setIfcFile(file);
    setError(null);
  }, []);

  /**
   * Handle IFC file clear
   */
  const handleIfcFileClear = useCallback(() => {
    setIfcFile(null);
  }, []);

  /**
   * Handle IDS selection change
   */
  const handleIdsSelectionChange = useCallback((selection: IdsSelection | null) => {
    setIdsSelection(selection);
    setError(null);
  }, []);

  /**
   * Poll job status
   */
  const pollStatus = useCallback(async (id: string) => {
    try {
      const status = await pollJobStatus(id);
      setJobStatus(status);

      // Check if job is finished
      if (isJobFinished(status)) {
        stopPolling();

        if (isJobSuccessful(status) && status.result) {
          setValidationResult(status.result);
          setPhase('completed');
        } else if (isJobFailed(status)) {
          setError({
            message: status.error || 'Validation failed',
            details: 'The validation job encountered an error during processing.',
          });
          setPhase('error');
        }
      }
    } catch (err) {
      stopPolling();

      const errorMessage =
        err instanceof ApiError
          ? err.message
          : 'Failed to check job status. Please try again.';

      setError({
        message: errorMessage,
        details: err instanceof Error ? err.message : undefined,
      });
      setPhase('error');
    }
  }, [stopPolling]);

  /**
   * Start polling for job status
   */
  const startPolling = useCallback(
    (id: string) => {
      // Stop any existing polling
      stopPolling();

      // Poll immediately
      pollStatus(id);

      // Then poll every POLLING_INTERVAL
      pollingIntervalRef.current = setInterval(() => {
        pollStatus(id);
      }, POLLING_INTERVAL);
    },
    [stopPolling, pollStatus]
  );

  /**
   * Submit validation request
   */
  const handleSubmit = useCallback(async () => {
    // Validate inputs
    if (!ifcFile) {
      setError({
        message: 'Please select an IFC file to validate.',
      });
      return;
    }

    if (!idsSelection) {
      setError({
        message: 'Please select an IDS standard or upload a custom IDS file.',
      });
      return;
    }

    // Clear previous state
    setError(null);
    setValidationResult(null);
    setJobStatus(null);
    setJobId(null);
    setPhase('submitting');

    try {
      // Prepare submission parameters
      const idsStandard = idsSelection.type === 'standard' ? idsSelection.standard : undefined;
      const idsFile = idsSelection.type === 'custom' ? idsSelection.file : undefined;

      // Submit validation
      const response = await submitValidation(ifcFile, idsStandard, idsFile);

      // Store job ID and start polling
      setJobId(response.job_id);
      setPhase('polling');
      startPolling(response.job_id);
    } catch (err) {
      const errorMessage =
        err instanceof ApiError
          ? err.message
          : 'Failed to submit validation. Please try again.';

      setError({
        message: errorMessage,
        details: err instanceof Error ? err.message : undefined,
      });
      setPhase('error');
    }
  }, [ifcFile, idsSelection, startPolling]);

  /**
   * Cancel validation (stop polling)
   */
  const handleCancel = useCallback(() => {
    stopPolling();
    setPhase('idle');
    setJobId(null);
    setJobStatus(null);
  }, [stopPolling]);

  /**
   * Reset to initial state
   */
  const handleReset = useCallback(() => {
    stopPolling();
    setPhase('idle');
    setIfcFile(null);
    setIdsSelection({ type: 'standard', standard: 'nl-bim' });
    setJobId(null);
    setJobStatus(null);
    setValidationResult(null);
    setError(null);
  }, [stopPolling]);

  /**
   * Retry validation
   */
  const handleRetry = useCallback(() => {
    setError(null);
    setValidationResult(null);
    setJobStatus(null);
    setJobId(null);
    setPhase('idle');
  }, []);

  /**
   * Dismiss error
   */
  const handleDismissError = useCallback(() => {
    setError(null);
    if (phase === 'error') {
      setPhase('idle');
    }
  }, [phase]);

  /**
   * Download results as JSON
   */
  const handleDownloadJson = useCallback(() => {
    if (!validationResult) return;

    const jsonString = JSON.stringify(validationResult, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `validation-results-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [validationResult]);

  /**
   * Clean up polling on unmount
   */
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  // Determine if validation can be submitted
  const canSubmit =
    ifcFile !== null &&
    idsSelection !== null &&
    (phase === 'idle' || phase === 'error' || phase === 'completed');

  // Determine if inputs should be disabled
  const inputsDisabled = phase === 'submitting' || phase === 'polling';

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="header-logo" aria-hidden="true">
            <span className="logo-icon">&#x1F3D7;</span>
          </div>
          <div className="header-title">
            <h1 className="app-title">3BM IFC Validator</h1>
            <p className="app-subtitle">Validate IFC files against IDS standards</p>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="app-main">
        {/* Input section */}
        <section className="input-section" aria-label="Upload and configuration">
          {/* IFC File Upload */}
          <FileUpload
            onFileSelect={handleIfcFileSelect}
            onFileClear={handleIfcFileClear}
            disabled={inputsDisabled}
            label="IFC File"
          />

          {/* IDS Selection */}
          <IdsSelector
            onSelectionChange={handleIdsSelectionChange}
            disabled={inputsDisabled}
          />

          {/* Submit button */}
          <div className="submit-section">
            <button
              type="button"
              className="submit-btn"
              onClick={handleSubmit}
              disabled={!canSubmit || inputsDisabled}
              aria-busy={phase === 'submitting'}
            >
              {phase === 'submitting' ? (
                <>
                  <span className="btn-spinner" aria-hidden="true" />
                  Submitting...
                </>
              ) : (
                <>
                  <span className="btn-icon" aria-hidden="true">&#x2713;</span>
                  Validate
                </>
              )}
            </button>

            {(phase === 'completed' || validationResult) && (
              <button
                type="button"
                className="reset-btn"
                onClick={handleReset}
                aria-label="Start new validation"
              >
                New Validation
              </button>
            )}
          </div>
        </section>

        {/* Error display */}
        {error && (
          <section className="error-section" aria-label="Error">
            <ErrorDisplay
              message={error.message}
              details={error.details}
              type={
                error.message.toLowerCase().includes('network')
                  ? 'network'
                  : error.message.toLowerCase().includes('upload')
                  ? 'upload'
                  : 'validation'
              }
              onRetry={handleRetry}
              onDismiss={handleDismissError}
            />
          </section>
        )}

        {/* Progress indicator */}
        {(phase === 'polling' || phase === 'submitting') && jobStatus && (
          <section className="progress-section" aria-label="Validation progress">
            <ValidationProgress
              status={jobStatus.status}
              progressMessage={jobStatus.progress}
              createdAt={jobStatus.created_at}
              startedAt={jobStatus.started_at}
              onCancel={handleCancel}
            />
          </section>
        )}

        {/* Submitting state without job status yet */}
        {phase === 'submitting' && !jobStatus && (
          <section className="progress-section" aria-label="Validation progress">
            <div className="submitting-indicator" role="status" aria-live="polite">
              <div className="submitting-spinner" aria-hidden="true">
                <div className="spinner-ring" />
              </div>
              <span className="submitting-text">Uploading files and starting validation...</span>
            </div>
          </section>
        )}

        {/* Results section */}
        {validationResult && (
          <section className="results-section" aria-label="Validation results">
            <ResultsSummary
              result={validationResult}
              onDownloadJson={handleDownloadJson}
            />

            {validationResult.specifications.length > 0 && (
              <div className="specifications-container">
                <h2 className="specifications-heading">Specifications</h2>
                <SpecificationList
                  specifications={validationResult.specifications}
                  autoExpandFailed={true}
                />
              </div>
            )}
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p className="footer-text">
          &copy; {new Date().getFullYear()} 3BM &mdash; IFC Validator powered by{' '}
          <a
            href="https://github.com/IfcOpenShell/IfcOpenShell"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-link"
          >
            IfcOpenShell
          </a>
        </p>
      </footer>

      {/* Styles */}
      <style>{`
        .app {
          display: flex;
          flex-direction: column;
          min-height: 100vh;
          background-color: var(--color-background);
        }

        /* Header */
        .app-header {
          background-color: var(--magic-violet);
          color: var(--color-text-light);
          padding: var(--spacing-lg) var(--spacing-xl);
          box-shadow: var(--shadow-md);
        }

        .header-content {
          display: flex;
          align-items: center;
          gap: var(--spacing-md);
          max-width: 1200px;
          margin: 0 auto;
        }

        .header-logo {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 48px;
          height: 48px;
          background-color: var(--verdigris);
          border-radius: var(--radius-md);
        }

        .logo-icon {
          font-size: var(--font-size-2xl);
          line-height: 1;
        }

        .header-title {
          flex: 1;
        }

        .app-title {
          margin: 0;
          font-size: var(--font-size-xl);
          font-weight: 700;
          color: var(--color-text-light);
        }

        .app-subtitle {
          margin: var(--spacing-xs) 0 0;
          font-size: var(--font-size-sm);
          color: rgba(255, 255, 255, 0.8);
        }

        /* Main content */
        .app-main {
          flex: 1;
          padding: var(--spacing-xl);
          max-width: 1200px;
          width: 100%;
          margin: 0 auto;
          box-sizing: border-box;
        }

        /* Input section */
        .input-section {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-xl);
          background-color: var(--color-surface);
          padding: var(--spacing-xl);
          border-radius: var(--radius-lg);
          border: 1px solid var(--color-border);
          box-shadow: var(--shadow-sm);
        }

        /* Submit section */
        .submit-section {
          display: flex;
          align-items: center;
          gap: var(--spacing-md);
          padding-top: var(--spacing-md);
          border-top: 1px solid var(--color-border);
        }

        .submit-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: var(--spacing-sm);
          padding: var(--spacing-md) var(--spacing-2xl);
          background-color: var(--color-primary);
          color: var(--color-text-light);
          border: none;
          border-radius: var(--radius-md);
          font-size: var(--font-size-lg);
          font-weight: 600;
          cursor: pointer;
          transition: all var(--transition-fast);
          min-height: 48px;
        }

        .submit-btn:hover:not(:disabled) {
          background-color: #3a9e92;
          transform: translateY(-1px);
          box-shadow: var(--shadow-md);
        }

        .submit-btn:active:not(:disabled) {
          transform: translateY(0);
        }

        .submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .submit-btn:focus-visible {
          outline: 2px solid var(--color-primary);
          outline-offset: 2px;
        }

        .btn-icon {
          font-size: var(--font-size-lg);
        }

        .btn-spinner {
          width: 20px;
          height: 20px;
          border: 3px solid rgba(255, 255, 255, 0.3);
          border-top-color: var(--color-text-light);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        .reset-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          padding: var(--spacing-md) var(--spacing-lg);
          background-color: transparent;
          color: var(--color-text-secondary);
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          font-size: var(--font-size-base);
          font-weight: 500;
          cursor: pointer;
          transition: all var(--transition-fast);
          min-height: 48px;
        }

        .reset-btn:hover {
          border-color: var(--color-primary);
          color: var(--color-primary);
          background-color: var(--color-hover);
        }

        .reset-btn:focus-visible {
          outline: 2px solid var(--color-primary);
          outline-offset: 2px;
        }

        /* Progress and error sections */
        .error-section,
        .progress-section {
          margin-top: var(--spacing-xl);
        }

        /* Submitting indicator */
        .submitting-indicator {
          display: flex;
          align-items: center;
          gap: var(--spacing-md);
          padding: var(--spacing-lg);
          background-color: var(--color-surface);
          border-radius: var(--radius-lg);
          border: 1px solid var(--color-primary);
        }

        .submitting-spinner {
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
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% {
            transform: rotate(0deg);
          }
          100% {
            transform: rotate(360deg);
          }
        }

        .submitting-text {
          font-size: var(--font-size-base);
          color: var(--color-text);
        }

        /* Results section */
        .results-section {
          margin-top: var(--spacing-xl);
          display: flex;
          flex-direction: column;
          gap: var(--spacing-xl);
        }

        .specifications-container {
          background-color: var(--color-surface);
          padding: var(--spacing-lg);
          border-radius: var(--radius-lg);
          border: 1px solid var(--color-border);
          box-shadow: var(--shadow-sm);
        }

        .specifications-heading {
          margin: 0 0 var(--spacing-lg);
          font-size: var(--font-size-lg);
          font-weight: 600;
          color: var(--color-text);
        }

        /* Footer */
        .app-footer {
          background-color: var(--color-surface);
          border-top: 1px solid var(--color-border);
          padding: var(--spacing-lg) var(--spacing-xl);
          text-align: center;
        }

        .footer-text {
          margin: 0;
          font-size: var(--font-size-sm);
          color: var(--color-text-secondary);
        }

        .footer-link {
          color: var(--color-primary);
          text-decoration: none;
        }

        .footer-link:hover {
          text-decoration: underline;
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
          .app-header {
            padding: var(--spacing-md);
          }

          .header-logo {
            width: 40px;
            height: 40px;
          }

          .logo-icon {
            font-size: var(--font-size-xl);
          }

          .app-title {
            font-size: var(--font-size-lg);
          }

          .app-main {
            padding: var(--spacing-md);
          }

          .input-section {
            padding: var(--spacing-md);
          }

          .submit-section {
            flex-direction: column;
          }

          .submit-btn,
          .reset-btn {
            width: 100%;
          }
        }

        @media (max-width: 480px) {
          .header-content {
            flex-direction: column;
            text-align: center;
          }

          .app-subtitle {
            display: none;
          }

          .specifications-container {
            padding: var(--spacing-md);
          }
        }

        /* Reduced motion */
        @media (prefers-reduced-motion: reduce) {
          .btn-spinner,
          .spinner-ring {
            animation-duration: 2s;
          }

          .submit-btn:hover:not(:disabled) {
            transform: none;
          }
        }
      `}</style>
    </div>
  );
}

export default App;
