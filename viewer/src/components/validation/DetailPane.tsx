/**
 * DetailPane — context-sensitive detail panel for validation tree selection.
 *
 * Shows a property table and actions depending on the selected tree item:
 * - Specification: summary + requirement breakdown
 * - Requirement: element counts + failed elements list
 * - Element: messages + GlobalId + Zoom/BCF actions
 */

import { useCallback } from "react";

import type {
  SelectedTreeItem,
  SpecificationResult,
  RequirementResult,
  ElementResult,
} from "../../types/validation";

export interface DetailPaneProps {
  item: SelectedTreeItem;
  onElementZoom?: (globalId: string) => void;
  onCreateBcfFromSpec?: (spec: SpecificationResult) => void;
  onCreateBcfFromRequirement?: (
    spec: SpecificationResult,
    req: RequirementResult
  ) => void;
  onCreateBcfFromElement?: (
    spec: SpecificationResult,
    req: RequirementResult,
    el: ElementResult
  ) => void;
}

/** Format element display name */
function fmtElement(el: ElementResult): string {
  const parts: string[] = [];
  if (el.element_type) parts.push(el.element_type);
  if (el.element_name) parts.push(el.element_name);
  return parts.length > 0 ? parts.join(": ") : "Unknown Element";
}

/** Simple key-value row */
function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <tr>
      <td className="vt-detail__key">{label}</td>
      <td className="vt-detail__value">{value}</td>
    </tr>
  );
}

/** Status badge */
function StatusBadge({ status }: { status: "pass" | "fail" }) {
  return (
    <span
      className={`vt-detail__badge vt-detail__badge--${status}`}
    >
      {status === "pass" ? "PASS" : "FAIL"}
    </span>
  );
}

/** Specification detail view */
function SpecDetail({
  spec,
  onCreateBcf,
}: {
  spec: SpecificationResult;
  onCreateBcf?: (spec: SpecificationResult) => void;
}) {
  const passed = spec.total_requirements - spec.failed_requirements;

  return (
    <>
      <div className="vt-detail__title">{spec.specification_name}</div>
      <table className="vt-detail__table">
        <tbody>
          <Row label="Status" value={<StatusBadge status={spec.status} />} />
          <Row label="Severity" value={spec.severity} />
          <Row label="Requirements" value={spec.total_requirements} />
          <Row
            label="Passed"
            value={<span style={{ color: "var(--domain-pass)" }}>{passed}</span>}
          />
          <Row
            label="Failed"
            value={
              <span style={{ color: "var(--domain-fail)" }}>
                {spec.failed_requirements}
              </span>
            }
          />
        </tbody>
      </table>

      {spec.status === "fail" && onCreateBcf && (
        <div className="vt-detail__actions">
          <button
            type="button"
            className="vt-detail__btn vt-detail__btn--bcf"
            onClick={() => onCreateBcf(spec)}
          >
            +BCF issue
          </button>
        </div>
      )}
    </>
  );
}

/** Requirement detail view */
function ReqDetail({
  spec,
  req,
  onCreateBcf,
}: {
  spec: SpecificationResult;
  req: RequirementResult;
  onCreateBcf?: (spec: SpecificationResult, req: RequirementResult) => void;
}) {
  const passed = req.total_elements - req.failed_elements;

  return (
    <>
      <div className="vt-detail__title">{req.requirement_description}</div>
      <div className="vt-detail__subtitle">{spec.specification_name}</div>
      <table className="vt-detail__table">
        <tbody>
          <Row label="Status" value={<StatusBadge status={req.status} />} />
          <Row label="Elements" value={req.total_elements} />
          <Row
            label="Passed"
            value={<span style={{ color: "var(--domain-pass)" }}>{passed}</span>}
          />
          <Row
            label="Failed"
            value={
              <span style={{ color: "var(--domain-fail)" }}>
                {req.failed_elements}
              </span>
            }
          />
        </tbody>
      </table>

      {req.status === "fail" && onCreateBcf && (
        <div className="vt-detail__actions">
          <button
            type="button"
            className="vt-detail__btn vt-detail__btn--bcf"
            onClick={() => onCreateBcf(spec, req)}
          >
            +BCF issue
          </button>
        </div>
      )}
    </>
  );
}

/** Element detail view */
function ElDetail({
  spec,
  req,
  el,
  onZoom,
  onCreateBcf,
}: {
  spec: SpecificationResult;
  req: RequirementResult;
  el: ElementResult;
  onZoom?: (globalId: string) => void;
  onCreateBcf?: (
    spec: SpecificationResult,
    req: RequirementResult,
    el: ElementResult
  ) => void;
}) {
  const handleZoom = useCallback(() => {
    if (el.global_id) onZoom?.(el.global_id);
  }, [el.global_id, onZoom]);

  return (
    <>
      <div className="vt-detail__title">{fmtElement(el)}</div>
      <div className="vt-detail__subtitle">
        {spec.specification_name} &mdash; {req.requirement_description}
      </div>
      <table className="vt-detail__table">
        <tbody>
          <Row label="Status" value={<StatusBadge status={el.status} />} />
          {el.global_id && (
            <Row
              label="GlobalId"
              value={
                <span className="vt-detail__monospace">{el.global_id}</span>
              }
            />
          )}
          {el.element_type && <Row label="Type" value={el.element_type} />}
          {el.element_name && <Row label="Name" value={el.element_name} />}
        </tbody>
      </table>

      {el.messages.length > 0 && (
        <div className="vt-detail__messages">
          <div className="vt-detail__messages-label">Messages</div>
          <ul className="vt-detail__messages-list">
            {el.messages.map((msg, i) => (
              <li key={i} className="vt-detail__message">
                {msg}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="vt-detail__actions">
        {el.global_id && onZoom && (
          <button
            type="button"
            className="vt-detail__btn vt-detail__btn--zoom"
            onClick={handleZoom}
          >
            Zoom
          </button>
        )}
        {el.status === "fail" && onCreateBcf && (
          <button
            type="button"
            className="vt-detail__btn vt-detail__btn--bcf"
            onClick={() => onCreateBcf(spec, req, el)}
          >
            +BCF
          </button>
        )}
      </div>
    </>
  );
}

export function DetailPane({
  item,
  onElementZoom,
  onCreateBcfFromSpec,
  onCreateBcfFromRequirement,
  onCreateBcfFromElement,
}: DetailPaneProps) {
  return (
    <div className="vt-detail">
      {item.kind === "spec" && (
        <SpecDetail spec={item.spec} onCreateBcf={onCreateBcfFromSpec} />
      )}
      {item.kind === "requirement" && (
        <ReqDetail
          spec={item.spec}
          req={item.req}
          onCreateBcf={onCreateBcfFromRequirement}
        />
      )}
      {item.kind === "element" && (
        <ElDetail
          spec={item.spec}
          req={item.req}
          el={item.el}
          onZoom={onElementZoom}
          onCreateBcf={onCreateBcfFromElement}
        />
      )}
    </div>
  );
}
