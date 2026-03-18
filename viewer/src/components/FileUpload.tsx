/**
 * FileUpload Component
 *
 * Drag-and-drop file upload component with file picker fallback.
 * - Validates .ifc extension
 * - Shows file name and size
 * - Max 500MB file size indicator
 */

import { useState, useRef, useCallback } from 'react';

/** Maximum file size in bytes (500MB) */
const MAX_FILE_SIZE = 500 * 1024 * 1024;

/** Maximum file size for display */
const MAX_FILE_SIZE_DISPLAY = '500 MB';

/** Accepted file extension */
const ACCEPTED_EXTENSION = '.ifc';

/** Props for the FileUpload component */
export interface FileUploadProps {
  /** Callback when a valid file is selected */
  onFileSelect: (file: File) => void;
  /** Callback when file is cleared */
  onFileClear?: () => void;
  /** Whether the upload is disabled (e.g., during validation) */
  disabled?: boolean;
  /** Optional label text */
  label?: string;
  /** Accepted file extension (defaults to .ifc) */
  accept?: string;
  /** Maximum file size in bytes (defaults to 500MB) */
  maxSize?: number;
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
 * FileUpload component with drag-and-drop and file picker
 */
export function FileUpload({
  onFileSelect,
  onFileClear,
  disabled = false,
  label = 'IFC File',
  accept = ACCEPTED_EXTENSION,
  maxSize = MAX_FILE_SIZE,
}: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /**
   * Validate and process selected file
   */
  const processFile = useCallback(
    (file: File) => {
      setError(null);

      // Validate file extension
      if (!hasValidExtension(file, accept)) {
        setError(`Invalid file type. Please select a ${accept} file.`);
        return;
      }

      // Validate file size
      if (file.size > maxSize) {
        setError(
          `File is too large. Maximum size is ${formatFileSize(maxSize)}.`
        );
        return;
      }

      // File is valid
      setSelectedFile(file);
      onFileSelect(file);
    },
    [accept, maxSize, onFileSelect]
  );

  /**
   * Handle drag over event
   */
  const handleDragOver = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) {
        setIsDragOver(true);
      }
    },
    [disabled]
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

      if (disabled) return;

      const file = e.dataTransfer.files[0];
      if (file) {
        processFile(file);
      }
    },
    [disabled, processFile]
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
  const handleClick = useCallback(() => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, [disabled]);

  /**
   * Handle keyboard activation
   */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
        e.preventDefault();
        fileInputRef.current?.click();
      }
    },
    [disabled]
  );

  /**
   * Clear selected file
   */
  const handleClear = useCallback(
    (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();
      setSelectedFile(null);
      setError(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      onFileClear?.();
    },
    [onFileClear]
  );

  // Determine zone classes
  const zoneClasses = [
    'file-upload-zone',
    isDragOver ? 'file-upload-zone--drag-over' : '',
    disabled ? 'file-upload-zone--disabled' : '',
    selectedFile ? 'file-upload-zone--has-file' : '',
    error ? 'file-upload-zone--error' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className="file-upload">
      {/* Label */}
      <label className="file-upload-label">{label}</label>

      {/* Drop Zone */}
      <div
        className={zoneClasses}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label={`Drop ${accept} file here or click to browse`}
        aria-disabled={disabled}
      >
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          onChange={handleFileChange}
          disabled={disabled}
          className="file-upload-input"
          aria-hidden="true"
        />

        {selectedFile ? (
          /* File selected state */
          <div className="file-upload-selected">
            <span className="upload-icon" aria-hidden="true">
              &#x2705;
            </span>
            <div className="file-info">
              <span className="file-name">{selectedFile.name}</span>
              <span className="file-size">
                ({formatFileSize(selectedFile.size)})
              </span>
            </div>
            {!disabled && (
              <button
                type="button"
                className="file-clear-btn"
                onClick={handleClear}
                aria-label="Clear selected file"
              >
                &#x2715;
              </button>
            )}
          </div>
        ) : (
          /* Empty state */
          <div className="file-upload-empty">
            <span className="upload-icon" aria-hidden="true">
              &#x1F4C1;
            </span>
            <span className="upload-text">
              Drop {accept} file here or{' '}
              <span className="upload-link">click to browse</span>
            </span>
            <span className="upload-hint">
              Maximum file size: {MAX_FILE_SIZE_DISPLAY}
            </span>
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="file-upload-error" role="alert">
          {error}
        </div>
      )}

      {/* File size indicator */}
      <div className="file-upload-meta">
        <span className="max-size-indicator">
          Max size: {MAX_FILE_SIZE_DISPLAY}
        </span>
      </div>

      {/* Styles */}
      <style>{`
        .file-upload {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-sm);
        }

        .file-upload-label {
          font-size: var(--font-size-base);
          font-weight: 600;
          color: var(--color-text);
        }

        .file-upload-zone {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: var(--spacing-xl) var(--spacing-lg);
          min-height: 150px;
          border: 2px dashed var(--color-border);
          border-radius: var(--radius-lg);
          background-color: var(--color-surface);
          cursor: pointer;
          transition: border-color var(--transition-fast),
            background-color var(--transition-fast);
        }

        .file-upload-zone:hover:not(.file-upload-zone--disabled) {
          border-color: var(--color-primary);
          background-color: var(--color-hover);
        }

        .file-upload-zone:focus-visible {
          outline: 2px solid var(--color-primary);
          outline-offset: 2px;
        }

        .file-upload-zone--drag-over {
          border-color: var(--color-primary);
          background-color: var(--color-active);
          border-style: solid;
        }

        .file-upload-zone--has-file {
          border-color: var(--color-success);
          border-style: solid;
        }

        .file-upload-zone--error {
          border-color: var(--color-error);
        }

        .file-upload-zone--disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .file-upload-input {
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

        .file-upload-empty,
        .file-upload-selected {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: var(--spacing-sm);
          text-align: center;
        }

        .file-upload-selected {
          flex-direction: row;
          gap: var(--spacing-md);
        }

        .upload-icon {
          font-size: var(--font-size-3xl);
          line-height: 1;
        }

        .upload-text {
          font-size: var(--font-size-base);
          color: var(--color-text);
        }

        .upload-link {
          color: var(--color-primary);
          text-decoration: underline;
          font-weight: 500;
        }

        .upload-hint {
          font-size: var(--font-size-sm);
          color: var(--color-text-secondary);
        }

        .file-info {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: var(--spacing-xs);
        }

        .file-name {
          font-weight: 600;
          color: var(--color-text);
          word-break: break-all;
        }

        .file-size {
          font-size: var(--font-size-sm);
          color: var(--color-text-secondary);
        }

        .file-clear-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          padding: 0;
          border: none;
          border-radius: var(--radius-full);
          background-color: var(--color-border);
          color: var(--color-text);
          cursor: pointer;
          transition: background-color var(--transition-fast);
        }

        .file-clear-btn:hover {
          background-color: var(--color-error);
          color: var(--color-text-light);
        }

        .file-upload-error {
          padding: var(--spacing-sm) var(--spacing-md);
          background-color: rgba(219, 76, 64, 0.1);
          border-radius: var(--radius-sm);
          color: var(--color-error);
          font-size: var(--font-size-sm);
        }

        .file-upload-meta {
          display: flex;
          justify-content: flex-end;
        }

        .max-size-indicator {
          font-size: var(--font-size-xs);
          color: var(--color-text-secondary);
        }
      `}</style>
    </div>
  );
}

export default FileUpload;
