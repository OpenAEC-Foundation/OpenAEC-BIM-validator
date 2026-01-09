/**
 * Unit tests for ResultsSummary component
 *
 * Tests cover:
 * - Rendering validation results correctly
 * - Displaying success/failure status
 * - Statistics cards (total, passed, failed)
 * - File information display
 * - Download JSON button
 * - Accessibility
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ResultsSummary } from './ResultsSummary';
import type { ValidationResult } from '../types/validation';

/**
 * Helper to create a successful validation result
 */
function createSuccessfulResult(
  overrides: Partial<ValidationResult> = {}
): ValidationResult {
  return {
    success: true,
    ifc_file_name: 'building.ifc',
    ids_file_name: 'nl-bim-basis-ils.ids',
    total_specifications: 13,
    failed_specifications: 0,
    total_elements_validated: 1500,
    validation_timestamp: '2025-01-09T10:30:00Z',
    specifications: [],
    ...overrides,
  };
}

/**
 * Helper to create a failed validation result
 */
function createFailedResult(
  overrides: Partial<ValidationResult> = {}
): ValidationResult {
  return {
    success: false,
    ifc_file_name: 'complex_model.ifc',
    ids_file_name: 'rvb-bim-norm.ids',
    total_specifications: 13,
    failed_specifications: 5,
    total_elements_validated: 3200,
    validation_timestamp: '2025-01-09T11:45:30Z',
    specifications: [],
    ...overrides,
  };
}

describe('ResultsSummary', () => {
  describe('Rendering', () => {
    it('should render with region role and accessible name', () => {
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} />);

      expect(
        screen.getByRole('region', { name: /validation results summary/i })
      ).toBeInTheDocument();
    });

    it('should display summary heading', () => {
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} />);

      expect(
        screen.getByRole('heading', { name: /validation passed/i })
      ).toBeInTheDocument();
    });
  });

  describe('Success State', () => {
    it('should display "Validation Passed" for successful result', () => {
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} />);

      expect(screen.getByText('Validation Passed')).toBeInTheDocument();
    });

    it('should show success icon for passed validation', () => {
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} />);

      // Check for the checkmark emoji
      expect(screen.getByText('✅')).toBeInTheDocument();
    });

    it('should apply success styling class', () => {
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} />);

      const summaryContainer = screen.getByRole('region', {
        name: /validation results summary/i,
      });
      expect(summaryContainer).toHaveClass('results-summary--success');
    });
  });

  describe('Failure State', () => {
    it('should display "Validation Failed" for failed result', () => {
      const result = createFailedResult();
      render(<ResultsSummary result={result} />);

      expect(screen.getByText('Validation Failed')).toBeInTheDocument();
    });

    it('should show failure icon for failed validation', () => {
      const result = createFailedResult();
      render(<ResultsSummary result={result} />);

      // Check for the X emoji
      expect(screen.getByText('❌')).toBeInTheDocument();
    });

    it('should apply failure styling class', () => {
      const result = createFailedResult();
      render(<ResultsSummary result={result} />);

      const summaryContainer = screen.getByRole('region', {
        name: /validation results summary/i,
      });
      expect(summaryContainer).toHaveClass('results-summary--failure');
    });
  });

  describe('Statistics Cards', () => {
    it('should display total specifications count', () => {
      const result = createSuccessfulResult({ total_specifications: 13 });
      render(<ResultsSummary result={result} />);

      expect(screen.getByText('13')).toBeInTheDocument();
      expect(screen.getByText('Total')).toBeInTheDocument();
    });

    it('should display passed specifications count', () => {
      const result = createSuccessfulResult({
        total_specifications: 13,
        failed_specifications: 0,
      });
      render(<ResultsSummary result={result} />);

      // All 13 passed
      expect(screen.getByText('Passed')).toBeInTheDocument();
      // Check that 13 appears in the passed card (total - failed = 13 - 0 = 13)
      const passedCard = document.querySelector('.stat-card--passed');
      expect(passedCard).toHaveTextContent('13');
    });

    it('should display failed specifications count', () => {
      const result = createFailedResult({
        total_specifications: 13,
        failed_specifications: 5,
      });
      render(<ResultsSummary result={result} />);

      expect(screen.getByText('Failed')).toBeInTheDocument();
      const failedCard = document.querySelector('.stat-card--failed');
      expect(failedCard).toHaveTextContent('5');
    });

    it('should calculate passed correctly from total and failed', () => {
      const result = createFailedResult({
        total_specifications: 10,
        failed_specifications: 3,
      });
      render(<ResultsSummary result={result} />);

      // Passed should be 10 - 3 = 7
      const passedCard = document.querySelector('.stat-card--passed');
      expect(passedCard).toHaveTextContent('7');
    });

    it('should handle all specifications passing', () => {
      const result = createSuccessfulResult({
        total_specifications: 5,
        failed_specifications: 0,
      });
      render(<ResultsSummary result={result} />);

      const passedCard = document.querySelector('.stat-card--passed');
      const failedCard = document.querySelector('.stat-card--failed');

      expect(passedCard).toHaveTextContent('5');
      expect(failedCard).toHaveTextContent('0');
    });

    it('should handle all specifications failing', () => {
      const result = createFailedResult({
        total_specifications: 8,
        failed_specifications: 8,
      });
      render(<ResultsSummary result={result} />);

      const passedCard = document.querySelector('.stat-card--passed');
      const failedCard = document.querySelector('.stat-card--failed');

      expect(passedCard).toHaveTextContent('0');
      expect(failedCard).toHaveTextContent('8');
    });
  });

  describe('File Information', () => {
    it('should display IFC file name', () => {
      const result = createSuccessfulResult({
        ifc_file_name: 'my_building_model.ifc',
      });
      render(<ResultsSummary result={result} />);

      expect(screen.getByText('IFC File:')).toBeInTheDocument();
      expect(screen.getByText('my_building_model.ifc')).toBeInTheDocument();
    });

    it('should display IDS file name', () => {
      const result = createSuccessfulResult({
        ids_file_name: 'custom-requirements.ids',
      });
      render(<ResultsSummary result={result} />);

      expect(screen.getByText('IDS File:')).toBeInTheDocument();
      expect(screen.getByText('custom-requirements.ids')).toBeInTheDocument();
    });

    it('should display elements validated count', () => {
      const result = createSuccessfulResult({
        total_elements_validated: 1500,
      });
      render(<ResultsSummary result={result} />);

      expect(screen.getByText('Elements Validated:')).toBeInTheDocument();
      expect(screen.getByText('1.5K')).toBeInTheDocument();
    });

    it('should format large element counts with K suffix', () => {
      const result = createSuccessfulResult({
        total_elements_validated: 45000,
      });
      render(<ResultsSummary result={result} />);

      expect(screen.getByText('45K')).toBeInTheDocument();
    });

    it('should format very large element counts with M suffix', () => {
      const result = createSuccessfulResult({
        total_elements_validated: 2500000,
      });
      render(<ResultsSummary result={result} />);

      expect(screen.getByText('2.5M')).toBeInTheDocument();
    });

    it('should display small element counts without suffix', () => {
      const result = createSuccessfulResult({
        total_elements_validated: 500,
      });
      render(<ResultsSummary result={result} />);

      expect(screen.getByText('500')).toBeInTheDocument();
    });

    it('should display completed timestamp', () => {
      const result = createSuccessfulResult({
        validation_timestamp: '2025-01-09T10:30:00Z',
      });
      render(<ResultsSummary result={result} />);

      expect(screen.getByText('Completed:')).toBeInTheDocument();
      // The exact format depends on locale, but it should contain the date
      expect(screen.getByText(/jan.*9.*2025/i)).toBeInTheDocument();
    });

    it('should display file names with title attribute for truncation', () => {
      const longFileName = 'very_long_building_model_name_with_lots_of_details.ifc';
      const result = createSuccessfulResult({
        ifc_file_name: longFileName,
      });
      render(<ResultsSummary result={result} />);

      const fileNameElement = screen.getByText(longFileName);
      expect(fileNameElement).toHaveAttribute('title', longFileName);
    });
  });

  describe('Download JSON Button', () => {
    it('should display download button when onDownloadJson is provided', () => {
      const mockDownload = vi.fn();
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} onDownloadJson={mockDownload} />);

      expect(
        screen.getByRole('button', { name: /download results as json/i })
      ).toBeInTheDocument();
    });

    it('should not display download button when onDownloadJson is not provided', () => {
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} />);

      expect(
        screen.queryByRole('button', { name: /download results as json/i })
      ).not.toBeInTheDocument();
    });

    it('should call onDownloadJson when download button is clicked', async () => {
      const user = userEvent.setup();
      const mockDownload = vi.fn();
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} onDownloadJson={mockDownload} />);

      const downloadButton = screen.getByRole('button', {
        name: /download results as json/i,
      });
      await user.click(downloadButton);

      expect(mockDownload).toHaveBeenCalledTimes(1);
    });

    it('should display JSON text on download button', () => {
      const mockDownload = vi.fn();
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} onDownloadJson={mockDownload} />);

      expect(screen.getByText('JSON')).toBeInTheDocument();
    });

    it('should display download icon', () => {
      const mockDownload = vi.fn();
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} onDownloadJson={mockDownload} />);

      // Check for the download arrow emoji
      expect(screen.getByText('⬇')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle zero specifications', () => {
      const result = createSuccessfulResult({
        total_specifications: 0,
        failed_specifications: 0,
        total_elements_validated: 0,
      });
      render(<ResultsSummary result={result} />);

      const totalCard = document.querySelector('.stat-card--total');
      const passedCard = document.querySelector('.stat-card--passed');
      const failedCard = document.querySelector('.stat-card--failed');

      expect(totalCard).toHaveTextContent('0');
      expect(passedCard).toHaveTextContent('0');
      expect(failedCard).toHaveTextContent('0');
    });

    it('should handle very long file names', () => {
      const longIFCName =
        'this_is_a_very_long_ifc_file_name_that_should_be_truncated_in_the_ui.ifc';
      const longIDSName =
        'this_is_also_a_very_long_ids_file_name_for_testing_purposes.ids';
      const result = createSuccessfulResult({
        ifc_file_name: longIFCName,
        ids_file_name: longIDSName,
      });
      render(<ResultsSummary result={result} />);

      expect(screen.getByText(longIFCName)).toBeInTheDocument();
      expect(screen.getByText(longIDSName)).toBeInTheDocument();
    });

    it('should handle invalid timestamp gracefully', () => {
      const result = createSuccessfulResult({
        validation_timestamp: 'invalid-timestamp',
      });
      render(<ResultsSummary result={result} />);

      // Should display the raw timestamp if parsing fails
      expect(screen.getByText('invalid-timestamp')).toBeInTheDocument();
    });

    it('should handle single specification', () => {
      const result = createSuccessfulResult({
        total_specifications: 1,
        failed_specifications: 0,
      });
      render(<ResultsSummary result={result} />);

      const totalCard = document.querySelector('.stat-card--total');
      expect(totalCard).toHaveTextContent('1');
    });
  });

  describe('Accessibility', () => {
    it('should have proper heading hierarchy', () => {
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} />);

      const heading = screen.getByRole('heading', { level: 2 });
      expect(heading).toBeInTheDocument();
    });

    it('should have accessible download button', async () => {
      const mockDownload = vi.fn();
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} onDownloadJson={mockDownload} />);

      const downloadButton = screen.getByRole('button', {
        name: /download results as json/i,
      });
      expect(downloadButton).toHaveAttribute(
        'aria-label',
        'Download results as JSON'
      );
    });

    it('should mark icons as aria-hidden', () => {
      const mockDownload = vi.fn();
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} onDownloadJson={mockDownload} />);

      const summaryIcon = document.querySelector('.summary-icon');
      const downloadIcon = document.querySelector('.download-icon');

      expect(summaryIcon).toHaveAttribute('aria-hidden', 'true');
      expect(downloadIcon).toHaveAttribute('aria-hidden', 'true');
    });
  });

  describe('Visual Styling Classes', () => {
    it('should apply correct classes to stat cards', () => {
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} />);

      expect(document.querySelector('.stat-card--total')).toBeInTheDocument();
      expect(document.querySelector('.stat-card--passed')).toBeInTheDocument();
      expect(document.querySelector('.stat-card--failed')).toBeInTheDocument();
    });

    it('should have summary-stats container', () => {
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} />);

      expect(document.querySelector('.summary-stats')).toBeInTheDocument();
    });

    it('should have summary-details container', () => {
      const result = createSuccessfulResult();
      render(<ResultsSummary result={result} />);

      expect(document.querySelector('.summary-details')).toBeInTheDocument();
    });
  });
});
