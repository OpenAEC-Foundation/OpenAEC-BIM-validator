/**
 * Unit tests for API client functions
 *
 * Tests cover:
 * - submitValidation: submitting IFC files with various IDS options
 * - pollJobStatus: polling job status with various responses
 * - Helper functions: isJobFinished, isJobSuccessful, isJobFailed
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  submitValidation,
  pollJobStatus,
  isJobFinished,
  isJobSuccessful,
  isJobFailed,
  ApiError,
} from './client';
import type {
  JobStatusResponse,
  SubmitValidationResponse,
  ValidationResult,
} from '../types/validation';

// Mock fetch is already set up in setupTests.ts, but we need to type it
const mockFetch = global.fetch as ReturnType<typeof vi.fn>;

/**
 * Helper to create a mock Response object
 */
function createMockResponse(
  data: unknown,
  options: { ok?: boolean; status?: number } = {}
): Response {
  const { ok = true, status = 200 } = options;
  return {
    ok,
    status,
    json: vi.fn().mockResolvedValue(data),
    text: vi.fn().mockResolvedValue(JSON.stringify(data)),
  } as unknown as Response;
}

/**
 * Helper to create a mock File object
 */
function createMockFile(name: string, content: string = 'mock content'): File {
  return new File([content], name, { type: 'application/octet-stream' });
}

/**
 * Helper to create a sample ValidationResult for testing
 */
function createMockValidationResult(): ValidationResult {
  return {
    success: true,
    ifc_file_name: 'test.ifc',
    ids_file_name: 'test.ids',
    total_specifications: 5,
    failed_specifications: 0,
    total_elements_validated: 100,
    validation_timestamp: '2025-01-09T10:00:00Z',
    specifications: [],
  };
}

describe('submitValidation', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should submit validation with IFC file only', async () => {
    const mockResponse: SubmitValidationResponse = {
      job_id: 'test-job-123',
      status: 'pending',
      message: 'Validation job queued',
      status_url: '/api/v1/jobs/test-job-123',
    };

    mockFetch.mockResolvedValue(createMockResponse(mockResponse));

    const ifcFile = createMockFile('model.ifc');
    const result = await submitValidation(ifcFile);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledWith('/api/v1/validate', {
      method: 'POST',
      body: expect.any(FormData),
    });

    // Verify FormData contents
    const callArgs = mockFetch.mock.calls[0];
    const formData = callArgs[1].body as FormData;
    expect(formData.get('ifc_file')).toBeTruthy();

    expect(result).toEqual(mockResponse);
  });

  it('should submit validation with IFC file and IDS standard (nl-bim)', async () => {
    const mockResponse: SubmitValidationResponse = {
      job_id: 'test-job-456',
      status: 'pending',
      message: 'Validation job queued',
      status_url: '/api/v1/jobs/test-job-456',
    };

    mockFetch.mockResolvedValue(createMockResponse(mockResponse));

    const ifcFile = createMockFile('model.ifc');
    const result = await submitValidation(ifcFile, 'nl-bim');

    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Verify FormData includes ids_standard
    const callArgs = mockFetch.mock.calls[0];
    const formData = callArgs[1].body as FormData;
    expect(formData.get('ifc_file')).toBeTruthy();
    expect(formData.get('ids_standard')).toBe('nl-bim');

    expect(result).toEqual(mockResponse);
  });

  it('should submit validation with IFC file and IDS standard (rvb)', async () => {
    const mockResponse: SubmitValidationResponse = {
      job_id: 'test-job-789',
      status: 'pending',
      message: 'Validation job queued',
      status_url: '/api/v1/jobs/test-job-789',
    };

    mockFetch.mockResolvedValue(createMockResponse(mockResponse));

    const ifcFile = createMockFile('model.ifc');
    const result = await submitValidation(ifcFile, 'rvb');

    // Verify FormData includes ids_standard
    const callArgs = mockFetch.mock.calls[0];
    const formData = callArgs[1].body as FormData;
    expect(formData.get('ids_standard')).toBe('rvb');

    expect(result).toEqual(mockResponse);
  });

  it('should submit validation with IFC file and custom IDS file', async () => {
    const mockResponse: SubmitValidationResponse = {
      job_id: 'test-job-custom',
      status: 'pending',
      message: 'Validation job queued',
      status_url: '/api/v1/jobs/test-job-custom',
    };

    mockFetch.mockResolvedValue(createMockResponse(mockResponse));

    const ifcFile = createMockFile('model.ifc');
    const idsFile = createMockFile('custom.ids');
    const result = await submitValidation(ifcFile, undefined, idsFile);

    // Verify FormData includes ids_file, NOT ids_standard
    const callArgs = mockFetch.mock.calls[0];
    const formData = callArgs[1].body as FormData;
    expect(formData.get('ifc_file')).toBeTruthy();
    expect(formData.get('ids_file')).toBeTruthy();
    expect(formData.get('ids_standard')).toBeNull();

    expect(result).toEqual(mockResponse);
  });

  it('should prioritize custom IDS file over IDS standard', async () => {
    const mockResponse: SubmitValidationResponse = {
      job_id: 'test-job-priority',
      status: 'pending',
      message: 'Validation job queued',
      status_url: '/api/v1/jobs/test-job-priority',
    };

    mockFetch.mockResolvedValue(createMockResponse(mockResponse));

    const ifcFile = createMockFile('model.ifc');
    const idsFile = createMockFile('custom.ids');
    // Pass both standard and custom file - file should take precedence
    await submitValidation(ifcFile, 'nl-bim', idsFile);

    // Verify FormData includes ids_file, NOT ids_standard
    const callArgs = mockFetch.mock.calls[0];
    const formData = callArgs[1].body as FormData;
    expect(formData.get('ids_file')).toBeTruthy();
    expect(formData.get('ids_standard')).toBeNull();
  });

  it('should throw ApiError on network failure', async () => {
    mockFetch.mockRejectedValue(new Error('Network failure'));

    const ifcFile = createMockFile('model.ifc');

    await expect(submitValidation(ifcFile)).rejects.toThrow(ApiError);
    await expect(submitValidation(ifcFile)).rejects.toThrow(
      'Network error: Unable to connect to the server'
    );
  });

  it('should throw ApiError with status code on HTTP error', async () => {
    const errorResponse = { detail: 'Invalid file format' };
    mockFetch.mockResolvedValue(
      createMockResponse(errorResponse, { ok: false, status: 400 })
    );

    const ifcFile = createMockFile('model.ifc');

    try {
      await submitValidation(ifcFile);
      expect.fail('Should have thrown an error');
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      const apiError = error as ApiError;
      expect(apiError.message).toBe('Invalid file format');
      expect(apiError.statusCode).toBe(400);
    }
  });

  it('should handle error response without detail field', async () => {
    const errorResponse = { message: 'Something went wrong' };
    mockFetch.mockResolvedValue(
      createMockResponse(errorResponse, { ok: false, status: 500 })
    );

    const ifcFile = createMockFile('model.ifc');

    try {
      await submitValidation(ifcFile);
      expect.fail('Should have thrown an error');
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      const apiError = error as ApiError;
      expect(apiError.message).toBe('Something went wrong');
      expect(apiError.statusCode).toBe(500);
    }
  });

  it('should handle error response that fails to parse as JSON', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 502,
      json: vi.fn().mockRejectedValue(new Error('Invalid JSON')),
    } as unknown as Response);

    const ifcFile = createMockFile('model.ifc');

    try {
      await submitValidation(ifcFile);
      expect.fail('Should have thrown an error');
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      const apiError = error as ApiError;
      expect(apiError.message).toContain('502');
      expect(apiError.statusCode).toBe(502);
    }
  });
});

describe('pollJobStatus', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('should return pending job status', async () => {
    const mockStatus: JobStatusResponse = {
      job_id: 'job-pending',
      status: 'pending',
      created_at: '2025-01-09T10:00:00Z',
      started_at: null,
      completed_at: null,
      progress: 'Job queued',
      result: null,
      error: null,
      duration_seconds: null,
    };

    mockFetch.mockResolvedValue(createMockResponse(mockStatus));

    const result = await pollJobStatus('job-pending');

    expect(mockFetch).toHaveBeenCalledWith('/api/v1/jobs/job-pending');
    expect(result).toEqual(mockStatus);
    expect(result.status).toBe('pending');
  });

  it('should return processing job status with progress message', async () => {
    const mockStatus: JobStatusResponse = {
      job_id: 'job-processing',
      status: 'processing',
      created_at: '2025-01-09T10:00:00Z',
      started_at: '2025-01-09T10:00:05Z',
      completed_at: null,
      progress: 'Processing specification 3 of 13',
      result: null,
      error: null,
      duration_seconds: null,
    };

    mockFetch.mockResolvedValue(createMockResponse(mockStatus));

    const result = await pollJobStatus('job-processing');

    expect(result.status).toBe('processing');
    expect(result.progress).toBe('Processing specification 3 of 13');
    expect(result.started_at).toBe('2025-01-09T10:00:05Z');
  });

  it('should return completed job status with result', async () => {
    const mockValidationResult = createMockValidationResult();
    const mockStatus: JobStatusResponse = {
      job_id: 'job-completed',
      status: 'completed',
      created_at: '2025-01-09T10:00:00Z',
      started_at: '2025-01-09T10:00:05Z',
      completed_at: '2025-01-09T10:00:30Z',
      progress: 'Completed',
      result: mockValidationResult,
      error: null,
      duration_seconds: 25,
    };

    mockFetch.mockResolvedValue(createMockResponse(mockStatus));

    const result = await pollJobStatus('job-completed');

    expect(result.status).toBe('completed');
    expect(result.result).toEqual(mockValidationResult);
    expect(result.duration_seconds).toBe(25);
  });

  it('should return failed job status with error', async () => {
    const mockStatus: JobStatusResponse = {
      job_id: 'job-failed',
      status: 'failed',
      created_at: '2025-01-09T10:00:00Z',
      started_at: '2025-01-09T10:00:05Z',
      completed_at: '2025-01-09T10:00:10Z',
      progress: null,
      result: null,
      error: 'Invalid IFC file: Unable to parse schema',
      duration_seconds: 5,
    };

    mockFetch.mockResolvedValue(createMockResponse(mockStatus));

    const result = await pollJobStatus('job-failed');

    expect(result.status).toBe('failed');
    expect(result.error).toBe('Invalid IFC file: Unable to parse schema');
    expect(result.result).toBeNull();
  });

  it('should throw ApiError when job is not found (404)', async () => {
    mockFetch.mockResolvedValue(
      createMockResponse({ detail: 'Job not found' }, { ok: false, status: 404 })
    );

    try {
      await pollJobStatus('nonexistent-job');
      expect.fail('Should have thrown an error');
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      const apiError = error as ApiError;
      expect(apiError.statusCode).toBe(404);
      expect(apiError.message).toContain('Job not found');
    }
  });

  it('should throw ApiError on network failure', async () => {
    mockFetch.mockRejectedValue(new Error('Network unavailable'));

    await expect(pollJobStatus('some-job')).rejects.toThrow(ApiError);
    await expect(pollJobStatus('some-job')).rejects.toThrow(
      'Network error: Unable to connect to the server'
    );
  });

  it('should throw ApiError when job ID is empty', async () => {
    await expect(pollJobStatus('')).rejects.toThrow(ApiError);
    await expect(pollJobStatus('')).rejects.toThrow('Job ID is required');
  });

  it('should URL-encode the job ID', async () => {
    const mockStatus: JobStatusResponse = {
      job_id: 'job/with/special/chars',
      status: 'pending',
      created_at: '2025-01-09T10:00:00Z',
      started_at: null,
      completed_at: null,
      progress: null,
      result: null,
      error: null,
      duration_seconds: null,
    };

    mockFetch.mockResolvedValue(createMockResponse(mockStatus));

    await pollJobStatus('job/with/special/chars');

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/jobs/job%2Fwith%2Fspecial%2Fchars'
    );
  });

  it('should handle generic HTTP errors', async () => {
    const errorResponse = { detail: 'Internal server error' };
    mockFetch.mockResolvedValue(
      createMockResponse(errorResponse, { ok: false, status: 500 })
    );

    try {
      await pollJobStatus('some-job');
      expect.fail('Should have thrown an error');
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      const apiError = error as ApiError;
      expect(apiError.statusCode).toBe(500);
    }
  });
});

describe('isJobFinished', () => {
  it('should return true for completed status', () => {
    const status: JobStatusResponse = {
      job_id: 'test',
      status: 'completed',
      created_at: '2025-01-09T10:00:00Z',
      started_at: '2025-01-09T10:00:05Z',
      completed_at: '2025-01-09T10:00:30Z',
      progress: null,
      result: createMockValidationResult(),
      error: null,
      duration_seconds: 25,
    };

    expect(isJobFinished(status)).toBe(true);
  });

  it('should return true for failed status', () => {
    const status: JobStatusResponse = {
      job_id: 'test',
      status: 'failed',
      created_at: '2025-01-09T10:00:00Z',
      started_at: '2025-01-09T10:00:05Z',
      completed_at: '2025-01-09T10:00:10Z',
      progress: null,
      result: null,
      error: 'Something went wrong',
      duration_seconds: 5,
    };

    expect(isJobFinished(status)).toBe(true);
  });

  it('should return false for pending status', () => {
    const status: JobStatusResponse = {
      job_id: 'test',
      status: 'pending',
      created_at: '2025-01-09T10:00:00Z',
      started_at: null,
      completed_at: null,
      progress: 'Queued',
      result: null,
      error: null,
      duration_seconds: null,
    };

    expect(isJobFinished(status)).toBe(false);
  });

  it('should return false for processing status', () => {
    const status: JobStatusResponse = {
      job_id: 'test',
      status: 'processing',
      created_at: '2025-01-09T10:00:00Z',
      started_at: '2025-01-09T10:00:05Z',
      completed_at: null,
      progress: 'Processing...',
      result: null,
      error: null,
      duration_seconds: null,
    };

    expect(isJobFinished(status)).toBe(false);
  });
});

describe('isJobSuccessful', () => {
  it('should return true for completed status with result', () => {
    const status: JobStatusResponse = {
      job_id: 'test',
      status: 'completed',
      created_at: '2025-01-09T10:00:00Z',
      started_at: '2025-01-09T10:00:05Z',
      completed_at: '2025-01-09T10:00:30Z',
      progress: null,
      result: createMockValidationResult(),
      error: null,
      duration_seconds: 25,
    };

    expect(isJobSuccessful(status)).toBe(true);
  });

  it('should return false for completed status without result', () => {
    const status: JobStatusResponse = {
      job_id: 'test',
      status: 'completed',
      created_at: '2025-01-09T10:00:00Z',
      started_at: '2025-01-09T10:00:05Z',
      completed_at: '2025-01-09T10:00:30Z',
      progress: null,
      result: null,
      error: null,
      duration_seconds: 25,
    };

    expect(isJobSuccessful(status)).toBe(false);
  });

  it('should return false for failed status', () => {
    const status: JobStatusResponse = {
      job_id: 'test',
      status: 'failed',
      created_at: '2025-01-09T10:00:00Z',
      started_at: '2025-01-09T10:00:05Z',
      completed_at: '2025-01-09T10:00:10Z',
      progress: null,
      result: null,
      error: 'Error occurred',
      duration_seconds: 5,
    };

    expect(isJobSuccessful(status)).toBe(false);
  });

  it('should return false for pending status', () => {
    const status: JobStatusResponse = {
      job_id: 'test',
      status: 'pending',
      created_at: '2025-01-09T10:00:00Z',
      started_at: null,
      completed_at: null,
      progress: null,
      result: null,
      error: null,
      duration_seconds: null,
    };

    expect(isJobSuccessful(status)).toBe(false);
  });

  it('should return false for processing status', () => {
    const status: JobStatusResponse = {
      job_id: 'test',
      status: 'processing',
      created_at: '2025-01-09T10:00:00Z',
      started_at: '2025-01-09T10:00:05Z',
      completed_at: null,
      progress: 'Processing...',
      result: null,
      error: null,
      duration_seconds: null,
    };

    expect(isJobSuccessful(status)).toBe(false);
  });
});

describe('isJobFailed', () => {
  it('should return true for failed status', () => {
    const status: JobStatusResponse = {
      job_id: 'test',
      status: 'failed',
      created_at: '2025-01-09T10:00:00Z',
      started_at: '2025-01-09T10:00:05Z',
      completed_at: '2025-01-09T10:00:10Z',
      progress: null,
      result: null,
      error: 'Validation failed',
      duration_seconds: 5,
    };

    expect(isJobFailed(status)).toBe(true);
  });

  it('should return false for completed status', () => {
    const status: JobStatusResponse = {
      job_id: 'test',
      status: 'completed',
      created_at: '2025-01-09T10:00:00Z',
      started_at: '2025-01-09T10:00:05Z',
      completed_at: '2025-01-09T10:00:30Z',
      progress: null,
      result: createMockValidationResult(),
      error: null,
      duration_seconds: 25,
    };

    expect(isJobFailed(status)).toBe(false);
  });

  it('should return false for pending status', () => {
    const status: JobStatusResponse = {
      job_id: 'test',
      status: 'pending',
      created_at: '2025-01-09T10:00:00Z',
      started_at: null,
      completed_at: null,
      progress: null,
      result: null,
      error: null,
      duration_seconds: null,
    };

    expect(isJobFailed(status)).toBe(false);
  });

  it('should return false for processing status', () => {
    const status: JobStatusResponse = {
      job_id: 'test',
      status: 'processing',
      created_at: '2025-01-09T10:00:00Z',
      started_at: '2025-01-09T10:00:05Z',
      completed_at: null,
      progress: 'Processing...',
      result: null,
      error: null,
      duration_seconds: null,
    };

    expect(isJobFailed(status)).toBe(false);
  });
});

describe('ApiError', () => {
  it('should create error with message only', () => {
    const error = new ApiError('Something went wrong');

    expect(error.message).toBe('Something went wrong');
    expect(error.name).toBe('ApiError');
    expect(error.statusCode).toBeUndefined();
    expect(error.detail).toBeUndefined();
  });

  it('should create error with message and status code', () => {
    const error = new ApiError('Not found', 404);

    expect(error.message).toBe('Not found');
    expect(error.statusCode).toBe(404);
    expect(error.detail).toBeUndefined();
  });

  it('should create error with all properties', () => {
    const error = new ApiError('Validation failed', 422, 'Invalid file format');

    expect(error.message).toBe('Validation failed');
    expect(error.statusCode).toBe(422);
    expect(error.detail).toBe('Invalid file format');
  });

  it('should be instanceof Error', () => {
    const error = new ApiError('Test');

    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(ApiError);
  });
});
