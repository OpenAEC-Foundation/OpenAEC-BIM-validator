/**
 * SpatialTree — hierarchical tree view of IFC spatial structure.
 *
 * Renders the IfcProject -> IfcSite -> IfcBuilding -> IfcBuildingStorey
 * hierarchy. Each node is expandable and clickable.
 *
 * Spatial tree data comes from the backend (Fase 1 backend endpoint).
 * For now, shows a placeholder until the backend provides data.
 */

import { useState, useCallback } from "react";

import { useStore } from "../../store";
import type { SpatialNode } from "../../types/project";

import "./SpatialTree.css";

interface SpatialTreeNodeProps {
  node: SpatialNode;
  depth: number;
}

function SpatialTreeNode({ node, depth }: SpatialTreeNodeProps) {
  const [expanded, setExpanded] = useState(depth < 2);

  const selectElement = useStore((s) => s.selectElement);
  const selectedElementId = useStore((s) => s.selectedElementId);

  const hasChildren = node.children.length > 0;
  const isSelected = selectedElementId === node.globalId;

  const handleToggle = useCallback(() => {
    setExpanded((prev) => !prev);
  }, []);

  const handleSelect = useCallback(() => {
    selectElement(node.globalId);
  }, [selectElement, node.globalId]);

  return (
    <div className="spatial-node">
      <div
        className={`spatial-node__row ${isSelected ? "spatial-node__row--selected" : ""}`}
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
      >
        {/* Expand/collapse toggle */}
        <button
          type="button"
          className="spatial-node__toggle"
          onClick={handleToggle}
          style={{ visibility: hasChildren ? "visible" : "hidden" }}
          aria-label={expanded ? "Inklappen" : "Uitklappen"}
        >
          {expanded ? "-" : "+"}
        </button>

        {/* Node label */}
        <button
          type="button"
          className="spatial-node__label"
          onClick={handleSelect}
          title={`${node.type}: ${node.name}`}
        >
          <span className="spatial-node__type">{node.type.replace("Ifc", "")}</span>
          <span className="spatial-node__name">{node.name}</span>
          {node.elementCount > 0 && (
            <span className="spatial-node__count">({node.elementCount})</span>
          )}
        </button>
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div className="spatial-node__children">
          {node.children.map((child) => (
            <SpatialTreeNode
              key={child.globalId}
              node={child}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function SpatialTree() {
  const project = useStore((s) => s.project);

  // Collect spatial trees from all loaded models
  const spatialTrees =
    project?.models
      .filter((m) => m.spatialTree && m.loadState === "loaded")
      .map((m) => ({ modelId: m.id, tree: m.spatialTree! })) ?? [];

  if (spatialTrees.length === 0) {
    return null;
  }

  return (
    <div className="spatial-tree">
      <div className="spatial-tree__header">
        <h3 className="spatial-tree__title">Ruimtelijke structuur</h3>
      </div>
      {spatialTrees.map(({ modelId, tree }) => (
        <SpatialTreeNode key={modelId} node={tree} depth={0} />
      ))}
    </div>
  );
}
