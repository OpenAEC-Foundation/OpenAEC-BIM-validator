/**
 * SpatialSubTree — inline spatial hierarchy for a single model.
 *
 * Three levels of nesting:
 * 1. SpatialNode (Project/Site/Building/Storey/Space) — recursive, auto-expand depth < 2
 * 2. ElementTypeGroup ("Wall (23)") — lazy-loaded on first storey expand
 * 3. ElementItem — individual element, clickable → selectElement + zoom-to-element
 *
 * Data flow:
 * - Spatial tree comes from store (model.spatialTree)
 * - Contained elements are lazy-loaded via "contained-elements-request" event
 * - Element groups stored in local React state (not Zustand)
 */

import { useState, useCallback } from "react";

import { useStore } from "../../store";
import type { SpatialNode, ElementTypeGroup } from "../../types/project";

/** Max elements shown per group before "show all" button */
const ELEMENT_DISPLAY_LIMIT = 50;

interface SpatialSubTreeProps {
  tree: SpatialNode;
  engineModelId: string;
}

interface SpatialNodeProps {
  node: SpatialNode;
  depth: number;
  engineModelId: string;
}

interface ElementTypeGroupProps {
  group: ElementTypeGroup;
  depth: number;
}

/** A single clickable element */
function ElementItem({
  globalId,
  name,
  depth,
}: {
  globalId: string;
  name: string;
  depth: number;
}) {
  const selectElement = useStore((s) => s.selectElement);
  const selectedElementId = useStore((s) => s.selectedElementId);
  const isSelected = selectedElementId === globalId;

  const handleClick = useCallback(() => {
    selectElement(globalId);
    window.dispatchEvent(
      new CustomEvent("zoom-to-element", { detail: { globalId } })
    );
  }, [selectElement, globalId]);

  return (
    <div
      className={`spatial-node__row spatial-node__row--element ${
        isSelected ? "spatial-node__row--selected" : ""
      }`}
      style={{ paddingLeft: `${depth * 16 + 4}px` }}
    >
      <span className="spatial-node__toggle" style={{ visibility: "hidden" }} />
      <button
        type="button"
        className="spatial-node__label"
        onClick={handleClick}
        title={`${globalId}: ${name}`}
      >
        <span className="spatial-node__name">{name}</span>
      </button>
    </div>
  );
}

/** A group of elements of the same IFC type */
function ElementTypeGroupNode({ group, depth }: ElementTypeGroupProps) {
  const [expanded, setExpanded] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const visibleElements =
    showAll || group.elements.length <= ELEMENT_DISPLAY_LIMIT
      ? group.elements
      : group.elements.slice(0, ELEMENT_DISPLAY_LIMIT);

  return (
    <div className="spatial-node">
      <div
        className="spatial-node__row spatial-node__row--type-group"
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
      >
        <button
          type="button"
          className="spatial-node__toggle"
          onClick={() => setExpanded((p) => !p)}
          aria-label={expanded ? "Inklappen" : "Uitklappen"}
        >
          {expanded ? "\u25BE" : "\u25B8"}
        </button>
        <span className="spatial-node__label spatial-node__label--type-group">
          <span className="spatial-node__type-name">{group.displayName}</span>
          <span className="spatial-node__count">({group.count})</span>
        </span>
      </div>

      {expanded && (
        <div className="spatial-node__children">
          {visibleElements.map((el) => (
            <ElementItem
              key={el.globalId || el.expressId}
              globalId={el.globalId}
              name={el.name}
              depth={depth + 1}
            />
          ))}
          {!showAll && group.elements.length > ELEMENT_DISPLAY_LIMIT && (
            <div
              className="spatial-node__show-all"
              style={{ paddingLeft: `${(depth + 1) * 16 + 4}px` }}
            >
              <button
                type="button"
                className="spatial-node__show-all-btn"
                onClick={() => setShowAll(true)}
              >
                Toon alle ({group.elements.length})
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** A spatial node (Project/Site/Building/Storey/Space) */
function SpatialNodeItem({ node, depth, engineModelId }: SpatialNodeProps) {
  const [expanded, setExpanded] = useState(depth < 2);
  const [elementGroups, setElementGroups] = useState<
    ElementTypeGroup[] | null
  >(null);
  const [loadingElements, setLoadingElements] = useState(false);

  const selectElement = useStore((s) => s.selectElement);
  const selectedElementId = useStore((s) => s.selectedElementId);

  const hasChildren = node.children.length > 0 || node.elementCount > 0;
  const isSelected = selectedElementId === node.globalId;

  const handleToggle = useCallback(() => {
    const willExpand = !expanded;
    setExpanded(willExpand);

    // Lazy-load contained elements on first expand if this node has elements
    if (
      willExpand &&
      node.elementCount > 0 &&
      elementGroups === null &&
      !loadingElements
    ) {
      setLoadingElements(true);
      const requestId = `elements-${node.globalId}-${Date.now()}`;

      const handleResponse = (e: Event) => {
        const detail = (
          e as CustomEvent<{
            requestId: string;
            groups: ElementTypeGroup[];
            error: string | null;
          }>
        ).detail;
        if (detail.requestId !== requestId) return;

        window.removeEventListener(
          "contained-elements-response",
          handleResponse
        );
        setElementGroups(detail.groups ?? []);
        setLoadingElements(false);
      };

      window.addEventListener(
        "contained-elements-response",
        handleResponse
      );
      window.dispatchEvent(
        new CustomEvent("contained-elements-request", {
          detail: {
            engineModelId,
            spatialGlobalId: node.globalId,
            requestId,
          },
        })
      );
    }
  }, [expanded, node.globalId, node.elementCount, engineModelId, elementGroups, loadingElements]);

  const handleSelect = useCallback(() => {
    selectElement(node.globalId);
  }, [selectElement, node.globalId]);

  return (
    <div className="spatial-node">
      <div
        className={`spatial-node__row ${
          isSelected ? "spatial-node__row--selected" : ""
        }`}
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
      >
        <button
          type="button"
          className="spatial-node__toggle"
          onClick={handleToggle}
          style={{ visibility: hasChildren ? "visible" : "hidden" }}
          aria-label={expanded ? "Inklappen" : "Uitklappen"}
        >
          {expanded ? "\u25BE" : "\u25B8"}
        </button>

        <button
          type="button"
          className="spatial-node__label"
          onClick={handleSelect}
          title={`${node.type}: ${node.name}`}
        >
          <span className="spatial-node__type">
            {node.type.replace(/^IFC/, "")}
          </span>
          <span className="spatial-node__name">{node.name}</span>
          {node.elementCount > 0 && (
            <span className="spatial-node__count">
              ({node.elementCount})
            </span>
          )}
        </button>
      </div>

      {expanded && (
        <div className="spatial-node__children">
          {/* Child spatial nodes */}
          {node.children.map((child) => (
            <SpatialNodeItem
              key={child.globalId}
              node={child}
              depth={depth + 1}
              engineModelId={engineModelId}
            />
          ))}

          {/* Loading indicator for contained elements */}
          {loadingElements && (
            <div
              className="spatial-node__loading"
              style={{ paddingLeft: `${(depth + 1) * 16 + 4}px` }}
            >
              <span className="spatial-node__spinner" />
              <span className="spatial-node__loading-text">
                Elementen laden...
              </span>
            </div>
          )}

          {/* Element type groups */}
          {elementGroups?.map((group) => (
            <ElementTypeGroupNode
              key={group.type}
              group={group}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/** Main entry: inline spatial tree for one model */
export function SpatialSubTree({ tree, engineModelId }: SpatialSubTreeProps) {
  return (
    <div className="spatial-subtree">
      <SpatialNodeItem node={tree} depth={1} engineModelId={engineModelId} />
    </div>
  );
}
