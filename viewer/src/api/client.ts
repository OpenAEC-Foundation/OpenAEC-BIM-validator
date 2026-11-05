/**
 * API client for the IFC Validator async job endpoints
 *
 * This client provides functions to:
 * - Submit validation requests (POST /api/v1/validate)
 * - Poll job status (GET /api/v1/jobs/{job_id})
 */

import type {
  JobStatusResponse,
  SubmitValidationResponse,
  IdsStandard,
} from '../types/validation';
import { API_ORIGIN } from './apiBase';

/** Base URL for API endpoints */
const API_BASE = `${API_ORIGIN}/api/v1`;

/**
 * Error thrown when an API request fails
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly detail?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Parse error response from the API
 */
async function parseErrorResponse(response: Response): Promise<string> {
  try {
    const errorData = await response.json();
    return errorData.detail || errorData.message || 'An unknown error occurred';
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

/**
 * Submit an IFC file for validation
 *
 * @param ifcFile - The IFC file to validate (required)
 * @param idsStandard - The IDS standard to use: 'nl-bim' or 'rvb' (optional)
 * @param idsFile - A custom IDS file to use instead of a standard (optional)
 * @returns Promise resolving to the submission response with job_id and status_url
 * @throws ApiError if the submission fails
 *
 * @example
 * // Using a standard IDS
 * const response = await submitValidation(ifcFile, 'nl-bim');
 *
 * @example
 * // Using a custom IDS file
 * const response = await submitValidation(ifcFile, undefined, customIdsFile);
 */
export async function submitValidation(
  ifcFile: File,
  idsStandard?: IdsStandard,
  idsFile?: File
): Promise<SubmitValidationResponse> {
  const formData = new FormData();
  formData.append('ifc_file', ifcFile);

  if (idsFile) {
    // Custom IDS file takes precedence over standard
    formData.append('ids_file', idsFile);
  } else if (idsStandard) {
    formData.append('ids_standard', idsStandard);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/validate`, {
      method: 'POST',
      body: formData,
    });
  } catch (error) {
    // Network error (no response received)
    throw new ApiError(
      'Network error: Unable to connect to the server. Please check your connection and try again.',
      undefined,
      error instanceof Error ? error.message : 'Unknown network error'
    );
  }

  if (!response.ok) {
    const errorMessage = await parseErrorResponse(response);
    throw new ApiError(
      errorMessage,
      response.status,
      errorMessage
    );
  }

  return response.json();
}

/**
 * Poll the status of a validation job
 *
 * @param jobId - The unique identifier of the job to poll
 * @returns Promise resolving to the current job status
 * @throws ApiError if the status check fails
 *
 * @example
 * const status = await pollJobStatus('abc-123');
 * if (status.status === 'completed') {
 *   console.log('Results:', status.result);
 * }
 */
export async function pollJobStatus(jobId: string): Promise<JobStatusResponse> {
  if (!jobId) {
    throw new ApiError('Job ID is required', undefined, 'Missing job_id parameter');
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}`);
  } catch (error) {
    // Network error (no response received)
    throw new ApiError(
      'Network error: Unable to connect to the server. Please check your connection and try again.',
      undefined,
      error instanceof Error ? error.message : 'Unknown network error'
    );
  }

  if (!response.ok) {
    if (response.status === 404) {
      throw new ApiError(
        `Job not found: ${jobId}`,
        404,
        'The requested validation job does not exist'
      );
    }
    const errorMessage = await parseErrorResponse(response);
    throw new ApiError(
      errorMessage,
      response.status,
      errorMessage
    );
  }

  return response.json();
}

/**
 * Check if a job has finished (completed or failed)
 *
 * @param status - The job status response to check
 * @returns true if the job has finished processing
 */
export function isJobFinished(status: JobStatusResponse): boolean {
  return status.status === 'completed' || status.status === 'failed';
}

/**
 * Check if a job completed successfully
 *
 * @param status - The job status response to check
 * @returns true if the job completed successfully with results
 */
export function isJobSuccessful(status: JobStatusResponse): boolean {
  return status.status === 'completed' && status.result !== null;
}

/**
 * Check if a job failed
 *
 * @param status - The job status response to check
 * @returns true if the job failed with an error
 */
export function isJobFailed(status: JobStatusResponse): boolean {
  return status.status === 'failed';
}

/**
 * Download validation results as BCF 2.1 .bcfzip
 *
 * @param jobId - The unique identifier of the completed validation job
 * @returns Promise resolving to a Blob containing the .bcfzip file
 * @throws ApiError if the download fails
 */
export async function downloadBcf(jobId: string): Promise<Blob> {
  if (!jobId) {
    throw new ApiError('Job ID is required', undefined, 'Missing job_id parameter');
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}/bcf`);
  } catch (error) {
    throw new ApiError(
      'Network error: Unable to download BCF file.',
      undefined,
      error instanceof Error ? error.message : 'Unknown network error'
    );
  }

  if (!response.ok) {
    const errorMessage = await parseErrorResponse(response);
    throw new ApiError(errorMessage, response.status, errorMessage);
  }

  return response.blob();
}
