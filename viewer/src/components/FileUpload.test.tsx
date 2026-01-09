/**
 * Unit tests for FileUpload component
 *
 * Tests cover:
 * - File type validation (.ifc files only)
 * - File size validation (max 500MB)
 * - Drag and drop functionality
 * - File picker functionality
 * - Error display
 * - Disabled state
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FileUpload } from './FileUpload';

/**
 * Helper to create a mock File object
 */
function createMockFile(
  name: string,
  sizeInBytes: number = 1024,
  type: string = 'application/octet-stream'
): File {
  const content = new Array(sizeInBytes).fill('a').join('');
  return new File([content], name, { type });
}

describe('FileUpload', () => {
  let mockOnFileSelect: ReturnType<typeof vi.fn>;
  let mockOnFileClear: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnFileSelect = vi.fn();
    mockOnFileClear = vi.fn();
  });

  describe('Rendering', () => {
    it('should render with default label', () => {
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      expect(screen.getByText('IFC File')).toBeInTheDocument();
    });

    it('should render with custom label', () => {
      render(
        <FileUpload
          onFileSelect={mockOnFileSelect}
          label="Upload Building Model"
        />
      );

      expect(screen.getByText('Upload Building Model')).toBeInTheDocument();
    });

    it('should display drop zone with instructions', () => {
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      expect(screen.getByText(/drop .ifc file here or/i)).toBeInTheDocument();
      expect(screen.getByText('click to browse')).toBeInTheDocument();
    });

    it('should display max file size indicator', () => {
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      expect(screen.getByText(/maximum file size: 500 MB/i)).toBeInTheDocument();
      expect(screen.getByText(/max size: 500 MB/i)).toBeInTheDocument();
    });

    it('should have accessible drop zone with proper ARIA attributes', () => {
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const dropZone = screen.getByRole('button', {
        name: /drop .ifc file here or click to browse/i,
      });
      expect(dropZone).toBeInTheDocument();
      expect(dropZone).toHaveAttribute('tabindex', '0');
    });
  });

  describe('File Selection via Picker', () => {
    it('should accept valid .ifc file', async () => {
      const user = userEvent.setup();
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const file = createMockFile('building.ifc', 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(mockOnFileSelect).toHaveBeenCalledWith(file);
    });

    it('should accept .IFC file with uppercase extension', async () => {
      const user = userEvent.setup();
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const file = createMockFile('BUILDING.IFC', 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(mockOnFileSelect).toHaveBeenCalledWith(file);
    });

    it('should reject non-.ifc file', async () => {
      const user = userEvent.setup();
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const file = createMockFile('document.pdf', 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(mockOnFileSelect).not.toHaveBeenCalled();
      expect(
        screen.getByText(/invalid file type. please select a .ifc file/i)
      ).toBeInTheDocument();
    });

    it('should reject files with similar but incorrect extension', async () => {
      const user = userEvent.setup();
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const file = createMockFile('model.ifc.txt', 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(mockOnFileSelect).not.toHaveBeenCalled();
      expect(
        screen.getByText(/invalid file type. please select a .ifc file/i)
      ).toBeInTheDocument();
    });
  });

  describe('File Size Validation', () => {
    it('should reject files larger than 500MB', async () => {
      const user = userEvent.setup();
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      // Create a file larger than 500MB (500 * 1024 * 1024 bytes)
      const largeSizeBytes = 500 * 1024 * 1024 + 1;
      const file = createMockFile('large_building.ifc', largeSizeBytes);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(mockOnFileSelect).not.toHaveBeenCalled();
      expect(
        screen.getByText(/file is too large/i)
      ).toBeInTheDocument();
    });

    it('should accept files at exactly 500MB', async () => {
      const user = userEvent.setup();
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      // Create a file exactly at 500MB
      const exactSizeBytes = 500 * 1024 * 1024;
      const file = createMockFile('exact_size.ifc', exactSizeBytes);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(mockOnFileSelect).toHaveBeenCalledWith(file);
    });

    it('should accept files smaller than 500MB', async () => {
      const user = userEvent.setup();
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      // Create a 100MB file
      const file = createMockFile('small_building.ifc', 100 * 1024 * 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(mockOnFileSelect).toHaveBeenCalledWith(file);
    });

    it('should use custom maxSize when provided', async () => {
      const user = userEvent.setup();
      // Set max size to 10MB
      render(
        <FileUpload
          onFileSelect={mockOnFileSelect}
          maxSize={10 * 1024 * 1024}
        />
      );

      // Create an 11MB file
      const file = createMockFile('building.ifc', 11 * 1024 * 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(mockOnFileSelect).not.toHaveBeenCalled();
      expect(screen.getByText(/file is too large/i)).toBeInTheDocument();
    });
  });

  describe('Drag and Drop', () => {
    it('should accept valid file via drag and drop', async () => {
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const dropZone = screen.getByRole('button', {
        name: /drop .ifc file here or click to browse/i,
      });
      const file = createMockFile('model.ifc', 1024);

      fireEvent.dragOver(dropZone, {
        dataTransfer: { files: [file] },
      });
      fireEvent.drop(dropZone, {
        dataTransfer: { files: [file] },
      });

      await waitFor(() => {
        expect(mockOnFileSelect).toHaveBeenCalledWith(file);
      });
    });

    it('should reject invalid file via drag and drop', async () => {
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const dropZone = screen.getByRole('button', {
        name: /drop .ifc file here or click to browse/i,
      });
      const file = createMockFile('document.pdf', 1024);

      fireEvent.drop(dropZone, {
        dataTransfer: { files: [file] },
      });

      await waitFor(() => {
        expect(mockOnFileSelect).not.toHaveBeenCalled();
        expect(
          screen.getByText(/invalid file type/i)
        ).toBeInTheDocument();
      });
    });

    it('should handle drag over state visually', () => {
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const dropZone = screen.getByRole('button', {
        name: /drop .ifc file here or click to browse/i,
      });

      fireEvent.dragOver(dropZone);

      expect(dropZone).toHaveClass('file-upload-zone--drag-over');
    });

    it('should remove drag over state on drag leave', () => {
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const dropZone = screen.getByRole('button', {
        name: /drop .ifc file here or click to browse/i,
      });

      fireEvent.dragOver(dropZone);
      fireEvent.dragLeave(dropZone);

      expect(dropZone).not.toHaveClass('file-upload-zone--drag-over');
    });
  });

  describe('Selected File Display', () => {
    it('should display selected file name and size', async () => {
      const user = userEvent.setup();
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const file = createMockFile('my_building.ifc', 45.2 * 1024 * 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(screen.getByText('my_building.ifc')).toBeInTheDocument();
      expect(screen.getByText(/45\.2 MB/i)).toBeInTheDocument();
    });

    it('should show clear button when file is selected', async () => {
      const user = userEvent.setup();
      render(
        <FileUpload
          onFileSelect={mockOnFileSelect}
          onFileClear={mockOnFileClear}
        />
      );

      const file = createMockFile('building.ifc', 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(
        screen.getByRole('button', { name: /clear selected file/i })
      ).toBeInTheDocument();
    });

    it('should clear file and call onFileClear when clear button clicked', async () => {
      const user = userEvent.setup();
      render(
        <FileUpload
          onFileSelect={mockOnFileSelect}
          onFileClear={mockOnFileClear}
        />
      );

      const file = createMockFile('building.ifc', 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      const clearButton = screen.getByRole('button', {
        name: /clear selected file/i,
      });
      await user.click(clearButton);

      expect(mockOnFileClear).toHaveBeenCalled();
      expect(screen.queryByText('building.ifc')).not.toBeInTheDocument();
    });
  });

  describe('Disabled State', () => {
    it('should not allow file selection when disabled', async () => {
      const user = userEvent.setup();
      render(<FileUpload onFileSelect={mockOnFileSelect} disabled={true} />);

      const file = createMockFile('building.ifc', 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      // Input should be disabled
      expect(input).toBeDisabled();

      // Attempt to upload should not call the callback
      await user.upload(input, file);
      expect(mockOnFileSelect).not.toHaveBeenCalled();
    });

    it('should have disabled styling', () => {
      render(<FileUpload onFileSelect={mockOnFileSelect} disabled={true} />);

      const dropZone = screen.getByRole('button', {
        name: /drop .ifc file here or click to browse/i,
      });

      expect(dropZone).toHaveClass('file-upload-zone--disabled');
      expect(dropZone).toHaveAttribute('aria-disabled', 'true');
      expect(dropZone).toHaveAttribute('tabindex', '-1');
    });

    it('should not show clear button when disabled', async () => {
      const user = userEvent.setup();
      const { rerender } = render(
        <FileUpload
          onFileSelect={mockOnFileSelect}
          onFileClear={mockOnFileClear}
        />
      );

      const file = createMockFile('building.ifc', 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      // Verify file is shown
      expect(screen.getByText('building.ifc')).toBeInTheDocument();

      // Re-render with disabled
      rerender(
        <FileUpload
          onFileSelect={mockOnFileSelect}
          onFileClear={mockOnFileClear}
          disabled={true}
        />
      );

      // Clear button should not be present when disabled
      expect(
        screen.queryByRole('button', { name: /clear selected file/i })
      ).not.toBeInTheDocument();
    });

    it('should not accept drag and drop when disabled', async () => {
      render(<FileUpload onFileSelect={mockOnFileSelect} disabled={true} />);

      const dropZone = screen.getByRole('button', {
        name: /drop .ifc file here or click to browse/i,
      });
      const file = createMockFile('building.ifc', 1024);

      fireEvent.drop(dropZone, {
        dataTransfer: { files: [file] },
      });

      expect(mockOnFileSelect).not.toHaveBeenCalled();
    });
  });

  describe('Keyboard Accessibility', () => {
    it('should trigger file picker on Enter key', async () => {
      const user = userEvent.setup();
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const dropZone = screen.getByRole('button', {
        name: /drop .ifc file here or click to browse/i,
      });

      // Mock the file input click
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;
      const clickSpy = vi.spyOn(input, 'click');

      await user.type(dropZone, '{Enter}');

      expect(clickSpy).toHaveBeenCalled();
    });

    it('should trigger file picker on Space key', async () => {
      const user = userEvent.setup();
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const dropZone = screen.getByRole('button', {
        name: /drop .ifc file here or click to browse/i,
      });

      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;
      const clickSpy = vi.spyOn(input, 'click');

      await user.type(dropZone, ' ');

      expect(clickSpy).toHaveBeenCalled();
    });
  });

  describe('Custom Accept Prop', () => {
    it('should accept custom file extension', async () => {
      const user = userEvent.setup();
      render(
        <FileUpload
          onFileSelect={mockOnFileSelect}
          accept=".ids"
          label="IDS File"
        />
      );

      const file = createMockFile('rules.ids', 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(mockOnFileSelect).toHaveBeenCalledWith(file);
    });

    it('should reject files not matching custom accept', async () => {
      const user = userEvent.setup();
      render(
        <FileUpload
          onFileSelect={mockOnFileSelect}
          accept=".ids"
          label="IDS File"
        />
      );

      const file = createMockFile('building.ifc', 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(mockOnFileSelect).not.toHaveBeenCalled();
      expect(
        screen.getByText(/invalid file type. please select a .ids file/i)
      ).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('should clear error when valid file is selected after error', async () => {
      const user = userEvent.setup();
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      // First, upload invalid file to trigger error
      const invalidFile = createMockFile('document.pdf', 1024);
      await user.upload(input, invalidFile);

      expect(
        screen.getByText(/invalid file type/i)
      ).toBeInTheDocument();

      // Then, upload valid file
      const validFile = createMockFile('building.ifc', 1024);
      await user.upload(input, validFile);

      expect(
        screen.queryByText(/invalid file type/i)
      ).not.toBeInTheDocument();
      expect(mockOnFileSelect).toHaveBeenCalledWith(validFile);
    });

    it('should display error with alert role for accessibility', async () => {
      const user = userEvent.setup();
      render(<FileUpload onFileSelect={mockOnFileSelect} />);

      const file = createMockFile('document.pdf', 1024);
      const input = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      await user.upload(input, file);

      const errorElement = screen.getByRole('alert');
      expect(errorElement).toBeInTheDocument();
      expect(errorElement).toHaveTextContent(/invalid file type/i);
    });
  });
});
