/**
 * Validation slice — manages IDS validation state.
 *
 * Handles the full validation lifecycle: IDS selection, job submission,
 * polling, results, and error state. Integrates with the existing
 * API client for backend communication.
 */

import type { StateCreator } from "zustand";
import type {
  JobStatusResponse,
  ValidationResult,
  IdsStandard,
} from "../../types/validation";
import type { IdsSelection } from "../../components/IdsSelector";
import {
  submitValidation,
  pollJobStatus,
  isJobFinished,
  isJobSuccessful,
  isJobFailed,
  ApiError,
} from "../../api/client";

/** Polling interval in milliseconds */
const POLLING_INTERVAL = 2000;

/** Validation workflow phases */
export type ValidationPhase =
  | "idle"
  | "submitting"
  | "polling"
  | "completed"
  | "error";

export interface ValidationSlice {
  /** Current validation phase */
  validationPhase: ValidationPhase;

  /** IDS selection (standard or custom file) */
  idsSelection: IdsSelection | null;

  /** Active job ID */
  jobId: string | null;

  /** Latest job status from polling */
  jobStatus: JobStatusResponse | null;

  /** Final validation result */
  validationResult: ValidationResult | null;

  /** Validation error */
  validationError: { message: string; details?: string } | null;

  /** Set IDS selection */
  setIdsSelection: (selection: IdsSelection | null) => void;

  /** Submit validation for the current project's IFC file */
  submitValidation: (ifcFile: File) => Promise<void>;

  /** Cancel active validation */
  cancelValidation: () => void;

  /** Reset validation state */
  resetValidation: () => void;

  /** Dismiss validation error */
  dismissValidationError: () => void;

  /** Retry after error */
  retryValidation: () => void;
}

/** Store polling interval handle */
let pollingInterval: ReturnType<typeof setInterval> | null = null;

function stopPolling(): void {
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
}

export const createValidationSlice: StateCreator<ValidationSlice> = (
  set,
  get
) => ({
  validationPhase: "idle",
  idsSelection: { type: "standard", standard: "nl-bim" },
  jobId: null,
  jobStatus: null,
  validationResult: null,
  validationError: null,

  setIdsSelection: (selection: IdsSelection | null) => {
    set({ idsSelection: selection, validationError: null });
  },

  submitValidation: async (ifcFile: File) => {
    const { idsSelection } = get();

    if (!idsSelection) {
      set({
        validationError: {
          message: "Selecteer een IDS standaard of upload een custom IDS.",
        },
      });
      return;
    }

    set({
      validationPhase: "submitting",
      validationError: null,
      validationResult: null,
      jobStatus: null,
      jobId: null,
    });

    try {
      const idsStandard: IdsStandard | undefined =
        idsSelection.type === "standard" ? idsSelection.standard : undefined;
      const idsFile: File | undefined =
        idsSelection.type === "custom" ? idsSelection.file : undefined;

      const response = await submitValidation(ifcFile, idsStandard, idsFile);

      set({
        jobId: response.job_id,
        validationPhase: "polling",
      });

      // Start polling
      const pollFn = async () => {
        const state = get();
        if (state.validationPhase !== "polling" || !state.jobId) {
          stopPolling();
          return;
        }

        try {
          const status = await pollJobStatus(state.jobId);
          set({ jobStatus: status });

          if (isJobFinished(status)) {
            stopPolling();

            if (isJobSuccessful(status) && status.result) {
              set({
                validationResult: status.result,
                validationPhase: "completed",
              });
            } else if (isJobFailed(status)) {
              set({
                validationError: {
                  message: status.error ?? "Validatie mislukt",
                  details: "De validatie job heeft een fout opgeleverd.",
                },
                validationPhase: "error",
              });
            }
          }
        } catch (err) {
          stopPolling();
          set({
            validationError: {
              message:
                err instanceof ApiError
                  ? err.message
                  : "Fout bij ophalen job status.",
              details: err instanceof Error ? err.message : undefined,
            },
            validationPhase: "error",
          });
        }
      };

      // Initial poll + interval
      stopPolling();
      pollFn();
      pollingInterval = setInterval(pollFn, POLLING_INTERVAL);
    } catch (err) {
      set({
        validationError: {
          message:
            err instanceof ApiError
              ? err.message
              : "Validatie kon niet worden gestart.",
          details: err instanceof Error ? err.message : undefined,
        },
        validationPhase: "error",
      });
    }
  },

  cancelValidation: () => {
    stopPolling();
    set({
      validationPhase: "idle",
      jobId: null,
      jobStatus: null,
    });
  },

  resetValidation: () => {
    stopPolling();
    set({
      validationPhase: "idle",
      jobId: null,
      jobStatus: null,
      validationResult: null,
      validationError: null,
    });
  },

  retryValidation: () => {
    set({
      validationPhase: "idle",
      validationError: null,
      validationResult: null,
      jobStatus: null,
      jobId: null,
    });
  },

  dismissValidationError: () => {
    const { validationPhase } = get();
    set({ validationError: null });
    if (validationPhase === "error") {
      set({ validationPhase: "idle" });
    }
  },
});
