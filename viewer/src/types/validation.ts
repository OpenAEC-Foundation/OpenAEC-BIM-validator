/**
 * TypeScript interfaces for IFC Validator API responses
 * These interfaces match the backend FastAPI models exactly
 */

/**
 * Status of a single element validation
 */
export type ValidationStatus = 'pass' | 'fail';

/**
 * Job execution status
 */
export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';

/**
 * Severity level for specification results
 */
export type Severity = 'error' | 'warning' | 'info';

/**
 * Result of validating a single IFC element against a requirement
 */
export interface ElementResult {
  /** IFC GlobalId of the element (may be null for some element types) */
  global_id: string | null;
  /** IFC entity type (e.g., 'IfcWall', 'IfcDoor') */
  element_type: string;
  /** Name property of the element (may be null) */
  element_name: string | null;
  /** Validation status for this element */
  status: ValidationStatus;
  /** Detailed validation messages explaining pass/fail reasons */
  messages: string[];
}

/**
 * Result of validating all applicable elements against a single requirement
 */
export interface RequirementResult {
  /** Human-readable description of the requirement */
  requirement_description: string;
  /** Overall status of the requirement (pass if all elements pass) */
  status: ValidationStatus;
  /** Total number of elements checked against this requirement */
  total_elements: number;
  /** Number of elements that failed this requirement */
  failed_elements: number;
  /** Individual element validation results */
  elements: ElementResult[];
}

/**
 * Result of validating all requirements in a single specification
 */
export interface SpecificationResult {
  /** Name of the specification (from IDS file) */
  specification_name: string;
  /** Overall status of the specification (pass if all requirements pass) */
  status: ValidationStatus;
  /** Severity level of failures in this specification */
  severity: Severity;
  /** Total number of requirements in this specification */
  total_requirements: number;
  /** Number of requirements that failed */
  failed_requirements: number;
  /** Individual requirement validation results */
  requirements: RequirementResult[];
}

/**
 * Complete validation result returned when a job completes successfully
 */
export interface ValidationResult {
  /** Whether the entire validation passed (all specifications passed) */
  success: boolean;
  /** Name of the IFC file that was validated */
  ifc_file_name: string;
  /** Name of the IDS file used for validation */
  ids_file_name: string;
  /** Total number of specifications checked */
  total_specifications: number;
  /** Number of specifications that failed */
  failed_specifications: number;
  /** Total count of IFC elements validated across all specifications */
  total_elements_validated: number;
  /** ISO 8601 timestamp when validation completed */
  validation_timestamp: string;
  /** Individual specification validation results */
  specifications: SpecificationResult[];
}

/**
 * Response from the job status endpoint (GET /api/v1/jobs/{job_id})
 */
export interface JobStatusResponse {
  /** Unique identifier for the validation job */
  job_id: string;
  /** Current status of the job */
  status: JobStatus;
  /** ISO 8601 timestamp when job was created */
  created_at: string;
  /** ISO 8601 timestamp when job started processing (null if pending) */
  started_at: string | null;
  /** ISO 8601 timestamp when job completed (null if not completed) */
  completed_at: string | null;
  /** Human-readable progress message (e.g., "Processing specification 3 of 13") */
  progress: string | null;
  /** Validation result (only present when status is 'completed') */
  result: ValidationResult | null;
  /** Error message (only present when status is 'failed') */
  error: string | null;
  /** Total duration of validation in seconds (null if not completed) */
  duration_seconds: number | null;
}

/**
 * Response from the validation submission endpoint (POST /api/v1/validate)
 */
export interface SubmitValidationResponse {
  /** Unique identifier for the created validation job */
  job_id: string;
  /** Initial status (always 'pending') */
  status: JobStatus;
  /** Human-readable confirmation message */
  message: string;
  /** URL to poll for job status */
  status_url: string;
}

/**
 * IDS standard options available for validation
 */
export type IdsStandard = 'nl-bim' | 'rvb';
