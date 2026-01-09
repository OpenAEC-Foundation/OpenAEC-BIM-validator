/**
 * Unit tests for IdsSelector component
 *
 * Tests cover:
 * - Default selection is nl-bim
 * - Radio button selection behavior
 * - Custom IDS file upload
 * - Disabled state
 * - Selection change callbacks
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IdsSelector, type IdsSelection } from './IdsSelector';

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

describe('IdsSelector', () => {
  let mockOnSelectionChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnSelectionChange = vi.fn();
  });

  describe('Rendering', () => {
    it('should render with label', () => {
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      expect(screen.getByText('IDS Standard')).toBeInTheDocument();
    });

    it('should render all three options', () => {
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      expect(screen.getByText('NL BIM Basis ILS')).toBeInTheDocument();
      expect(screen.getByText('RVB BIM Norm')).toBeInTheDocument();
      expect(screen.getByText('Custom IDS')).toBeInTheDocument();
    });

    it('should display descriptions for each option', () => {
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      expect(
        screen.getByText('Dutch BIM Base Information Level Specification')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Rijksvastgoedbedrijf BIM Standard')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Upload your own IDS file')
      ).toBeInTheDocument();
    });

    it('should have proper radiogroup role', () => {
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      expect(
        screen.getByRole('radiogroup', { name: /ids standard selection/i })
      ).toBeInTheDocument();
    });
  });

  describe('Default Selection', () => {
    it('should default to nl-bim selection', () => {
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      const nlBimRadio = screen.getByRole('radio', { name: /nl bim basis ils/i });
      expect(nlBimRadio).toBeChecked();
    });

    it('should not default to rvb', () => {
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      const rvbRadio = screen.getByRole('radio', { name: /rvb bim norm/i });
      expect(rvbRadio).not.toBeChecked();
    });

    it('should not default to custom', () => {
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      expect(customRadio).not.toBeChecked();
    });

    it('should not show custom upload zone by default', () => {
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      expect(
        screen.queryByText(/drop .ids file here/i)
      ).not.toBeInTheDocument();
    });
  });

  describe('Selection Changes', () => {
    it('should call onSelectionChange with nl-bim when nl-bim is selected', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // First select a different option
      const rvbRadio = screen.getByRole('radio', { name: /rvb bim norm/i });
      await user.click(rvbRadio);

      // Then select nl-bim
      const nlBimRadio = screen.getByRole('radio', { name: /nl bim basis ils/i });
      await user.click(nlBimRadio);

      expect(mockOnSelectionChange).toHaveBeenCalledWith({
        type: 'standard',
        standard: 'nl-bim',
      });
    });

    it('should call onSelectionChange with rvb when rvb is selected', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      const rvbRadio = screen.getByRole('radio', { name: /rvb bim norm/i });
      await user.click(rvbRadio);

      expect(mockOnSelectionChange).toHaveBeenCalledWith({
        type: 'standard',
        standard: 'rvb',
      });
    });

    it('should call onSelectionChange with null when custom is selected without file', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      // When custom is selected without a file, it should emit null
      expect(mockOnSelectionChange).toHaveBeenCalledWith(null);
    });

    it('should update radio button checked state on selection', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      const nlBimRadio = screen.getByRole('radio', { name: /nl bim basis ils/i });
      const rvbRadio = screen.getByRole('radio', { name: /rvb bim norm/i });

      expect(nlBimRadio).toBeChecked();
      expect(rvbRadio).not.toBeChecked();

      await user.click(rvbRadio);

      expect(nlBimRadio).not.toBeChecked();
      expect(rvbRadio).toBeChecked();
    });
  });

  describe('Custom IDS Upload', () => {
    it('should show upload zone when custom is selected', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      expect(screen.getByText(/drop .ids file here/i)).toBeInTheDocument();
    });

    it('should hide upload zone when switching from custom to standard', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // Select custom first
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      expect(screen.getByText(/drop .ids file here/i)).toBeInTheDocument();

      // Switch to nl-bim
      const nlBimRadio = screen.getByRole('radio', { name: /nl bim basis ils/i });
      await user.click(nlBimRadio);

      expect(screen.queryByText(/drop .ids file here/i)).not.toBeInTheDocument();
    });

    it('should accept valid .ids file', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // Select custom
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      // Upload .ids file
      const file = createMockFile('requirements.ids', 1024);
      const input = document.querySelector(
        '.ids-upload-input'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(mockOnSelectionChange).toHaveBeenCalledWith({
        type: 'custom',
        file,
      });
    });

    it('should reject non-.ids file', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // Select custom
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      mockOnSelectionChange.mockClear();

      // Try to upload non-.ids file
      const file = createMockFile('document.pdf', 1024);
      const input = document.querySelector(
        '.ids-upload-input'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(
        screen.getByText(/invalid file type. please select a .ids file/i)
      ).toBeInTheDocument();

      // Should not emit a custom selection with the invalid file
      expect(mockOnSelectionChange).not.toHaveBeenCalledWith(
        expect.objectContaining({ type: 'custom', file })
      );
    });

    it('should reject files larger than 10MB', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // Select custom
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      mockOnSelectionChange.mockClear();

      // Create a file larger than 10MB
      const largeSizeBytes = 10 * 1024 * 1024 + 1;
      const file = createMockFile('large.ids', largeSizeBytes);
      const input = document.querySelector(
        '.ids-upload-input'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(screen.getByText(/file is too large/i)).toBeInTheDocument();
    });

    it('should display max size hint for custom upload', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      expect(screen.getByText(/maximum file size: 10 MB/i)).toBeInTheDocument();
    });

    it('should display selected file name and size', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // Select custom
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      // Upload valid file
      const file = createMockFile('my_rules.ids', 5 * 1024 * 1024);
      const input = document.querySelector(
        '.ids-upload-input'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(screen.getByText('my_rules.ids')).toBeInTheDocument();
      expect(screen.getByText(/5 MB/i)).toBeInTheDocument();
    });

    it('should allow clearing selected custom file', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // Select custom
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      // Upload valid file
      const file = createMockFile('rules.ids', 1024);
      const input = document.querySelector(
        '.ids-upload-input'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(screen.getByText('rules.ids')).toBeInTheDocument();

      // Clear the file
      const clearButton = screen.getByRole('button', {
        name: /clear selected ids file/i,
      });
      await user.click(clearButton);

      expect(screen.queryByText('rules.ids')).not.toBeInTheDocument();
      expect(mockOnSelectionChange).toHaveBeenLastCalledWith(null);
    });

    it('should retain custom file selection when switching away and back', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // Select custom and upload file
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      const file = createMockFile('rules.ids', 1024);
      const input = document.querySelector(
        '.ids-upload-input'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(screen.getByText('rules.ids')).toBeInTheDocument();

      // Switch to nl-bim
      const nlBimRadio = screen.getByRole('radio', { name: /nl bim basis ils/i });
      await user.click(nlBimRadio);

      expect(screen.queryByText('rules.ids')).not.toBeInTheDocument();

      // Switch back to custom - file should still be retained in state
      await user.click(customRadio);

      // The file info should still be displayed
      expect(screen.getByText('rules.ids')).toBeInTheDocument();
    });
  });

  describe('Drag and Drop for Custom IDS', () => {
    it('should accept file via drag and drop', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // Select custom
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      const dropZone = screen.getByRole('button', {
        name: /drop ids file here or click to browse/i,
      });
      const file = createMockFile('rules.ids', 1024);

      fireEvent.drop(dropZone, {
        dataTransfer: { files: [file] },
      });

      await waitFor(() => {
        expect(mockOnSelectionChange).toHaveBeenCalledWith({
          type: 'custom',
          file,
        });
      });
    });

    it('should handle drag over state visually', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // Select custom
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      const dropZone = screen.getByRole('button', {
        name: /drop ids file here or click to browse/i,
      });

      fireEvent.dragOver(dropZone);

      expect(dropZone).toHaveClass('ids-upload-zone--drag-over');
    });
  });

  describe('Disabled State', () => {
    it('should disable all radio buttons when disabled', () => {
      render(
        <IdsSelector onSelectionChange={mockOnSelectionChange} disabled={true} />
      );

      const nlBimRadio = screen.getByRole('radio', { name: /nl bim basis ils/i });
      const rvbRadio = screen.getByRole('radio', { name: /rvb bim norm/i });
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });

      expect(nlBimRadio).toBeDisabled();
      expect(rvbRadio).toBeDisabled();
      expect(customRadio).toBeDisabled();
    });

    it('should not call onSelectionChange when disabled', async () => {
      const user = userEvent.setup();
      render(
        <IdsSelector onSelectionChange={mockOnSelectionChange} disabled={true} />
      );

      const rvbRadio = screen.getByRole('radio', { name: /rvb bim norm/i });

      // Attempt to click - should not work
      await user.click(rvbRadio);

      // Should not have been called (beyond any initial calls)
      expect(mockOnSelectionChange).not.toHaveBeenCalled();
    });

    it('should apply disabled styling to options', () => {
      render(
        <IdsSelector onSelectionChange={mockOnSelectionChange} disabled={true} />
      );

      const options = document.querySelectorAll('.ids-option');
      options.forEach((option) => {
        expect(option).toHaveClass('ids-option--disabled');
      });
    });

    it('should disable custom upload zone when disabled', async () => {
      const user = userEvent.setup();
      const { rerender } = render(
        <IdsSelector onSelectionChange={mockOnSelectionChange} />
      );

      // First select custom while enabled
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      // Then disable
      rerender(
        <IdsSelector onSelectionChange={mockOnSelectionChange} disabled={true} />
      );

      const uploadZone = screen.getByRole('button', {
        name: /drop ids file here or click to browse/i,
      });

      expect(uploadZone).toHaveClass('ids-upload-zone--disabled');
      expect(uploadZone).toHaveAttribute('aria-disabled', 'true');
    });

    it('should not show clear button when disabled with custom file', async () => {
      const user = userEvent.setup();
      const { rerender } = render(
        <IdsSelector onSelectionChange={mockOnSelectionChange} />
      );

      // Select custom and upload file
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      const file = createMockFile('rules.ids', 1024);
      const input = document.querySelector(
        '.ids-upload-input'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(screen.getByText('rules.ids')).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /clear selected ids file/i })
      ).toBeInTheDocument();

      // Disable
      rerender(
        <IdsSelector onSelectionChange={mockOnSelectionChange} disabled={true} />
      );

      // Clear button should not be present when disabled
      expect(
        screen.queryByRole('button', { name: /clear selected ids file/i })
      ).not.toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('should display error message with alert role', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // Select custom
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      // Upload invalid file
      const file = createMockFile('document.txt', 1024);
      const input = document.querySelector(
        '.ids-upload-input'
      ) as HTMLInputElement;

      await user.upload(input, file);

      const errorElement = screen.getByRole('alert');
      expect(errorElement).toBeInTheDocument();
      expect(errorElement).toHaveTextContent(/invalid file type/i);
    });

    it('should clear error when valid file is selected', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // Select custom
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      const input = document.querySelector(
        '.ids-upload-input'
      ) as HTMLInputElement;

      // Upload invalid file first
      const invalidFile = createMockFile('document.txt', 1024);
      await user.upload(input, invalidFile);

      expect(screen.getByText(/invalid file type/i)).toBeInTheDocument();

      // Then upload valid file
      const validFile = createMockFile('rules.ids', 1024);
      await user.upload(input, validFile);

      expect(screen.queryByText(/invalid file type/i)).not.toBeInTheDocument();
    });

    it('should clear error when switching to standard option', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // Select custom
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      // Upload invalid file
      const file = createMockFile('document.txt', 1024);
      const input = document.querySelector(
        '.ids-upload-input'
      ) as HTMLInputElement;

      await user.upload(input, file);

      expect(screen.getByText(/invalid file type/i)).toBeInTheDocument();

      // Switch to nl-bim
      const nlBimRadio = screen.getByRole('radio', { name: /nl bim basis ils/i });
      await user.click(nlBimRadio);

      // Error should be cleared (upload zone is hidden)
      expect(screen.queryByText(/invalid file type/i)).not.toBeInTheDocument();
    });
  });

  describe('Selection Type Validation', () => {
    it('should emit standard selection with correct type', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      const rvbRadio = screen.getByRole('radio', { name: /rvb bim norm/i });
      await user.click(rvbRadio);

      const lastCall = mockOnSelectionChange.mock.calls[
        mockOnSelectionChange.mock.calls.length - 1
      ][0] as IdsSelection;

      expect(lastCall.type).toBe('standard');
      if (lastCall.type === 'standard') {
        expect(lastCall.standard).toBe('rvb');
      }
    });

    it('should emit custom selection with correct type and file', async () => {
      const user = userEvent.setup();
      render(<IdsSelector onSelectionChange={mockOnSelectionChange} />);

      // Select custom
      const customRadio = screen.getByRole('radio', { name: /custom ids/i });
      await user.click(customRadio);

      // Upload file
      const file = createMockFile('rules.ids', 1024);
      const input = document.querySelector(
        '.ids-upload-input'
      ) as HTMLInputElement;

      await user.upload(input, file);

      const lastCall = mockOnSelectionChange.mock.calls[
        mockOnSelectionChange.mock.calls.length - 1
      ][0] as IdsSelection;

      expect(lastCall.type).toBe('custom');
      if (lastCall.type === 'custom') {
        expect(lastCall.file.name).toBe('rules.ids');
      }
    });
  });
});
