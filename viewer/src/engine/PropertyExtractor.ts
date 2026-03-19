/**
 * PropertyExtractor — Client-side IFC property extraction via web-ifc.
 *
 * Opens the raw IFC bytes with web-ifc IfcAPI and extracts ALL properties
 * for a given element (by GlobalId). No backend required.
 *
 * Lazy initialization: the web-ifc model is only opened on first request.
 */

import * as WebIfc from "web-ifc";

const WASM_PATH = "https://unpkg.com/web-ifc@0.0.77/";

/** Material layer/constituent with optional details */
export interface MaterialInfo {
  name: string;
  thickness?: number;
  category?: string;
  isVentilated?: boolean;
}

/** Classification reference */
export interface ClassificationRef {
  system: string;
  reference: string;
  name?: string;
}

/** Structured IFC element properties */
export interface IfcElementProperties {
  globalId: string;
  entityType: string;
  name: string | null;
  description: string | null;
  tag: string | null;
  predefinedType: string | null;
  objectType: string | null;
  location: { storey?: string; building?: string; site?: string };
  materials: MaterialInfo[];
  typeName: string | null;
  typeProperties: Record<string, unknown>;
  typePropertySets: Array<{
    name: string;
    properties: Record<string, unknown>;
  }>;
  classifications: ClassificationRef[];
  /** Instance property sets (Pset_*, custom) */
  propertySets: Array<{
    name: string;
    properties: Record<string, unknown>;
  }>;
  /** Quantity sets (Qto_*, BaseQuantities) — separate from psets */
  quantities: Array<{
    name: string;
    properties: Record<string, unknown>;
  }>;
}

/** IFC type codes for spatial elements */
const SPATIAL_TYPES = {
  IFCBUILDINGSTOREY: WebIfc.IFCBUILDINGSTOREY,
  IFCBUILDING: WebIfc.IFCBUILDING,
  IFCSITE: WebIfc.IFCSITE,
};

/**
 * Extracts properties from an IFC file loaded in memory.
 */
export class PropertyExtractor {
  private ifcApi: WebIfc.IfcAPI | null = null;
  private modelId = 0;
  private initialized = false;
  private initPromise: Promise<void> | null = null;
  private ifcBytes: Uint8Array;

  /** Cache: GlobalId → expressID for fast lookups */
  private globalIdIndex = new Map<string, number>();

  /** Reverse lookup cache: IFC type code → entity name */
  private typeNameCache = new Map<number, string>();

  constructor(bytes: Uint8Array) {
    this.ifcBytes = bytes;
  }

  /**
   * Lazy init: open the IFC model with web-ifc on first use.
   */
  private async ensureInit(): Promise<void> {
    if (this.initialized) return;
    if (this.initPromise) return this.initPromise;

    this.initPromise = this._init();
    await this.initPromise;
  }

  private async _init(): Promise<void> {
    const api = new WebIfc.IfcAPI();
    api.SetWasmPath(WASM_PATH, true);
    await api.Init();

    this.modelId = api.OpenModel(this.ifcBytes);
    this.ifcApi = api;
    this.buildGlobalIdIndex();
    this.buildTypeNameCache();
    this.initialized = true;
  }

  /**
   * Build an index mapping GlobalId → expressID for all products.
   */
  private buildGlobalIdIndex(): void {
    if (!this.ifcApi) return;

    const allLines = this.ifcApi.GetAllLines(this.modelId);
    for (let i = 0; i < allLines.size(); i++) {
      const expressId = allLines.get(i);
      try {
        const props = this.ifcApi.GetLine(this.modelId, expressId, false);
        if (props?.GlobalId?.value) {
          this.globalIdIndex.set(props.GlobalId.value, expressId);
        }
      } catch {
        // Skip non-entity lines
      }
    }
  }

  /**
   * Build reverse lookup for IFC type codes → names.
   */
  private buildTypeNameCache(): void {
    for (const [key, value] of Object.entries(WebIfc)) {
      if (
        typeof value === "number" &&
        key.startsWith("IFC") &&
        key === key.toUpperCase()
      ) {
        this.typeNameCache.set(value, key);
      }
    }
  }

  /**
   * Get ALL properties for an element by GlobalId.
   */
  async getProperties(globalId: string): Promise<IfcElementProperties | null> {
    await this.ensureInit();
    if (!this.ifcApi) return null;

    const expressId = this.globalIdIndex.get(globalId);
    if (expressId === undefined) return null;

    try {
      const element = this.ifcApi.GetLine(this.modelId, expressId, false);
      if (!element) return null;

      const entityType = this.getEntityTypeName(element.type);

      const result: IfcElementProperties = {
        globalId,
        entityType,
        name: this.extractStringValue(element.Name),
        description: this.extractStringValue(element.Description),
        tag: this.extractStringValue(element.Tag),
        predefinedType: this.extractEnumValue(element.PredefinedType),
        objectType: this.extractStringValue(element.ObjectType),
        location: this.extractLocation(expressId),
        materials: [],
        typeName: null,
        typeProperties: {},
        typePropertySets: [],
        classifications: this.extractClassifications(expressId),
        propertySets: [],
        quantities: [],
      };

      // Extract type info (also checks type for materials)
      this.extractTypeInfo(expressId, result);

      // Extract property sets and quantities (separate)
      this.extractPropertySetsAndQuantities(expressId, result);

      // Extract materials (instance level — may also come from type)
      const instanceMaterials = this.extractMaterials(expressId);
      if (instanceMaterials.length > 0) {
        result.materials = instanceMaterials;
      } else if (result.materials.length === 0) {
        // Try type-level materials (already set in extractTypeInfo if found)
      }

      return result;
    } catch (err) {
      console.warn("[PropertyExtractor] Error extracting properties:", err);
      return null;
    }
  }

  /**
   * Get the IFC entity type name from the numeric type code.
   */
  private getEntityTypeName(typeCode: number): string {
    return this.typeNameCache.get(typeCode) ?? `IFC_TYPE_${typeCode}`;
  }

  /**
   * Extract spatial containment: IfcBuildingStorey → IfcBuilding → IfcSite.
   */
  private extractLocation(
    expressId: number
  ): IfcElementProperties["location"] {
    if (!this.ifcApi) return {};

    const location: IfcElementProperties["location"] = {};

    try {
      const relLines = this.ifcApi.GetLineIDsWithType(
        this.modelId,
        WebIfc.IFCRELCONTAINEDINSPATIALSTRUCTURE
      );

      for (let i = 0; i < relLines.size(); i++) {
        const relId = relLines.get(i);
        const rel = this.ifcApi.GetLine(this.modelId, relId, false);
        if (!rel?.RelatedElements) continue;

        const elements = this.toArray(rel.RelatedElements);
        if (elements.some((el) => el?.value === expressId) && rel.RelatingStructure?.value) {
          this.resolveContainment(rel.RelatingStructure.value, location);
          break;
        }
      }
    } catch {
      // Spatial containment extraction failed
    }

    return location;
  }

  /**
   * Walk up the spatial hierarchy from the containing structure.
   */
  private resolveContainment(
    structureId: number,
    location: IfcElementProperties["location"]
  ): void {
    if (!this.ifcApi) return;

    try {
      const structure = this.ifcApi.GetLine(this.modelId, structureId, false);
      if (!structure) return;

      const name = this.extractStringValue(structure.Name) ?? "?";

      if (structure.type === SPATIAL_TYPES.IFCBUILDINGSTOREY) {
        location.storey = name;
      } else if (structure.type === SPATIAL_TYPES.IFCBUILDING) {
        location.building = name;
      } else if (structure.type === SPATIAL_TYPES.IFCSITE) {
        location.site = name;
      }

      // Walk up via IfcRelAggregates
      const relLines = this.ifcApi.GetLineIDsWithType(
        this.modelId,
        WebIfc.IFCRELAGGREGATES
      );

      for (let i = 0; i < relLines.size(); i++) {
        const relId = relLines.get(i);
        const rel = this.ifcApi.GetLine(this.modelId, relId, false);
        if (!rel?.RelatedObjects) continue;

        const related = this.toArray(rel.RelatedObjects);
        if (related.some((obj) => obj?.value === structureId) && rel.RelatingObject?.value) {
          this.resolveContainment(rel.RelatingObject.value, location);
          break;
        }
      }
    } catch {
      // Walk up failed
    }
  }

  /**
   * Extract materials via IfcRelAssociatesMaterial.
   * Returns detailed material info with thickness where available.
   */
  private extractMaterials(expressId: number): MaterialInfo[] {
    if (!this.ifcApi) return [];

    const materials: MaterialInfo[] = [];

    try {
      const relLines = this.ifcApi.GetLineIDsWithType(
        this.modelId,
        WebIfc.IFCRELASSOCIATESMATERIAL
      );

      for (let i = 0; i < relLines.size(); i++) {
        const relId = relLines.get(i);
        const rel = this.ifcApi.GetLine(this.modelId, relId, false);
        if (!rel?.RelatedObjects) continue;

        const objects = this.toArray(rel.RelatedObjects);
        if (objects.some((obj) => obj?.value === expressId) && rel.RelatingMaterial?.value) {
          this.resolveMaterial(rel.RelatingMaterial.value, materials);
          break;
        }
      }
    } catch {
      // Material extraction failed
    }

    return materials;
  }

  /**
   * Resolve a material reference to MaterialInfo entries.
   */
  private resolveMaterial(materialId: number, materials: MaterialInfo[]): void {
    if (!this.ifcApi) return;

    try {
      const mat = this.ifcApi.GetLine(this.modelId, materialId, false);
      if (!mat) return;

      // IfcMaterial — single material
      if (mat.Name?.value && !mat.ForLayerSet && !mat.MaterialLayers && !mat.MaterialConstituents) {
        materials.push({
          name: mat.Name.value,
          category: this.extractStringValue(mat.Category) ?? undefined,
        });
        return;
      }

      // IfcMaterialLayerSetUsage → IfcMaterialLayerSet
      if (mat.ForLayerSet?.value) {
        this.resolveMaterial(mat.ForLayerSet.value, materials);
        return;
      }

      // IfcMaterialLayerSet → layers
      if (mat.MaterialLayers) {
        const layers = this.toArray(mat.MaterialLayers);
        for (const layerRef of layers) {
          if (!layerRef?.value) continue;
          const layer = this.ifcApi.GetLine(this.modelId, layerRef.value, false);
          if (!layer) continue;

          const info: MaterialInfo = { name: "?" };

          if (layer.Material?.value) {
            const layerMat = this.ifcApi.GetLine(this.modelId, layer.Material.value, false);
            if (layerMat?.Name?.value) info.name = layerMat.Name.value;
            if (layerMat?.Category?.value) info.category = layerMat.Category.value;
          }

          if (layer.LayerThickness?.value != null) {
            info.thickness = layer.LayerThickness.value;
          }
          if (layer.IsVentilated?.value != null) {
            info.isVentilated = layer.IsVentilated.value === true || layer.IsVentilated.value === "TRUE";
          }

          materials.push(info);
        }
        return;
      }

      // IfcMaterialConstituentSet → constituents
      if (mat.MaterialConstituents) {
        const constituents = this.toArray(mat.MaterialConstituents);
        for (const cRef of constituents) {
          if (!cRef?.value) continue;
          const constituent = this.ifcApi.GetLine(this.modelId, cRef.value, false);
          if (!constituent) continue;

          const info: MaterialInfo = { name: "?" };

          if (constituent.Material?.value) {
            const cMat = this.ifcApi.GetLine(this.modelId, constituent.Material.value, false);
            if (cMat?.Name?.value) info.name = cMat.Name.value;
            if (cMat?.Category?.value) info.category = cMat.Category.value;
          }

          if (constituent.Name?.value) {
            info.category = constituent.Name.value;
          }

          materials.push(info);
        }
        return;
      }

      // IfcMaterialProfileSetUsage → IfcMaterialProfileSet
      if (mat.ForProfileSet?.value) {
        this.resolveMaterial(mat.ForProfileSet.value, materials);
        return;
      }

      // IfcMaterialProfileSet → profiles
      if (mat.MaterialProfiles) {
        const profiles = this.toArray(mat.MaterialProfiles);
        for (const pRef of profiles) {
          if (!pRef?.value) continue;
          const profile = this.ifcApi.GetLine(this.modelId, pRef.value, false);
          if (!profile) continue;

          const info: MaterialInfo = { name: "?" };
          if (profile.Material?.value) {
            const pMat = this.ifcApi.GetLine(this.modelId, profile.Material.value, false);
            if (pMat?.Name?.value) info.name = pMat.Name.value;
          }
          if (profile.Name?.value) info.category = profile.Name.value;
          materials.push(info);
        }
        return;
      }

      // IfcMaterialList (IFC2X3 fallback)
      if (mat.Materials) {
        const matList = this.toArray(mat.Materials);
        for (const mRef of matList) {
          if (mRef?.value) {
            const m = this.ifcApi.GetLine(this.modelId, mRef.value, false);
            if (m?.Name?.value) {
              materials.push({ name: m.Name.value });
            }
          }
        }
      }
    } catch {
      // Material resolution failed
    }
  }

  /**
   * Extract type information via IfcRelDefinesByType.
   * Also pulls type-level materials and property sets.
   */
  private extractTypeInfo(
    expressId: number,
    result: IfcElementProperties
  ): void {
    if (!this.ifcApi) return;

    try {
      const relLines = this.ifcApi.GetLineIDsWithType(
        this.modelId,
        WebIfc.IFCRELDEFINESBYTYPE
      );

      for (let i = 0; i < relLines.size(); i++) {
        const relId = relLines.get(i);
        const rel = this.ifcApi.GetLine(this.modelId, relId, false);
        if (!rel?.RelatedObjects) continue;

        const objects = this.toArray(rel.RelatedObjects);
        if (!objects.some((obj) => obj?.value === expressId)) continue;
        if (!rel.RelatingType?.value) continue;

        const typeObj = this.ifcApi.GetLine(this.modelId, rel.RelatingType.value, false);
        if (!typeObj) break;

        result.typeName = this.extractStringValue(typeObj.Name) ?? null;

        // Type direct attributes
        const typeAttrs: Record<string, unknown> = {};
        if (typeObj.Description?.value) typeAttrs["Description"] = typeObj.Description.value;
        if (typeObj.Tag?.value) typeAttrs["Tag"] = typeObj.Tag.value;
        if (typeObj.ElementType?.value) typeAttrs["ElementType"] = typeObj.ElementType.value;
        const typePredefined = this.extractEnumValue(typeObj.PredefinedType);
        if (typePredefined) typeAttrs["PredefinedType"] = typePredefined;
        const typeEntityName = this.getEntityTypeName(typeObj.type);
        typeAttrs["TypeEntity"] = typeEntityName;
        result.typeProperties = typeAttrs;

        // Type property sets
        const { psets, qtos } = this.extractPropertySetsAndQuantitiesRaw(rel.RelatingType.value);
        result.typePropertySets = psets;
        // Type quantities go into result.quantities too
        for (const q of qtos) {
          result.quantities.push({ name: `[Type] ${q.name}`, properties: q.properties });
        }

        // Type-level materials (if instance has none)
        const typeMats = this.extractMaterials(rel.RelatingType.value);
        if (typeMats.length > 0 && result.materials.length === 0) {
          result.materials = typeMats;
        }

        // Type-level classifications
        const typeClassifications = this.extractClassifications(rel.RelatingType.value);
        for (const c of typeClassifications) {
          if (!result.classifications.some((rc) => rc.reference === c.reference && rc.system === c.system)) {
            result.classifications.push(c);
          }
        }

        break;
      }
    } catch {
      // Type info extraction failed
    }
  }

  /**
   * Extract classifications via IfcRelAssociatesClassification.
   */
  private extractClassifications(expressId: number): ClassificationRef[] {
    if (!this.ifcApi) return [];
    const refs: ClassificationRef[] = [];

    try {
      const relLines = this.ifcApi.GetLineIDsWithType(
        this.modelId,
        WebIfc.IFCRELASSOCIATESCLASSIFICATION
      );

      for (let i = 0; i < relLines.size(); i++) {
        const relId = relLines.get(i);
        const rel = this.ifcApi.GetLine(this.modelId, relId, false);
        if (!rel?.RelatedObjects) continue;

        const objects = this.toArray(rel.RelatedObjects);
        if (!objects.some((obj) => obj?.value === expressId)) continue;
        if (!rel.RelatingClassification?.value) continue;

        const classRef = this.ifcApi.GetLine(this.modelId, rel.RelatingClassification.value, false);
        if (!classRef) continue;

        const ref: ClassificationRef = {
          system: "",
          reference: this.extractStringValue(classRef.Identification ?? classRef.ItemReference) ?? "",
          name: this.extractStringValue(classRef.Name) ?? undefined,
        };

        // Resolve the classification system name
        if (classRef.ReferencedSource?.value) {
          const source = this.ifcApi.GetLine(this.modelId, classRef.ReferencedSource.value, false);
          if (source?.Name?.value) {
            ref.system = source.Name.value;
          }
        }

        if (ref.reference || ref.name) {
          refs.push(ref);
        }
      }
    } catch {
      // Classification extraction failed
    }

    return refs;
  }

  /**
   * Extract property sets AND quantity sets, populating result directly.
   */
  private extractPropertySetsAndQuantities(
    expressId: number,
    result: IfcElementProperties
  ): void {
    const { psets, qtos } = this.extractPropertySetsAndQuantitiesRaw(expressId);
    result.propertySets.push(...psets);
    result.quantities.push(...qtos);
  }

  /**
   * Raw extraction: returns psets and qtos separately.
   */
  private extractPropertySetsAndQuantitiesRaw(
    expressId: number
  ): {
    psets: IfcElementProperties["propertySets"];
    qtos: IfcElementProperties["quantities"];
  } {
    if (!this.ifcApi) return { psets: [], qtos: [] };

    const psets: IfcElementProperties["propertySets"] = [];
    const qtos: IfcElementProperties["quantities"] = [];

    try {
      const relLines = this.ifcApi.GetLineIDsWithType(
        this.modelId,
        WebIfc.IFCRELDEFINESBYPROPERTIES
      );

      for (let i = 0; i < relLines.size(); i++) {
        const relId = relLines.get(i);
        const rel = this.ifcApi.GetLine(this.modelId, relId, false);
        if (!rel?.RelatedObjects) continue;

        const objects = this.toArray(rel.RelatedObjects);
        if (!objects.some((obj) => obj?.value === expressId)) continue;
        if (!rel.RelatingPropertyDefinition?.value) continue;

        const psetDef = this.ifcApi.GetLine(
          this.modelId,
          rel.RelatingPropertyDefinition.value,
          false
        );
        if (!psetDef) continue;

        const psetName = this.extractStringValue(psetDef.Name) ?? "Unnamed";

        // Detect if this is a quantity set (IfcElementQuantity) or property set
        const isQuantitySet = !!psetDef.Quantities;

        const properties: Record<string, unknown> = {};

        // IfcPropertySet → HasProperties
        if (psetDef.HasProperties) {
          const props = this.toArray(psetDef.HasProperties);
          for (const propRef of props) {
            if (!propRef?.value) continue;
            const prop = this.ifcApi.GetLine(this.modelId, propRef.value, false);
            if (!prop) continue;
            this.extractProperty(prop, properties);
          }
        }

        // IfcElementQuantity → Quantities
        if (psetDef.Quantities) {
          const quantities = this.toArray(psetDef.Quantities);
          for (const qRef of quantities) {
            if (!qRef?.value) continue;
            const qty = this.ifcApi.GetLine(this.modelId, qRef.value, false);
            if (!qty) continue;

            const qName = this.extractStringValue(qty.Name) ?? "?";
            const val =
              qty.LengthValue?.value ??
              qty.AreaValue?.value ??
              qty.VolumeValue?.value ??
              qty.CountValue?.value ??
              qty.WeightValue?.value ??
              qty.TimeValue?.value ??
              null;

            properties[qName] = val;
          }
        }

        if (Object.keys(properties).length > 0) {
          if (isQuantitySet) {
            qtos.push({ name: psetName, properties });
          } else {
            psets.push({ name: psetName, properties });
          }
        }
      }
    } catch {
      // Property set extraction failed
    }

    return { psets, qtos };
  }

  /**
   * Extract a single property (handles all IfcProperty subtypes).
   */
  private extractProperty(
    prop: Record<string, unknown>,
    target: Record<string, unknown>
  ): void {
    const propName = this.extractStringValue(
      prop.Name as { value: string } | undefined
    ) ?? "?";

    // IfcPropertySingleValue
    if (prop.NominalValue !== undefined) {
      target[propName] = this.resolvePropertyValue(prop.NominalValue);
      return;
    }

    // IfcPropertyEnumeratedValue
    if (prop.EnumerationValues) {
      const vals = this.toArray(prop.EnumerationValues as unknown[]);
      target[propName] = vals
        .map((v) => (v as { value: unknown })?.value)
        .filter((v) => v != null)
        .join(", ");
      return;
    }

    // IfcPropertyBoundedValue
    if (prop.UpperBoundValue !== undefined || prop.LowerBoundValue !== undefined) {
      const upper = this.resolvePropertyValue(prop.UpperBoundValue);
      const lower = this.resolvePropertyValue(prop.LowerBoundValue);
      target[propName] = `${lower ?? "?"} — ${upper ?? "?"}`;
      return;
    }

    // IfcPropertyListValue
    if (prop.ListValues) {
      const vals = this.toArray(prop.ListValues as unknown[]);
      target[propName] = vals
        .map((v) => (v as { value: unknown })?.value)
        .filter((v) => v != null)
        .join(", ");
      return;
    }

    // IfcComplexProperty — nested properties
    if (prop.HasProperties && this.ifcApi) {
      const nested: Record<string, unknown> = {};
      const subProps = this.toArray(prop.HasProperties as unknown[]);
      for (const subRef of subProps) {
        if (!(subRef as { value: number })?.value) continue;
        try {
          const sub = this.ifcApi.GetLine(
            this.modelId,
            (subRef as { value: number }).value,
            false
          );
          if (sub) this.extractProperty(sub as Record<string, unknown>, nested);
        } catch {
          // Skip failed sub-property
        }
      }
      if (Object.keys(nested).length > 0) {
        // Flatten: prefix with complex property name
        for (const [k, v] of Object.entries(nested)) {
          target[`${propName}.${k}`] = v;
        }
      } else {
        target[propName] = "(complex)";
      }
      return;
    }

    // IfcPropertyTableValue
    if (prop.DefiningValues || prop.DefinedValues) {
      const defining = this.toArray((prop.DefiningValues ?? []) as unknown[]);
      const defined = this.toArray((prop.DefinedValues ?? []) as unknown[]);
      const pairs = defining.map((d, idx) => {
        const key = (d as { value: unknown })?.value ?? "?";
        const val = (defined[idx] as { value: unknown })?.value ?? "?";
        return `${key}: ${val}`;
      });
      target[propName] = pairs.join("; ");
      return;
    }

    // Fallback
    target[propName] = "(complex)";
  }

  /**
   * Resolve a property value (NominalValue etc.) to a JS primitive.
   */
  private resolvePropertyValue(val: unknown): unknown {
    if (val === null || val === undefined) return null;
    if (typeof val === "object" && val !== null && "value" in val) {
      return (val as { value: unknown }).value;
    }
    return val;
  }

  /**
   * Extract a string value from an IFC attribute.
   */
  private extractStringValue(
    attr: { value: string } | undefined | null
  ): string | null {
    if (!attr || attr.value === undefined || attr.value === null) return null;
    return String(attr.value);
  }

  /**
   * Extract an enum value from an IFC attribute.
   */
  private extractEnumValue(
    attr: { value: string } | undefined | null
  ): string | null {
    if (!attr || attr.value === undefined || attr.value === null) return null;
    const val = String(attr.value);
    return val === ".NOTDEFINED." || val === "NOTDEFINED" ? null : val.replace(/\./g, "");
  }

  /**
   * Normalize an IFC array-or-single value to always be an array.
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private toArray(val: any): any[] {
    if (Array.isArray(val)) return val;
    if (val == null) return [];
    return [val];
  }

  /**
   * Dispose web-ifc resources.
   */
  dispose(): void {
    if (this.ifcApi) {
      try {
        this.ifcApi.CloseModel(this.modelId);
      } catch {
        // Ignore close errors
      }
      this.ifcApi = null;
    }
    this.globalIdIndex.clear();
    this.typeNameCache.clear();
    this.initialized = false;
    this.initPromise = null;
  }
}
