/**
 * PropertiesPanel — BIMcollab-style tabbed IFC property viewer.
 *
 * Tabs: Info | Psets | Qto | Type
 * Uses client-side web-ifc extraction via PropertyExtractor.
 */

import { useState, useEffect, useRef, useCallback } from "react";

import { useStore } from "../../store";
import { isDemoMode } from "../../demo/useDemoMode";
import type { IfcElementProperties } from "../../engine/PropertyExtractor";

import "./PropertiesPanel.css";

/** Property tab IDs */
type PropsTab = "info" | "psets" | "qto" | "type";

const TABS: { id: PropsTab; label: string }[] = [
  { id: "info", label: "Info" },
  { id: "psets", label: "Psets" },
  { id: "qto", label: "Qto" },
  { id: "type", label: "Type" },
];

/** Demo properties for presentation mode */
const DEMO_PROPERTIES: IfcElementProperties = {
  globalId: "2O2Fr$t4X7Zf8NOew3FLOH",
  entityType: "IFCWALL",
  name: "Basiswand: Beton 200",
  description: "Dragende betonwand, 200mm",
  tag: "W-001",
  predefinedType: "STANDARD",
  objectType: "Beton 200mm",
  location: { storey: "Verdieping 1", building: "Kantoor", site: "Locatie A" },
  materials: [
    { name: "Beton C30/37", thickness: 150, category: "Concrete" },
    { name: "Isolatie EPS", thickness: 50, category: "Insulation" },
  ],
  typeName: "Beton 200mm",
  typeProperties: {
    TypeEntity: "IFCWALLTYPE",
    ElementType: "Betonwand",
    PredefinedType: "STANDARD",
  },
  typePropertySets: [
    {
      name: "Pset_WallCommon",
      properties: {
        Reference: "Beton 200",
        IsExternal: true,
        LoadBearing: true,
        FireRating: "REI 120",
      },
    },
  ],
  classifications: [
    { system: "NL-SfB", reference: "21.22", name: "Wanden; beton" },
  ],
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
      name: "Pset_EnvironmentalImpactValues",
      properties: {
        MWD: "3.2 MJ/m2",
        GWP: "42.5 kg CO2e/m2",
        LebensdauerRef: 75,
      },
    },
  ],
  quantities: [
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
  ],
};

/** Collapsible section within a tab */
function Section({
  title,
  defaultOpen = true,
  children,
  count,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  count?: number;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="props-section">
      <button
        type="button"
        className="props-section__toggle"
        onClick={() => setOpen(!open)}
      >
        <span className="props-section__arrow">
          {open ? "\u25BE" : "\u25B8"}
        </span>
        <span className="props-section__title">{title}</span>
        {count !== undefined && (
          <span className="props-section__count">{count}</span>
        )}
      </button>
      {open && <div className="props-section__body">{children}</div>}
    </div>
  );
}

/** Key-value table */
function PropertyTable({
  properties,
}: {
  properties: Record<string, unknown>;
}) {
  const entries = Object.entries(properties);
  if (entries.length === 0) return null;

  return (
    <table className="props-table">
      <tbody>
        {entries.map(([key, value]) => (
          <tr key={key}>
            <td className="props-table__key">{key}</td>
            <td className="props-table__value">{formatValue(value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function PropertiesPanel() {
  const selectedElementId = useStore((s) => s.selectedElementId);
  const viewerReady = useStore((s) => s.viewerReady);

  const [properties, setProperties] = useState<IfcElementProperties | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<PropsTab>("info");
  const requestIdRef = useRef(0);

  /** Request properties via custom event to CenterPanel */
  const fetchProperties = useCallback(
    (globalId: string) => {
      if (!viewerReady) {
        setError("Viewer niet gereed");
        return;
      }

      const requestId = String(++requestIdRef.current);
      setLoading(true);
      setError(null);

      const handleResponse = (e: Event) => {
        const detail = (
          e as CustomEvent<{
            requestId: string;
            properties: IfcElementProperties | null;
            error: string | null;
          }>
        ).detail;

        if (detail.requestId !== requestId) return;
        window.removeEventListener("property-response", handleResponse);

        if (detail.error) {
          setError(detail.error);
          setProperties(null);
        } else {
          setProperties(detail.properties);
        }
        setLoading(false);
      };

      window.addEventListener("property-response", handleResponse);
      window.dispatchEvent(
        new CustomEvent("property-request", {
          detail: { globalId, requestId },
        })
      );

      setTimeout(() => {
        window.removeEventListener("property-response", handleResponse);
      }, 15000);
    },
    [viewerReady]
  );

  useEffect(() => {
    setProperties(null);
    setError(null);
    setLoading(false);
    setActiveTab("info");

    if (!selectedElementId) return;

    if (isDemoMode()) {
      setProperties(DEMO_PROPERTIES);
      return;
    }

    fetchProperties(selectedElementId);
  }, [selectedElementId, fetchProperties]);

  // Empty state
  if (!selectedElementId) {
    return (
      <div className="empty-state empty-state--compact">
        <p className="empty-state__text">Selecteer een element in 3D</p>
      </div>
    );
  }

  // Loading
  if (loading) {
    return (
      <div className="props-panel">
        <div className="props-panel__header">
          <span className="props-panel__type">Element</span>
          <span className="props-panel__id">{selectedElementId}</span>
        </div>
        <p className="props-panel__status">Properties laden...</p>
      </div>
    );
  }

  // Error
  if (error) {
    return (
      <div className="props-panel">
        <div className="props-panel__header">
          <span className="props-panel__type">Element</span>
          <span className="props-panel__id">{selectedElementId}</span>
        </div>
        <p className="props-panel__status props-panel__status--error">{error}</p>
      </div>
    );
  }

  // No data
  if (!properties) {
    return (
      <div className="props-panel">
        <div className="props-panel__header">
          <span className="props-panel__type">Element</span>
          <span className="props-panel__id">{selectedElementId}</span>
        </div>
        <p className="props-panel__status">Geen properties gevonden</p>
      </div>
    );
  }

  // Compute tab badge counts
  const psetCount = properties.propertySets.length;
  const qtoCount = properties.quantities.length;
  const typeCount =
    (properties.typeName ? 1 : 0) +
    properties.typePropertySets.length;

  return (
    <div className="props-panel">
      {/* Header: entity badge + name + globalId */}
      <div className="props-panel__header">
        <span className="props-panel__type">{properties.entityType}</span>
        <h3 className="props-panel__name">
          {properties.name ?? "Naamloos"}
        </h3>
        <span className="props-panel__id">{properties.globalId}</span>
      </div>

      {/* Tab bar */}
      <div className="props-tabs">
        {TABS.map((tab) => {
          const badge =
            tab.id === "psets"
              ? psetCount
              : tab.id === "qto"
                ? qtoCount
                : tab.id === "type"
                  ? typeCount
                  : undefined;

          return (
            <button
              key={tab.id}
              type="button"
              className={`props-tabs__tab ${activeTab === tab.id ? "props-tabs__tab--active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
              {badge !== undefined && badge > 0 && (
                <span className="props-tabs__badge">{badge}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="props-panel__body">
        {activeTab === "info" && <InfoTab properties={properties} />}
        {activeTab === "psets" && <PsetsTab properties={properties} />}
        {activeTab === "qto" && <QtoTab properties={properties} />}
        {activeTab === "type" && <TypeTab properties={properties} />}
      </div>
    </div>
  );
}

/** Info tab: identity, location, material summary, classifications */
function InfoTab({ properties }: { properties: IfcElementProperties }) {
  const hasLocation =
    properties.location.storey ||
    properties.location.building ||
    properties.location.site;

  const identityProps: Record<string, unknown> = {};
  if (properties.objectType) identityProps["ObjectType"] = properties.objectType;
  if (properties.predefinedType) identityProps["PredefinedType"] = properties.predefinedType;
  if (properties.description) identityProps["Description"] = properties.description;
  if (properties.tag) identityProps["Tag"] = properties.tag;

  return (
    <>
      {/* Identity */}
      {Object.keys(identityProps).length > 0 && (
        <Section title="Identity">
          <PropertyTable properties={identityProps} />
        </Section>
      )}

      {/* Location */}
      {hasLocation && (
        <Section title="Location">
          <PropertyTable
            properties={{
              ...(properties.location.storey ? { Storey: properties.location.storey } : {}),
              ...(properties.location.building ? { Building: properties.location.building } : {}),
              ...(properties.location.site ? { Site: properties.location.site } : {}),
            }}
          />
        </Section>
      )}

      {/* Materials */}
      {properties.materials.length > 0 && (
        <Section title="Material" count={properties.materials.length}>
          <table className="props-table">
            <tbody>
              {properties.materials.map((mat, i) => (
                <tr key={i}>
                  <td className="props-table__key">{mat.name}</td>
                  <td className="props-table__value">
                    {mat.thickness != null
                      ? `${mat.thickness} mm`
                      : mat.category ?? ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}

      {/* Classifications */}
      {properties.classifications.length > 0 && (
        <Section title="Classification" count={properties.classifications.length}>
          <table className="props-table">
            <tbody>
              {properties.classifications.map((c, i) => (
                <tr key={i}>
                  <td className="props-table__key">
                    {c.system || "—"}
                  </td>
                  <td className="props-table__value">
                    {c.reference}
                    {c.name ? ` — ${c.name}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}
    </>
  );
}

/** Psets tab: all property sets in collapsible sections */
function PsetsTab({ properties }: { properties: IfcElementProperties }) {
  if (properties.propertySets.length === 0) {
    return <p className="props-panel__status">Geen property sets</p>;
  }

  return (
    <>
      {properties.propertySets.map((pset, i) => (
        <Section
          key={`${pset.name}-${i}`}
          title={pset.name}
          defaultOpen={i < 4}
          count={Object.keys(pset.properties).length}
        >
          <PropertyTable properties={pset.properties} />
        </Section>
      ))}
    </>
  );
}

/** Qto tab: all quantity sets in collapsible sections */
function QtoTab({ properties }: { properties: IfcElementProperties }) {
  if (properties.quantities.length === 0) {
    return <p className="props-panel__status">Geen quantities</p>;
  }

  return (
    <>
      {properties.quantities.map((qset, i) => (
        <Section
          key={`${qset.name}-${i}`}
          title={qset.name}
          defaultOpen
          count={Object.keys(qset.properties).length}
        >
          <PropertyTable properties={qset.properties} />
        </Section>
      ))}
    </>
  );
}

/** Type tab: type identity + type property sets */
function TypeTab({ properties }: { properties: IfcElementProperties }) {
  const hasTypeAttrs = Object.keys(properties.typeProperties).length > 0;

  if (!properties.typeName && !hasTypeAttrs && properties.typePropertySets.length === 0) {
    return <p className="props-panel__status">Geen type informatie</p>;
  }

  return (
    <>
      {/* Type identity */}
      {(properties.typeName || hasTypeAttrs) && (
        <Section title={properties.typeName ?? "Type"}>
          {hasTypeAttrs && (
            <PropertyTable properties={properties.typeProperties} />
          )}
        </Section>
      )}

      {/* Type property sets */}
      {properties.typePropertySets.map((pset, i) => (
        <Section
          key={`${pset.name}-${i}`}
          title={pset.name}
          defaultOpen
          count={Object.keys(pset.properties).length}
        >
          <PropertyTable properties={pset.properties} />
        </Section>
      ))}
    </>
  );
}

/** Format a property value for display */
function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "\u2014";
  if (typeof value === "boolean") return value ? "Ja" : "Nee";
  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toLocaleString("nl-NL")
      : value.toLocaleString("nl-NL", { maximumFractionDigits: 3 });
  }
  return String(value);
}
