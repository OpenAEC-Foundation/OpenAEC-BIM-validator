import { Button as OaButton } from "@openaec/ui-react";
/**
 * IdsSelector Component
 *
 * Radio button selector for IDS standards: NL BIM Basis ILS, RVB BIM Norm, Custom IDS.
 * Custom option shows a file upload zone for .ids files.
 */

import { useState, useRef, useCallback } from 'react';
import type { IdsStandard } from '../types/validation';

/** Maximum IDS file size in bytes (10MB) */
const MAX_IDS_FILE_SIZE = 10 * 1024 * 1024;

/** Maximum file size for display */
const MAX_IDS_FILE_SIZE_DISPLAY = '10 MB';

/** Accepted file extension for IDS files */
const ACCEPTED_IDS_EXTENSION = '.ids';

/** Selection options for IDS standard */
export type IdsSelection =
  | { type: 'standard'; standard: IdsStandard }
  | { type: 'custom'; file: File };

/** Radio option configuration */
interface IdsOption {
  value: 'nl-bim' | 'rvb' | 'custom';
  label: string;
  description: string;
}

/** Available IDS options */
const IDS_OPTIONS: IdsOption[] = [
  {
    value: 'nl-bim',
    label: 'NL BIM Basis ILS',
    description: 'Dutch BIM Base Information Level Specification',
  },
  {
    value: 'rvb',
    label: 'RVB BIM Norm',
    description: 'Rijksvastgoedbedrijf BIM Standard',
  },
  {
    value: 'custom',
    label: 'Custom IDS',
    description: 'Upload your own IDS file',
  },
];

/** Props for the IdsSelector component */
export interface IdsSelectorProps {
  /** Callback when selection changes (standard or custom file) */
  onSelectionChange: (selection: IdsSelection | null) => void;
  /** Whether the selector is disabled (e.g., during validation) */
  disabled?: boolean;
}

/**
 * Format file size for display
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Validate file extension
 */
function hasValidExtension(file: File, extension: string): boolean {
  const fileName = file.name.toLowerCase();
  return fileName.endsWith(extension.toLowerCase());
}

/**
 * IdsSelector component with radio buttons and optional file upload
 */
export function IdsSelector({
  onSelectionChange,
  disabled = false,
}: IdsSelectorProps) {
  const [selectedOption, setSelectedOption] = useState<
    'nl-bim' | 'rvb' | 'custom'
  >('nl-bim');
  const [customFile, setCustomFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /**
   * Handle radio button change
   */
  const handleOptionChange = useCallback(
    (value: 'nl-bim' | 'rvb' | 'custom') => {
      if (disabled) return;

      setSelectedOption(value);
      setError(null);

      if (value === 'custom') {
        // For custom, only emit when file is selected
        if (customFile) {
          onSelectionChange({ type: 'custom', file: customFile });
        } else {
          onSelectionChange(null);
        }
      } else {
        // For standard options, emit immediately
        onSelectionChange({ type: 'standard', standard: value });
      }
    },
    [disabled, customFile, onSelectionChange]
  );

  /**
   * Validate and process selected IDS file
   */
  const processFile = useCallback(
    (file: File) => {
      setError(null);

      // Validate file extension
      if (!hasValidExtension(file, ACCEPTED_IDS_EXTENSION)) {
        setError(
          `Invalid file type. Please select a ${ACCEPTED_IDS_EXTENSION} file.`
        );
        return;
      }

      // Validate file size
      if (file.size > MAX_IDS_FILE_SIZE) {
        setError(
          `File is too large. Maximum size is ${MAX_IDS_FILE_SIZE_DISPLAY}.`
        );
        return;
      }

      // File is valid
      setCustomFile(file);
      onSelectionChange({ type: 'custom', file });
    },
    [onSelectionChange]
  );

  /**
   * Handle drag over event
   */
  const handleDragOver = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled && selectedOption === 'custom') {
        setIsDragOver(true);
      }
    },
    [disabled, selectedOption]
  );

  /**
   * Handle drag leave event
   */
  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  /**
   * Handle file drop
   */
  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);

      if (disabled || selectedOption !== 'custom') return;

      const file = e.dataTransfer.files[0];
      if (file) {
        processFile(file);
      }
    },
    [disabled, selectedOption, processFile]
  );

  /**
   * Handle file input change
   */
  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        processFile(file);
      }
    },
    [processFile]
  );

  /**
   * Handle click on upload zone
   */
  const handleUploadClick = useCallback(() => {
    if (!disabled && selectedOption === 'custom' && fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, [disabled, selectedOption]);

  /**
   * Handle keyboard activation on upload zone
   */
  const handleUploadKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (
        (e.key === 'Enter' || e.key === ' ') &&
        !disabled &&
        selectedOption === 'custom'
      ) {
        e.preventDefault();
        fileInputRef.current?.click();
      }
    },
    [disabled, selectedOption]
  );

  /**
   * Clear selected custom file
   */
  const handleClearFile = useCallback(
    (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();
      setCustomFile(null);
      setError(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      // Emit null since custom is selected but no file
      onSelectionChange(null);
    },
    [onSelectionChange]
  );

  // Determine upload zone classes
  const uploadZoneClasses = [
    'ids-upload-zone',
    isDragOver ? 'ids-upload-zone--drag-over' : '',
    disabled ? 'ids-upload-zone--disabled' : '',
    customFile ? 'ids-upload-zone--has-file' : '',
    error ? 'ids-upload-zone--error' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className="ids-selector">
      {/* Label */}
      <label className="ids-selector-label">IDS Standard</label>

      {/* Radio options */}
      <div
        className="ids-options"
        role="radiogroup"
        aria-label="IDS Standard Selection"
      >
        {IDS_OPTIONS.map((option) => (
          <label
            key={option.value}
            className={`ids-option ${
              selectedOption === option.value ? 'ids-option--selected' : ''
            } ${disabled ? 'ids-option--disabled' : ''}`}
          >
            <input
              type="radio"
              name="ids-standard"
              value={option.value}
              checked={selectedOption === option.value}
              onChange={() => handleOptionChange(option.value)}
              disabled={disabled}
              className="ids-option-radio"
            />
            <span className="ids-option-indicator" />
            <div className="ids-option-content">
              <span className="ids-option-label">{option.label}</span>
              <span className="ids-option-description">{option.description}</span>
            </div>
          </label>
        ))}
      </div>

      {/* Custom file upload zone (visible when Custom IDS is selected) */}
      {selectedOption === 'custom' && (
        <div className="ids-custom-upload">
          <div
            className={uploadZoneClasses}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleUploadClick}
            onKeyDown={handleUploadKeyDown}
            role="button"
            tabIndex={disabled ? -1 : 0}
            aria-label="Drop IDS file here or click to browse"
            aria-disabled={disabled}
          >
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_IDS_EXTENSION}
              onChange={handleFileChange}
              disabled={disabled}
              className="ids-upload-input"
              aria-hidden="true"
            />

            {customFile ? (
              /* File selected state */
              <div className="ids-upload-selected">
                <span className="ids-upload-icon" aria-hidden="true">
                  &#x2705;
                </span>
                <div className="ids-file-info">
                  <span className="ids-file-name">{customFile.name}</span>
                  <span className="ids-file-size">
                    ({formatFileSize(customFile.size)})
                  </span>
                </div>
                {!disabled && (
                  <OaButton kind="quiet"
                    type="button"
                    className="ids-file-clear-btn"
                    onClick={handleClearFile}
                    aria-label="Clear selected IDS file"
                  >
                    &#x2715;
                  </OaButton>
                )}
              </div>
            ) : (
              /* Empty state */
              <div className="ids-upload-empty">
                <span className="ids-upload-icon" aria-hidden="true">
                  &#x1F4C4;
                </span>
                <span className="ids-upload-text">
                  Drop {ACCEPTED_IDS_EXTENSION} file here or{' '}
                  <span className="ids-upload-link">click to browse</span>
                </span>
                <span className="ids-upload-hint">
                  Maximum file size: {MAX_IDS_FILE_SIZE_DISPLAY}
                </span>
              </div>
            )}
          </div>

          {/* Error message */}
          {error && (
            <div className="ids-upload-error" role="alert">
              {error}
            </div>
          )}
        </div>
      )}

      {/* Styles */}
      <style>{`
        .ids-selector {
          display: flex;
          flex-direction: column;
          gap: var(--oa-space-lg);
        }

        .ids-selector-label {
          font-size: var(--oa-size-body);
          font-weight: 600;
          color: var(--oa-text);
        }

        .ids-options {
          display: flex;
          flex-direction: column;
          gap: var(--oa-space-sm);
        }

        @media (min-width: 768px) {
          .ids-options {
            flex-direction: row;
            gap: var(--oa-space-lg);
          }
        }

        .ids-option {
          display: flex;
          align-items: flex-start;
          gap: var(--oa-space-sm);
          padding: var(--oa-space-lg);
          border: 2px solid var(--oa-border);
          border-radius: var(--oa-radius-medium);
          background-color: var(--oa-panel);
          cursor: pointer;
          transition: border-color var(--transition-fast),
            background-color var(--transition-fast);
          flex: 1;
        }

        .ids-option:hover:not(.ids-option--disabled) {
          border-color: var(--oa-accent);
          background-color: var(--oa-hover);
        }

        .ids-option--selected {
          border-color: var(--oa-accent);
          background-color: var(--oa-hover);
        }

        .ids-option--disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .ids-option-radio {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0, 0, 0, 0);
          white-space: nowrap;
          border: 0;
        }

        .ids-option-indicator {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 20px;
          height: 20px;
          min-width: 20px;
          border: 2px solid var(--oa-border);
          border-radius: var(--oa-radius-full);
          background-color: var(--oa-panel);
          transition: border-color var(--transition-fast),
            background-color var(--transition-fast);
          margin-top: 2px;
        }

        .ids-option-radio:checked + .ids-option-indicator {
          border-color: var(--oa-accent);
          background-color: var(--oa-accent);
        }

        .ids-option-radio:checked + .ids-option-indicator::after {
          content: '';
          display: block;
          width: 8px;
          height: 8px;
          border-radius: var(--oa-radius-full);
          background-color: var(--oa-text-on-accent);
        }

        .ids-option-radio:focus-visible + .ids-option-indicator {
          outline: 2px solid var(--oa-accent);
          outline-offset: 2px;
        }

        .ids-option-content {
          display: flex;
          flex-direction: column;
          gap: var(--oa-space-xs);
        }

        .ids-option-label {
          font-weight: 600;
          color: var(--oa-text);
          font-size: var(--oa-size-body);
        }

        .ids-option-description {
          font-size: var(--oa-size-body);
          color: var(--oa-text-secondary);
        }

        /* Custom Upload Zone */
        .ids-custom-upload {
          display: flex;
          flex-direction: column;
          gap: var(--oa-space-sm);
          margin-top: var(--oa-space-sm);
          padding-left: var(--oa-space-lg);
          border-left: 3px solid var(--oa-accent);
        }

        .ids-upload-zone {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: var(--oa-space-xl);
          min-height: 100px;
          border: 2px dashed var(--oa-border);
          border-radius: var(--oa-radius-medium);
          background-color: var(--oa-panel);
          cursor: pointer;
          transition: border-color var(--transition-fast),
            background-color var(--transition-fast);
        }

        .ids-upload-zone:hover:not(.ids-upload-zone--disabled) {
          border-color: var(--oa-accent);
          background-color: var(--oa-hover);
        }

        .ids-upload-zone:focus-visible {
          outline: 2px solid var(--oa-accent);
          outline-offset: 2px;
        }

        .ids-upload-zone--drag-over {
          border-color: var(--oa-accent);
          background-color: var(--oa-accent);
          border-style: solid;
        }

        .ids-upload-zone--has-file {
          border-color: var(--oa-success);
          border-style: solid;
        }

        .ids-upload-zone--error {
          border-color: var(--oa-error);
        }

        .ids-upload-zone--disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .ids-upload-input {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0, 0, 0, 0);
          white-space: nowrap;
          border: 0;
        }

        .ids-upload-empty,
        .ids-upload-selected {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: var(--oa-space-xs);
          text-align: center;
        }

        .ids-upload-selected {
          flex-direction: row;
          gap: var(--oa-space-lg);
        }

        .ids-upload-icon {
          font-size: var(--oa-size-page-heading);
          line-height: 1;
        }

        .ids-upload-text {
          font-size: var(--oa-size-body);
          color: var(--oa-text);
        }

        .ids-upload-link {
          color: var(--oa-accent);
          text-decoration: underline;
          font-weight: 500;
        }

        .ids-upload-hint {
          font-size: var(--oa-size-label);
          color: var(--oa-text-secondary);
        }

        .ids-file-info {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: var(--oa-space-xs);
        }

        .ids-file-name {
          font-weight: 600;
          color: var(--oa-text);
          word-break: break-all;
          font-size: var(--oa-size-body);
        }

        .ids-file-size {
          font-size: var(--oa-size-label);
          color: var(--oa-text-secondary);
        }

        .ids-file-clear-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
          padding: 0;
          border: none;
          border-radius: var(--oa-radius-full);
          background-color: var(--oa-border);
          color: var(--oa-text);
          cursor: pointer;
          transition: background-color var(--transition-fast);
        }

        .ids-file-clear-btn:hover {
          background-color: var(--oa-error);
          color: var(--oa-text-on-accent);
        }

        .ids-upload-error {
          padding: var(--oa-space-sm) var(--oa-space-lg);
          background-color: rgba(219, 76, 64, 0.1);
          border-radius: var(--oa-radius-small);
          color: var(--oa-error);
          font-size: var(--oa-size-body);
        }
      `}</style>
    </div>
  );
}

export default IdsSelector;
