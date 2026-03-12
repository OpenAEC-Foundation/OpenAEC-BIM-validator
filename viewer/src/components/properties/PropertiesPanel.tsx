/**
 * PropertiesPanel — shows properties of the selected element.
 *
 * Displays property sets, type properties, and material info
 * for the element selected in the 3D viewer.
 *
 * Fetches properties from the backend API when a backend model ID
 * is available. Falls back to demo data in demo mode.
 */

import { useState, useEffect, useRef } from "react";

import { useStore } from "../../store";
import { isDemoMode } from "../../demo/useDemoMode";
import { getElementProperties } from "../../api/projectApi";
import type { ElementProperties } from "../../types/project";

import "./PropertiesPanel.css";

/** Demo properties for presentation screenshots */
const DEMO_PROPERTIES: ElementProperties = {
  globalId: "2O2Fr$t4X7Zf8NOew3FLOH",
  entityType: "IfcWall",
  name: "Basiswand: Beton 200",
  modelId: "demo-model-arc",
  propertySets: [
    {
      name: "Pset_WallCommon",
      properties: {
        Reference: "Beton 200",
        IsExternal: true,
        LoadBearing: true,
        FireRating: "REI 120",
        ThermalTransmittance: 0.28,
        AcousticRating: "Rw 52 dB",
      },
    },
    {
      name: "BaseQuantities",
      properties: {
        Length: 4200,
        Height: 3600,
        Width: 200,
        GrossArea: 15.12,
        NetArea: 13.86,
        GrossVolume: 3.024,
        NetVolume: 2.772,
      },
    },
    {
      name: "Pset_EnvironmentalImpactValues",
      properties: {
        MWD: "3.2 MJ/m2",
        GWP: "42.5 kg CO2e/m2",
        LebensdauerRef: 75,
      },
    },
  ],
  typeProperties: {
    TypeName: "Beton 200mm",
    Manufacturer: "In-situ gestort",
    Betondekking: "30mm",
    Wapeningstype: "B500B",
  },
  material: "Beton C30/37 (200mm)",
};

export function PropertiesPanel() {
  const selectedElementId = useStore((s) => s.selectedElementId);
  const project = useStore((s) => s.project);

  const [properties, setProperties] = useState<ElementProperties | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fetchIdRef = useRef(0);

  /** Find the backend model ID (only available when uploaded via v2 API) */
  const backendModelId = project?.models.find(
    (m) => m.loadState === "loaded"
  )?.backendModelId ?? null;

  useEffect(() => {
    setProperties(null);
    setError(null);
    setLoading(false);

    if (!selectedElementId) return;

    // Demo mode: use static data
    if (isDemoMode()) {
      setProperties(DEMO_PROPERTIES);
      return;
    }

    // No backend model → can't fetch properties
    if (!backendModelId) {
      setError("Properties niet beschikbaar (model niet via project-API geladen)");
      return;
    }

    const currentFetchId = ++fetchIdRef.current;
    setLoading(true);

    getElementProperties(backendModelId, selectedElementId)
      .then((data) => {
        if (fetchIdRef.current !== currentFetchId) return;
        setProperties(data);
        setLoading(false);
      })
      .catch((err) => {
        if (fetchIdRef.current !== currentFetchId) return;
        const msg = err instanceof Error ? err.message : "Ophalen mislukt";
        setError(msg);
        setLoading(false);
      });
  }, [selectedElementId, backendModelId]);

  if (!selectedElementId) {
    return (
      <div className="empty-state">
        <p className="empty-state__text">
          Klik op een element in de 3D viewer om properties te bekijken
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="properties-panel">
        <div className="properties-panel__header">
          <span className="properties-panel__type">Element</span>
          <span className="properties-panel__id">{selectedElementId}</span>
        </div>
        <p className="properties-panel__placeholder">
          Properties laden...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="properties-panel">
        <div className="properties-panel__header">
          <span className="properties-panel__type">Element</span>
          <span className="properties-panel__id">{selectedElementId}</span>
        </div>
        <p className="properties-panel__placeholder">{error}</p>
      </div>
    );
  }

  if (!properties) {
    return (
      <div className="properties-panel">
        <div className="properties-panel__header">
          <span className="properties-panel__type">Element</span>
          <span className="properties-panel__id">{selectedElementId}</span>
        </div>
        <p className="properties-panel__placeholder">
          Geen properties gevonden
        </p>
      </div>
    );
  }

  return (
    <div className="properties-panel">
      {/* Element header */}
      <div className="properties-panel__header">
        <span className="properties-panel__type">{properties.entityType}</span>
        <h3 className="properties-panel__name">{properties.name ?? "Naamloos"}</h3>
        <span className="properties-panel__id">{properties.globalId}</span>
      </div>

      {/* Material */}
      {properties.material && (
        <div className="properties-panel__section">
          <h4 className="properties-panel__section-title">Materiaal</h4>
          <p className="properties-panel__material">{properties.material}</p>
        </div>
      )}

      {/* Type properties */}
      {properties.typeProperties &&
        Object.keys(properties.typeProperties).length > 0 && (
          <div className="properties-panel__section">
            <h4 className="properties-panel__section-title">Type Properties</h4>
            <table className="properties-panel__table">
              <tbody>
                {Object.entries(properties.typeProperties).map(
                  ([key, value]) => (
                    <tr key={key}>
                      <td className="properties-panel__key">{key}</td>
                      <td className="properties-panel__value">
                        {formatValue(value)}
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        )}

      {/* Property sets */}
      {properties.propertySets.map((pset) => (
        <div key={pset.name} className="properties-panel__section">
          <h4 className="properties-panel__section-title">{pset.name}</h4>
          <table className="properties-panel__table">
            <tbody>
              {Object.entries(pset.properties).map(([key, value]) => (
                <tr key={key}>
                  <td className="properties-panel__key">{key}</td>
                  <td className="properties-panel__value">
                    {formatValue(value)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

/** Format a property value for display */
function formatValue(value: string | number | boolean | null): string {
  if (value === null) return "—";
  if (typeof value === "boolean") return value ? "Ja" : "Nee";
  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toLocaleString("nl-NL")
      : value.toLocaleString("nl-NL", { maximumFractionDigits: 3 });
  }
  return String(value);
}
