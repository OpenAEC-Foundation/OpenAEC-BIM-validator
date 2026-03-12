/**
 * useDemoMode — populates the store with realistic fake data.
 *
 * Activated via ?demo=true URL parameter.
 * Fills all panels with representative content for screenshots
 * and presentations.
 */

import { useEffect } from "react";
import { useStore } from "../store";
import type { SpatialNode, Project, ModelInfo } from "../types/project";
import type { ValidationResult } from "../types/validation";

/** Check if demo mode is active */
export function isDemoMode(): boolean {
  return new URLSearchParams(window.location.search).has("demo");
}

/** Fake spatial tree */
const DEMO_SPATIAL_TREE: SpatialNode = {
  globalId: "0001",
  name: "Kantoorgebouw Zwolle",
  type: "IfcProject",
  elementCount: 2847,
  children: [
    {
      globalId: "0002",
      name: "Bouwlocatie A",
      type: "IfcSite",
      elementCount: 2847,
      children: [
        {
          globalId: "0003",
          name: "Hoofdgebouw",
          type: "IfcBuilding",
          elementCount: 2847,
          children: [
            {
              globalId: "0010",
              name: "Fundering (-1)",
              type: "IfcBuildingStorey",
              elementCount: 312,
              children: [],
            },
            {
              globalId: "0011",
              name: "Begane grond (0)",
              type: "IfcBuildingStorey",
              elementCount: 891,
              children: [],
            },
            {
              globalId: "0012",
              name: "Eerste verdieping (1)",
              type: "IfcBuildingStorey",
              elementCount: 756,
              children: [],
            },
            {
              globalId: "0013",
              name: "Tweede verdieping (2)",
              type: "IfcBuildingStorey",
              elementCount: 634,
              children: [],
            },
            {
              globalId: "0014",
              name: "Dak",
              type: "IfcBuildingStorey",
              elementCount: 254,
              children: [],
            },
          ],
        },
      ],
    },
  ],
};

/** Fake validation results */
const DEMO_VALIDATION_RESULT: ValidationResult = {
  success: false,
  ifc_file_name: "Kantoorgebouw_Zwolle_ARC.ifc",
  ids_file_name: "NL_BIM_Basis_ILS.ids",
  total_specifications: 8,
  failed_specifications: 3,
  total_elements_validated: 2847,
  validation_timestamp: new Date().toISOString(),
  specifications: [
    {
      specification_name: "Alle elementen moeten een classificatie hebben",
      status: "fail",
      severity: "error",
      total_requirements: 1,
      failed_requirements: 1,
      requirements: [
        {
          requirement_description:
            "Elk IfcElement moet een NL/SfB classificatie bevatten",
          status: "fail",
          total_elements: 2847,
          failed_elements: 42,
          elements: [
            {
              global_id: "2O2Fr$t4X7Zf8NOew3FLOH",
              element_type: "IfcWall",
              element_name: "Basiswand: Beton 200",
              status: "fail",
              messages: ["Geen classificatie referentie gevonden"],
            },
            {
              global_id: "3vB2YO$MX4xBjqLOe6dHmF",
              element_type: "IfcSlab",
              element_name: "Vloer: Beton 300mm",
              status: "fail",
              messages: ["Classificatie ontbreekt (verwacht: NL/SfB)"],
            },
            {
              global_id: "1FNFp$3YP0$fMaDNLqKrn2",
              element_type: "IfcColumn",
              element_name: "HEA 300",
              status: "fail",
              messages: ["Geen classificatie referentie gevonden"],
            },
          ],
        },
      ],
    },
    {
      specification_name: "Brandwerendheid moet zijn gespecificeerd",
      status: "fail",
      severity: "error",
      total_requirements: 2,
      failed_requirements: 1,
      requirements: [
        {
          requirement_description:
            "IfcWall en IfcSlab moeten Pset_WallCommon.FireRating bevatten",
          status: "fail",
          total_elements: 486,
          failed_elements: 18,
          elements: [
            {
              global_id: "0hD9z$Y1v6IezXfPMqZp3k",
              element_type: "IfcWall",
              element_name: "Binnenwand: Gips 100",
              status: "fail",
              messages: ["FireRating ontbreekt in Pset_WallCommon"],
            },
          ],
        },
        {
          requirement_description:
            "FireRating waarde moet een geldige notatie zijn (bijv. REI60)",
          status: "pass",
          total_elements: 468,
          failed_elements: 0,
          elements: [],
        },
      ],
    },
    {
      specification_name: "Materiaal specificatie vereist",
      status: "fail",
      severity: "warning",
      total_requirements: 1,
      failed_requirements: 1,
      requirements: [
        {
          requirement_description:
            "Alle constructieve elementen moeten een materiaal hebben",
          status: "fail",
          total_elements: 1204,
          failed_elements: 7,
          elements: [
            {
              global_id: "2X4f8$kOj1xeqWLp9Rm4nH",
              element_type: "IfcBeam",
              element_name: "IPE 240",
              status: "fail",
              messages: [
                "Geen IfcMaterial of IfcMaterialLayerSet gekoppeld",
              ],
            },
          ],
        },
      ],
    },
    {
      specification_name: "Naamgeving volgens NEN 2660",
      status: "pass",
      severity: "info",
      total_requirements: 2,
      failed_requirements: 0,
      requirements: [
        {
          requirement_description: "Elementen moeten een Name attribuut hebben",
          status: "pass",
          total_elements: 2847,
          failed_elements: 0,
          elements: [],
        },
        {
          requirement_description:
            "Name moet voldoen aan het vastgestelde naamgevingspatroon",
          status: "pass",
          total_elements: 2847,
          failed_elements: 0,
          elements: [],
        },
      ],
    },
    {
      specification_name: "Ruimtenummering aanwezig",
      status: "pass",
      severity: "info",
      total_requirements: 1,
      failed_requirements: 0,
      requirements: [
        {
          requirement_description:
            "IfcSpace elementen moeten een LongName hebben",
          status: "pass",
          total_elements: 89,
          failed_elements: 0,
          elements: [],
        },
      ],
    },
    {
      specification_name: "Geometrie kwaliteit",
      status: "pass",
      severity: "info",
      total_requirements: 1,
      failed_requirements: 0,
      requirements: [
        {
          requirement_description:
            "Elementen mogen geen lege geometrie bevatten",
          status: "pass",
          total_elements: 2847,
          failed_elements: 0,
          elements: [],
        },
      ],
    },
    {
      specification_name: "Project informatie volledig",
      status: "pass",
      severity: "info",
      total_requirements: 3,
      failed_requirements: 0,
      requirements: [
        {
          requirement_description: "IfcProject moet een Name hebben",
          status: "pass",
          total_elements: 1,
          failed_elements: 0,
          elements: [],
        },
        {
          requirement_description: "IfcSite moet coördinaten bevatten",
          status: "pass",
          total_elements: 1,
          failed_elements: 0,
          elements: [],
        },
        {
          requirement_description:
            "IfcBuilding moet een adres bevatten",
          status: "pass",
          total_elements: 1,
          failed_elements: 0,
          elements: [],
        },
      ],
    },
    {
      specification_name: "Verdieping-toewijzing compleet",
      status: "pass",
      severity: "info",
      total_requirements: 1,
      failed_requirements: 0,
      requirements: [
        {
          requirement_description:
            "Elk element moet aan een IfcBuildingStorey zijn gekoppeld",
          status: "pass",
          total_elements: 2847,
          failed_elements: 0,
          elements: [],
        },
      ],
    },
  ],
};

/** Populate the store with demo data */
export function useDemoMode(): void {
  useEffect(() => {
    if (!isDemoMode()) return;

    const store = useStore.getState();

    // Create project
    const project: Project = {
      id: "demo-project-001",
      name: "Kantoorgebouw Zwolle",
      createdAt: new Date().toISOString(),
      models: [
        {
          id: "demo-model-arc",
          fileName: "Kantoorgebouw_Zwolle_ARC.ifc",
          fileSize: 48_320_000,
          format: "ifc",
          loadState: "loaded",
          visible: true,
          spatialTree: DEMO_SPATIAL_TREE,
          engineModelId: "model-demo-arc",
        } as ModelInfo,
        {
          id: "demo-model-str",
          fileName: "Kantoorgebouw_Zwolle_CON.ifc",
          fileSize: 22_150_000,
          format: "ifc",
          loadState: "loaded",
          visible: true,
          engineModelId: "model-demo-str",
        } as ModelInfo,
        {
          id: "demo-model-mep",
          fileName: "Kantoorgebouw_Zwolle_MEP.ifc",
          fileSize: 35_780_000,
          format: "ifc",
          loadState: "loading",
          visible: true,
        } as ModelInfo,
      ],
    };

    // Set project
    useStore.setState({ project });

    // Set viewer as ready
    store.setViewerReady(true);

    // Set selected element
    store.selectElement("2O2Fr$t4X7Zf8NOew3FLOH");

    // Set validation results
    useStore.setState({
      validationPhase: "completed",
      validationResult: DEMO_VALIDATION_RESULT,
      idsSelection: { type: "standard", standard: "nl-bim" },
    });

    // Set active tab to validation
    store.setActiveRightTab("validation");

    // Set highlight group for validation failures
    store.setHighlightGroup({
      id: "validation-failures",
      color: "#ff4444",
      globalIds: [
        "2O2Fr$t4X7Zf8NOew3FLOH",
        "3vB2YO$MX4xBjqLOe6dHmF",
        "1FNFp$3YP0$fMaDNLqKrn2",
        "0hD9z$Y1v6IezXfPMqZp3k",
        "2X4f8$kOj1xeqWLp9Rm4nH",
      ],
    });

    // Set status message
    store.setStatusMessage(
      "Validatie voltooid — 3 van 8 specificaties gefaald (67 elementen)"
    );
  }, []);
}
