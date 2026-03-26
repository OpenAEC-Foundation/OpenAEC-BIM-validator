/**
 * BcfGenerateDialog — modal overlay for configuring BCF generation settings.
 *
 * Shown before bulk or single-issue BCF export. Settings are persisted
 * in localStorage so the user's preferences carry over between sessions.
 */

import { useCallback, useEffect, useState } from "react";

import type { BcfGenerationSettings } from "../../types/bcfGenerationSettings";
import {
  TOPIC_TYPE_OPTIONS,
  PRIORITY_OPTIONS,
  loadBcfSettings,
  saveBcfSettings,
} from "../../types/bcfGenerationSettings";

import "./BcfGenerateDialog.css";

export interface BcfGenerateDialogProps {
  /** Number of issues that will be generated */
  issueCount: number;
  /** Called when the user confirms generation */
  onGenerate: (settings: BcfGenerationSettings) => void;
  /** Called when the user cancels */
  onCancel: () => void;
}

export function BcfGenerateDialog({
  issueCount,
  onGenerate,
  onCancel,
}: BcfGenerateDialogProps) {
  const [settings, setSettings] = useState<BcfGenerationSettings>(loadBcfSettings);

  /** Persist on every change */
  useEffect(() => {
    saveBcfSettings(settings);
  }, [settings]);

  /** Close on Escape */
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onCancel]);

  const update = useCallback(
    <K extends keyof BcfGenerationSettings>(key: K, value: BcfGenerationSettings[K]) => {
      setSettings((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const handleGenerate = useCallback(() => {
    onGenerate(settings);
  }, [onGenerate, settings]);

  /** Prevent overlay click from bubbling to underlying panels */
  const handleOverlayClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) onCancel();
    },
    [onCancel],
  );

  return (
    <div className="bcf-dialog-overlay" onClick={handleOverlayClick}>
      <div className="bcf-dialog" role="dialog" aria-labelledby="bcf-dialog-title">
        {/* Header */}
        <div className="bcf-dialog__header">
          <h2 id="bcf-dialog-title" className="bcf-dialog__title">
            BCF Export Settings
          </h2>
          <span className="bcf-dialog__issue-count">
            {issueCount} issue{issueCount !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Body */}
        <div className="bcf-dialog__body">
          <div className="bcf-dialog__grid">
            {/* ── Title section ──────────────────────────── */}
            <div className="bcf-dialog__field">
              <label className="bcf-dialog__label" htmlFor="bcf-title-prefix">
                Title prefix
              </label>
              <input
                id="bcf-title-prefix"
                className="bcf-dialog__input"
                type="text"
                placeholder="bijv. REV01"
                value={settings.titlePrefix}
                onChange={(e) => update("titlePrefix", e.target.value)}
              />
            </div>

            <div className="bcf-dialog__field">
              <span className="bcf-dialog__label">Title inhoud</span>
              <div className="bcf-dialog__checkboxes">
                <label className="bcf-dialog__checkbox-label">
                  <input
                    type="checkbox"
                    checked={settings.includeSpecName}
                    onChange={(e) => update("includeSpecName", e.target.checked)}
                  />
                  Spec name
                </label>
                <label className="bcf-dialog__checkbox-label">
                  <input
                    type="checkbox"
                    checked={settings.includeReqName}
                    onChange={(e) => update("includeReqName", e.target.checked)}
                  />
                  Req name
                </label>
              </div>
            </div>

            {/* ── Metadata section ───────────────────────── */}
            <div className="bcf-dialog__section">Metadata</div>

            <div className="bcf-dialog__field">
              <label className="bcf-dialog__label" htmlFor="bcf-type">
                Type
              </label>
              <select
                id="bcf-type"
                className="bcf-dialog__select"
                value={settings.topicType}
                onChange={(e) => update("topicType", e.target.value)}
              >
                {TOPIC_TYPE_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            <div className="bcf-dialog__field">
              <label className="bcf-dialog__label" htmlFor="bcf-priority">
                Priority
              </label>
              <select
                id="bcf-priority"
                className="bcf-dialog__select"
                value={settings.priority}
                onChange={(e) =>
                  update("priority", e.target.value as BcfGenerationSettings["priority"])
                }
              >
                {PRIORITY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="bcf-dialog__field">
              <label className="bcf-dialog__label" htmlFor="bcf-assigned">
                Assigned to
              </label>
              <input
                id="bcf-assigned"
                className="bcf-dialog__input"
                type="text"
                placeholder="naam of email"
                value={settings.assignedTo}
                onChange={(e) => update("assignedTo", e.target.value)}
              />
            </div>

            <div className="bcf-dialog__field">
              <label className="bcf-dialog__label" htmlFor="bcf-label">
                Label
              </label>
              <input
                id="bcf-label"
                className="bcf-dialog__input"
                type="text"
                placeholder="bijv. Sprint 3"
                value={settings.label}
                onChange={(e) => update("label", e.target.value)}
              />
            </div>

            <div className="bcf-dialog__field">
              <label className="bcf-dialog__label" htmlFor="bcf-milestone">
                Milestone
              </label>
              <input
                id="bcf-milestone"
                className="bcf-dialog__input"
                type="text"
                placeholder="bijv. DO fase"
                value={settings.milestone}
                onChange={(e) => update("milestone", e.target.value)}
              />
            </div>

            <div className="bcf-dialog__field">
              <label className="bcf-dialog__label" htmlFor="bcf-deadline">
                Deadline
              </label>
              <input
                id="bcf-deadline"
                className="bcf-dialog__input"
                type="date"
                value={settings.deadline}
                onChange={(e) => update("deadline", e.target.value)}
              />
            </div>

            {/* ── Description section ────────────────────── */}
            <div className="bcf-dialog__section">Beschrijving</div>

            <div className="bcf-dialog__field bcf-dialog__field--full">
              <label className="bcf-dialog__label" htmlFor="bcf-desc-prefix">
                Description prefix
              </label>
              <input
                id="bcf-desc-prefix"
                className="bcf-dialog__input"
                type="text"
                placeholder="bijv. Actie vereist voor oplevering"
                value={settings.descriptionPrefix}
                onChange={(e) => update("descriptionPrefix", e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bcf-dialog__footer">
          <button
            type="button"
            className="bcf-dialog__btn bcf-dialog__btn--cancel"
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            type="button"
            className="bcf-dialog__btn bcf-dialog__btn--generate"
            onClick={handleGenerate}
          >
            Generate {issueCount} issue{issueCount !== 1 ? "s" : ""}
          </button>
        </div>
      </div>
    </div>
  );
}
