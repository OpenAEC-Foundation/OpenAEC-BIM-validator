/**
 * ResultsTree — BIMcollab-style flat tree for validation results.
 *
 * Replaces the old card-based SpecificationList with compact 24px rows,
 * expand arrows, severity dots, and indentation levels.
 */

import { useState, useCallback, useMemo } from "react";

import type {
  SpecificationResult,
  RequirementResult,
  ElementResult,
  SelectedTreeItem,
} from "../types/validation";

/** Props for the ResultsTree component */
export interface ResultsTreeProps {
  specifications: SpecificationResult[];
  autoExpandFailed?: boolean;
  selectedItem: SelectedTreeItem | null;
  onItemSelect: (item: SelectedTreeItem) => void;
}

/** Severity → CSS color token */
function severityColor(severity: string): string {
  switch (severity) {
    case "error":
      return "var(--domain-fail)";
    case "warning":
      return "var(--domain-warning)";
    case "info":
      return "var(--theme-accent)";
    default:
      return "var(--theme-text-muted)";
  }
}

/** Format element display name */
function formatElementName(el: ElementResult): string {
  const parts: string[] = [];
  if (el.element_type) parts.push(el.element_type);
  if (el.element_name) parts.push(el.element_name);
  return parts.length > 0 ? parts.join(": ") : "Unknown Element";
}

/** Check if a tree item matches the current selection */
function isSelected(
  current: SelectedTreeItem | null,
  kind: SelectedTreeItem["kind"],
  spec: SpecificationResult,
  req?: RequirementResult,
  el?: ElementResult
): boolean {
  if (!current || current.kind !== kind) return false;
  if (current.spec !== spec) return false;
  if (kind === "requirement" && current.kind === "requirement") {
    return current.req === req;
  }
  if (kind === "element" && current.kind === "element") {
    return current.req === req && current.el === el;
  }
  return kind === "spec";
}

/** Specification row (level 0) */
function SpecRow({
  spec,
  expanded,
  selected,
  onToggle,
  onSelect,
}: {
  spec: SpecificationResult;
  expanded: boolean;
  selected: boolean;
  onToggle: () => void;
  onSelect: () => void;
}) {
  const isFail = spec.status === "fail";

  const handleClick = useCallback(() => {
    onSelect();
  }, [onSelect]);

  const handleToggle = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onToggle();
    },
    [onToggle]
  );

  return (
    <div
      className={`vt-row${selected ? " vt-row--selected" : ""}`}
      style={{ paddingLeft: 4 }}
      onClick={handleClick}
      role="treeitem"
      aria-expanded={expanded}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      <span
        className="vt-row__arrow"
        onClick={handleToggle}
        role="button"
        tabIndex={-1}
      >
        {expanded ? "\u25BC" : "\u25B6"}
      </span>
      <span
        className="vt-row__dot"
        style={{ backgroundColor: severityColor(spec.severity) }}
      />
      <span className="vt-row__label" title={spec.specification_name}>
        {spec.specification_name}
      </span>
      {isFail && (
        <span className="vt-row__count vt-row__count--fail">
          {spec.failed_requirements}
        </span>
      )}
      {!isFail && <span className="vt-row__count vt-row__count--pass">OK</span>}
    </div>
  );
}

/** Requirement row (level 1) */
function ReqRow({
  req,
  expanded,
  selected,
  onToggle,
  onSelect,
}: {
  req: RequirementResult;
  expanded: boolean;
  selected: boolean;
  onToggle: () => void;
  onSelect: () => void;
}) {
  const isFail = req.status === "fail";
  const hasChildren = req.elements.length > 0;

  const handleClick = useCallback(() => {
    onSelect();
  }, [onSelect]);

  const handleToggle = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onToggle();
    },
    [onToggle]
  );

  return (
    <div
      className={`vt-row${selected ? " vt-row--selected" : ""}`}
      style={{ paddingLeft: 24 }}
      onClick={handleClick}
      role="treeitem"
      aria-expanded={hasChildren ? expanded : undefined}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      {hasChildren ? (
        <span
          className="vt-row__arrow"
          onClick={handleToggle}
          role="button"
          tabIndex={-1}
        >
          {expanded ? "\u25BC" : "\u25B6"}
        </span>
      ) : (
        <span className="vt-row__arrow vt-row__arrow--empty" />
      )}
      <span
        className="vt-row__dot"
        style={{
          backgroundColor: isFail ? "var(--domain-fail)" : "var(--domain-pass)",
        }}
      />
      <span className="vt-row__label" title={req.requirement_description}>
        {req.requirement_description}
      </span>
      {isFail && (
        <span className="vt-row__count vt-row__count--fail">
          {req.failed_elements}
        </span>
      )}
    </div>
  );
}

/** Element row (level 2) */
function ElRow({
  el,
  selected,
  onSelect,
}: {
  el: ElementResult;
  selected: boolean;
  onSelect: () => void;
}) {
  const isFail = el.status === "fail";

  return (
    <div
      className={`vt-row${selected ? " vt-row--selected" : ""}`}
      style={{ paddingLeft: 44 }}
      onClick={onSelect}
      role="treeitem"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
    >
      <span className="vt-row__arrow vt-row__arrow--empty" />
      <span
        className="vt-row__dot"
        style={{
          backgroundColor: isFail ? "var(--domain-fail)" : "var(--domain-pass)",
        }}
      />
      <span className="vt-row__label" title={formatElementName(el)}>
        {formatElementName(el)}
      </span>
      {el.global_id && (
        <span className="vt-row__gid" title={el.global_id}>
          {el.global_id.slice(0, 8)}
        </span>
      )}
    </div>
  );
}

/**
 * ResultsTree — flat tree displaying validation specifications,
 * requirements, and elements.
 */
export function ResultsTree({
  specifications,
  autoExpandFailed = true,
  selectedItem,
  onItemSelect,
}: ResultsTreeProps) {
  // Sort: failed first
  const sorted = useMemo(
    () =>
      [...specifications].sort((a, b) => {
        if (a.status === "fail" && b.status === "pass") return -1;
        if (a.status === "pass" && b.status === "fail") return 1;
        return 0;
      }),
    [specifications]
  );

  // Track expanded state per spec/req by reference identity
  const [expandedSpecs, setExpandedSpecs] = useState<Set<SpecificationResult>>(
    () => {
      const initial = new Set<SpecificationResult>();
      if (autoExpandFailed) {
        for (const s of specifications) {
          if (s.status === "fail") initial.add(s);
        }
      }
      return initial;
    }
  );

  const [expandedReqs, setExpandedReqs] = useState<Set<RequirementResult>>(
    () => new Set()
  );

  const toggleSpec = useCallback((spec: SpecificationResult) => {
    setExpandedSpecs((prev) => {
      const next = new Set(prev);
      if (next.has(spec)) next.delete(spec);
      else next.add(spec);
      return next;
    });
  }, []);

  const toggleReq = useCallback((req: RequirementResult) => {
    setExpandedReqs((prev) => {
      const next = new Set(prev);
      if (next.has(req)) next.delete(req);
      else next.add(req);
      return next;
    });
  }, []);

  if (specifications.length === 0) {
    return (
      <div className="vt-tree vt-tree--empty">
        <p className="vt-tree__empty-msg">Geen specificaties gevonden.</p>
      </div>
    );
  }

  return (
    <div className="vt-tree" role="tree" aria-label="Validation Results">
      {sorted.map((spec) => {
        const specExpanded = expandedSpecs.has(spec);

        return (
          <div key={spec.specification_name} role="group">
            <SpecRow
              spec={spec}
              expanded={specExpanded}
              selected={isSelected(selectedItem, "spec", spec)}
              onToggle={() => toggleSpec(spec)}
              onSelect={() => onItemSelect({ kind: "spec", spec })}
            />
            {specExpanded &&
              spec.requirements.map((req, ri) => {
                const reqExpanded = expandedReqs.has(req);
                const failedEls = req.elements.filter(
                  (e) => e.status === "fail"
                );
                const passedEls = req.elements.filter(
                  (e) => e.status === "pass"
                );
                const orderedEls = [...failedEls, ...passedEls];

                return (
                  <div key={`${spec.specification_name}-req-${ri}`} role="group">
                    <ReqRow
                      req={req}
                      expanded={reqExpanded}
                      selected={isSelected(
                        selectedItem,
                        "requirement",
                        spec,
                        req
                      )}
                      onToggle={() => toggleReq(req)}
                      onSelect={() =>
                        onItemSelect({ kind: "requirement", spec, req })
                      }
                    />
                    {reqExpanded &&
                      orderedEls.map((el, ei) => (
                        <ElRow
                          key={el.global_id ?? `el-${ei}`}
                          el={el}
                          selected={isSelected(
                            selectedItem,
                            "element",
                            spec,
                            req,
                            el
                          )}
                          onSelect={() =>
                            onItemSelect({ kind: "element", spec, req, el })
                          }
                        />
                      ))}
                  </div>
                );
              })}
          </div>
        );
      })}
    </div>
  );
}

/** Legacy props for backward compatibility with LegacyValidationView */
export interface SpecificationListProps {
  specifications: SpecificationResult[];
  autoExpandFailed?: boolean;
}

/**
 * Legacy SpecificationList wrapper — provides the old API surface
 * (no selection state) for LegacyValidationView.
 */
export function SpecificationList({
  specifications,
  autoExpandFailed,
}: SpecificationListProps) {
  const [selected, setSelected] = useState<SelectedTreeItem | null>(null);
  return (
    <ResultsTree
      specifications={specifications}
      autoExpandFailed={autoExpandFailed}
      selectedItem={selected}
      onItemSelect={setSelected}
    />
  );
}

export default SpecificationList;
