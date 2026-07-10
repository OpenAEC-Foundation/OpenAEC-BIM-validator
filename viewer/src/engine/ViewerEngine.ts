/**
 * ViewerEngine — That Open Engine v3 wrapper.
 *
 * Manages the complete 3D viewer lifecycle: scene setup, IFC loading,
 * element interaction (highlight, hover, pick), and camera controls.
 *
 * Designed with a ModelLoader abstraction to support future IFCx format.
 */

import * as OBC from "@thatopen/components";
import * as OBCF from "@thatopen/components-front";
import * as FRAGS from "@thatopen/fragments";
import * as THREE from "three";
import { TransformControls } from "three/examples/jsm/controls/TransformControls.js";

import { PropertyClient } from "./PropertyClient";
import type { IfcElementProperties } from "./PropertyExtractor";
import type { SpatialNode, ElementTypeGroup } from "../types/project";
import type { BcfCameraState } from "../types/bcf";

const WORKER_URL =
  "https://thatopen.github.io/engine_fragment/resources/worker.mjs";
const WASM_PATH = "https://unpkg.com/web-ifc@0.0.77/";

/** Camera fit distance multiplier */
const CAMERA_FIT_PADDING = 1.5;

/** Default scene background color */
const DEFAULT_BACKGROUND = "#1a1a2e";

/** Default highlight opacity */
const HIGHLIGHT_OPACITY = 0.6;


/** Ghost mode: low opacity makes non-selected elements nearly invisible */
const GHOST_OPACITY = 0.15;

/** Color for the isolated element and its fallback indicator (Verdigris) */
const ISOLATION_COLOR = 0x44b6a8;

/** Section plane colors per axis: X=red, Y=green, Z=blue */
const SECTION_PLANE_COLORS: Record<string, string> = {
  x: "#ff4444",
  y: "#44bb44",
  z: "#4488ff",
};

/** Section plane mesh opacity */
const SECTION_PLANE_OPACITY = 0.2;

/** Tracked section plane with visual mesh */
interface SectionPlaneEntry {
  id: string;
  axis: "x" | "y" | "z";
  plane: THREE.Plane;
  mesh: THREE.Mesh;
}

/** Callbacks for engine events */
export interface ViewerEngineCallbacks {
  /** Progress messages during init/load */
  onProgress?: (message: string) => void;
  /** Error messages */
  onError?: (message: string) => void;
  /** Element selected in 3D (GlobalId or null for deselect) */
  onElementSelected?: (globalId: string | null) => void;
  /** Element hovered in 3D */
  onElementHovered?: (globalId: string | null) => void;
}

/** Options for ViewerEngine initialization */
export interface ViewerEngineOptions {
  /** Scene background color */
  backgroundColor?: string;
  /** Enable grid */
  gridEnabled?: boolean;
}

/** Result of loading a model */
export interface LoadResult {
  /** Engine-internal model ID */
  modelId: string;
  /** Number of meshes loaded */
  meshCount: number;
  /** Total load time in ms */
  totalTimeMs: number;
}

/**
 * Core 3D viewer engine wrapping That Open Engine v3.
 */
export class ViewerEngine {
  private container: HTMLElement;
  private callbacks: ViewerEngineCallbacks;
  private options: ViewerEngineOptions;

  private components: OBC.Components | null = null;
  private world: OBC.SimpleWorld<
    OBC.SimpleScene,
    OBC.SimpleCamera,
    OBC.SimpleRenderer
  > | null = null;
  private fragments: OBC.FragmentsManager | null = null;
  private importer: FRAGS.IfcImporter | null = null;
  /** Highlighter instance — kept alive for its event subscriptions (3D click → selectElement).
   *  Read in dispose() to check if cleanup is needed. */
  private _hl: OBCF.Highlighter | null = null;
  private _isInitialized = false;
  private _disposed = false;

  /**
   * Loaded model objects, keyed by modelId.
   * Used for targeted bounding box / camera fit.
   */
  private modelObjects = new Map<string, THREE.Object3D>();

  /** Bounding boxes from fragment metadata, keyed by modelId. */
  private modelBoxes = new Map<string, THREE.Box3>();

  /** Raw IFC bytes per model, keyed by modelId. For client-side property extraction. */
  private modelBytes = new Map<string, Uint8Array>();

  /** Property extractors per model, keyed by modelId. Lazy initialized. */
  private propertyExtractors = new Map<string, PropertyClient>();

  /** Whether isolation mode is active. */
  private _isolated = false;

  /**
   * Active section clipping planes. Applied per-material to model geometry
   * only (never via renderer.clippingPlanes), so gizmos, section-plane
   * visuals and other helpers are never clipped away.
   */
  private clipPlanes: THREE.Plane[] = [];

  /** Saved material state for isolation restore. */
  private savedMaterials = new Map<
    THREE.Material,
    { opacity: number; transparent: boolean; depthWrite: boolean }
  >();

  /** Isolation indicator mesh (box around selected element). */
  private isolationIndicator: THREE.Group | null = null;

  /** Active section plane entries with visual meshes. */
  private sectionEntries: SectionPlaneEntry[] = [];

  /** Shared TransformControls for section plane interaction. */
  private sectionGizmo: TransformControls | null = null;

  /** Currently selected section plane ID. */
  private activeSectionPlaneId: string | null = null;

  /** Pointer handler for section plane selection via raycasting. */
  private sectionPlanePointerHandler: ((e: PointerEvent) => void) | null = null;

  /** Reusable raycaster for section plane hit testing. */
  private sectionRaycaster = new THREE.Raycaster();

  /** Flag to prevent deselection after gizmo drag. */
  private wasDraggingSection = false;

  constructor(
    container: HTMLElement,
    callbacks: ViewerEngineCallbacks = {},
    options: ViewerEngineOptions = {}
  ) {
    this.container = container;
    this.callbacks = callbacks;
    this.options = {
      backgroundColor: DEFAULT_BACKGROUND,
      gridEnabled: true,
      ...options,
    };
  }

  get isInitialized(): boolean {
    return this._isInitialized;
  }

  get isDisposed(): boolean {
    return this._disposed;
  }

  /**
   * Initialize the engine: scene, renderer, camera, fragments manager.
   */
  async init(): Promise<void> {
    if (this._isInitialized || this._disposed) return;

    try {
      this.progress("Checking WebGL support...");
      if (!this.checkWebGLSupport()) {
        throw new Error("WebGL is not supported in this browser.");
      }

      this.progress("Initializing That Open Engine v3...");

      const components = new OBC.Components();
      this.components = components;

      const worlds = components.get(OBC.Worlds);
      const world = worlds.create<
        OBC.SimpleScene,
        OBC.SimpleCamera,
        OBC.SimpleRenderer
      >();
      this.world = world;

      // Scene
      world.scene = new OBC.SimpleScene(components);
      world.scene.setup();
      world.scene.three.background = new THREE.Color(
        this.options.backgroundColor ?? DEFAULT_BACKGROUND
      );

      // Renderer
      world.renderer = new OBC.SimpleRenderer(components, this.container);

      // Camera
      world.camera = new OBC.OrthoPerspectiveCamera(components);
      const cam = world.camera as OBC.OrthoPerspectiveCamera;
      await cam.controls.setLookAt(15, 15, 15, 0, 0, 0);

      if (this._disposed) return;

      // Start render loop
      components.init();

      // Grid
      if (this.options.gridEnabled) {
        const grids = components.get(OBC.Grids);
        grids.create(world);
      }

      // Fragments manager + worker
      this.progress("Loading fragments worker...");
      const fragments = components.get(OBC.FragmentsManager);
      this.fragments = fragments;

      const workerResp = await fetch(WORKER_URL);
      if (this._disposed) return;

      const workerBlob = await workerResp.blob();
      const workerFile = new File([workerBlob], "worker.mjs", {
        type: "text/javascript",
      });
      const workerUrl = URL.createObjectURL(workerFile);
      fragments.init(workerUrl);

      // When a model is added to FragmentsManager, add it to the scene.
      // This callback fires during core.load() — required for tile streaming.
      // Matches the working client-renderer.js pattern exactly.
      fragments.list.onItemSet.add(({ value: model }) => {
        if (this._disposed || !this.world) return;
        model.useCamera(this.world.camera.three);
        this.world.scene.three.add(model.object);
        // Tiles stream in over time — each new tile must pick up any
        // active per-material section clipping and ghost state
        model.tiles.onItemSet.add(({ value: tile }) => {
          const tileObject = tile as unknown as THREE.Object3D;
          if (this.clipPlanes.length > 0) {
            this.applyClippingToObject(tileObject);
          }
          if (this._isolated) {
            this.ghostObject(tileObject);
          }
        });
        if (this.clipPlanes.length > 0) {
          this.applyClippingToObject(model.object);
        }
        fragments.core.update(true);
      });

      // IFC importer
      this.progress("Loading web-ifc WASM module...");
      const importer = new FRAGS.IfcImporter();
      importer.wasm = { absolute: true, path: WASM_PATH };
      this.importer = importer;

      if (this._disposed) return;

      this.setupHighlighter();
      this.setupSectionPlaneDeselect();

      this._isInitialized = true;
      this.progress("Engine ready.");
    } catch (error) {
      if (this._disposed) return;
      const msg =
        error instanceof Error ? error.message : "Unknown initialization error";
      this.error(`Initialization failed: ${msg}`);
      throw error;
    }
  }

  /**
   * Load an IFC file into the scene.
   */
  async loadModel(file: File): Promise<LoadResult> {
    if (!this._isInitialized || !this.fragments || !this.importer || !this.world) {
      throw new Error("Engine not initialized. Call init() first.");
    }

    const startTime = performance.now();
    const modelId = `model-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    try {
      this.progress(`Reading ${file.name}...`);
      const buffer = await file.arrayBuffer();
      if (this._disposed) throw new Error("Engine disposed");

      const data = new Uint8Array(buffer);

      // Store raw bytes for client-side property extraction
      this.modelBytes.set(modelId, data);

      this.progress("Converting IFC to fragments...");
      const fragmentBytes = await this.importer.process({
        bytes: data,
        progressCallback: (progress: number) => {
          this.progress(`Parsing IFC... ${Math.round(progress * 100)}%`);
        },
      });

      if (this._disposed) throw new Error("Engine disposed");

      // Load into fragments — onItemSet callback handles scene setup
      this.progress("Loading into 3D scene...");
      const model = await this.fragments.core.load(fragmentBytes, { modelId });

      if (this._disposed) throw new Error("Engine disposed");

      // Store model reference and bounding box for fitToModel/fitToAllModels
      this.modelObjects.set(modelId, model.object);
      const box = model.box as THREE.Box3;
      if (box && !box.isEmpty()) {
        this.modelBoxes.set(modelId, box.clone());
      }

      // Fit camera using model bounding box from fragment metadata.
      // Tile-based streaming loads meshes on-demand based on camera position,
      // so scene traversal would find 0 meshes at this point. The model's
      // .box property contains the pre-computed bounding box.
      this.progress("Fitting camera...");
      if (box && !box.isEmpty()) {
        this.fitCameraToBox(box);
      }

      const totalTimeMs = performance.now() - startTime;

      this.progress(
        `Loaded ${file.name} (${Math.round(totalTimeMs)}ms)`
      );

      return { modelId, meshCount: -1, totalTimeMs };
    } catch (error) {
      if (this._disposed) throw error;
      const msg =
        error instanceof Error ? error.message : "Unknown load error";
      this.error(`Failed to load ${file.name}: ${msg}`);
      throw error;
    }
  }

  /**
   * Highlight elements by their GlobalIds.
   *
   * Converts GUIDs to a ModelIdMap and applies a colored overlay
   * via FragmentsManager.highlight().
   */
  async highlightByGlobalIds(
    globalIds: string[],
    color: string = "#ff0000"
  ): Promise<void> {
    if (!this.fragments || globalIds.length === 0) return;

    const modelIdMap = await this.fragments.guidsToModelIdMap(globalIds);
    if (Object.keys(modelIdMap).length === 0) return;

    const style: FRAGS.MaterialDefinition = {
      color: new THREE.Color(color),
      renderedFaces: FRAGS.RenderedFaces.ONE,
      opacity: HIGHLIGHT_OPACITY,
      transparent: true,
    };

    await this.fragments.highlight(style, modelIdMap);
  }

  /**
   * Clear all highlights (both programmatic and selection-based).
   */
  async clearHighlights(): Promise<void> {
    if (this.fragments) {
      await this.fragments.resetHighlight();
    }
  }

  /**
   * Zoom camera to fit an element by GlobalId.
   *
   * Uses BoundingBoxer to compute the element's bounding box,
   * then fits the camera. Falls back to fitToAllModels() if
   * the element cannot be found.
   */
  async zoomToElement(globalId: string): Promise<void> {
    return this.zoomToElements([globalId]);
  }

  /**
   * Zoom camera to fit multiple elements by their GlobalIds.
   *
   * Computes the combined bounding box of all elements and fits
   * the camera to that box. Falls back to fitToAllModels() if
   * none of the elements can be found.
   */
  async zoomToElements(globalIds: string[]): Promise<void> {
    if (!this.components || !this.fragments || globalIds.length === 0) {
      this.fitToAllModels();
      return;
    }

    try {
      const modelIdMap = await this.fragments.guidsToModelIdMap(globalIds);
      if (Object.keys(modelIdMap).length === 0) {
        this.fitToAllModels();
        return;
      }

      const boxer = this.components.get(OBC.BoundingBoxer);
      boxer.dispose();
      await boxer.addFromModelIdMap(modelIdMap);
      const box = boxer.get();

      if (box.isEmpty()) {
        this.fitToAllModels();
        return;
      }

      this.fitCameraToBox(box);
    } catch {
      this.fitToAllModels();
    }
  }

  /**
   * Fit camera to a specific loaded model by its modelId.
   */
  fitToModel(modelId: string): void {
    if (!this.world) return;

    const box = this.modelBoxes.get(modelId);
    if (!box || box.isEmpty()) return;

    this.fitCameraToBox(box);
  }

  /**
   * Fit camera to show all loaded models.
   */
  fitToAllModels(): void {
    if (!this.world || this.modelBoxes.size === 0) return;

    const box = this.getModelBoundingBox();
    if (box.isEmpty()) return;

    this.fitCameraToBox(box);
  }

  /**
   * Reset camera to default position.
   */
  async resetView(): Promise<void> {
    if (!this.world) return;
    const cam = this.world.camera as OBC.OrthoPerspectiveCamera;
    await cam.controls.setLookAt(15, 15, 15, 0, 0, 0);
  }

  /**
   * Get or lazily create a PropertyExtractor for a model.
   */
  private getOrCreateExtractor(modelId: string): PropertyClient | null {
    const existing = this.propertyExtractors.get(modelId);
    if (existing) return existing;

    const bytes = this.modelBytes.get(modelId);
    if (!bytes) return null;

    const extractor = new PropertyClient(bytes);
    this.propertyExtractors.set(modelId, extractor);
    return extractor;
  }

  /**
   * Get all properties for an element by GlobalId.
   *
   * Uses client-side web-ifc extraction — no backend needed.
   * Lazy-initializes PropertyExtractor on first call per model.
   */
  async getElementProperties(
    globalId: string
  ): Promise<IfcElementProperties | null> {
    // Try each model until we find the element
    for (const modelId of this.modelBytes.keys()) {
      const extractor = this.getOrCreateExtractor(modelId);
      if (!extractor) continue;

      const props = await extractor.getProperties(globalId);
      if (props) return props;
    }

    return null;
  }

  /**
   * Extract the spatial tree for a specific model.
   */
  async extractSpatialTree(modelId: string): Promise<SpatialNode | null> {
    const extractor = this.getOrCreateExtractor(modelId);
    if (!extractor) return null;
    return extractor.extractSpatialTree();
  }

  /**
   * Get contained elements for a spatial element within a specific model.
   */
  async getContainedElements(
    modelId: string,
    spatialGlobalId: string
  ): Promise<ElementTypeGroup[]> {
    const extractor = this.getOrCreateExtractor(modelId);
    if (!extractor) return [];
    return extractor.getContainedElements(spatialGlobalId);
  }

  /**
   * Set visibility of a loaded model.
   */
  setModelVisibility(modelId: string, visible: boolean): void {
    const obj = this.modelObjects.get(modelId);
    if (obj) {
      obj.visible = visible;
    }
  }

  /**
   * Isolate an element: ghost all geometry via material-level opacity,
   * then render the selected element itself as a dedicated opaque mesh.
   *
   * Fragments batch many elements into shared meshes, so no material- or
   * instance-level trick can keep one element opaque while the rest is
   * ghosted (see TODO.md for the failed attempts). Instead the element's
   * triangles are split out of the batch via getItemsGeometry() into a
   * standalone THREE.Mesh — fully independent of the fragment material
   * system. Falls back to a bounding-box indicator if no geometry is
   * available for the element.
   */
  async isolateElement(globalId: string): Promise<void> {
    if (!this.world || !this.components || !this.fragments) return;

    // Restore any previous isolation first, so the split-out mesh and
    // saved material state never leak into the new ghost pass
    this.restoreMaterials();
    this.removeIsolationIndicator();

    // Ghost ALL meshes at the material level
    for (const obj of this.modelObjects.values()) {
      this.ghostObject(obj);
    }

    try {
      const modelIdMap = await this.fragments.guidsToModelIdMap([globalId]);
      if (Object.keys(modelIdMap).length === 0) {
        this._isolated = true;
        return;
      }

      const group = await this.buildSplitOutMeshes(modelIdMap);
      if (group) {
        this.world.scene.three.add(group);
        this.isolationIndicator = group;
      } else {
        await this.buildBoundingBoxIndicator(modelIdMap);
      }
    } catch {
      // Element not found — ghost-only mode still works
    }

    this._isolated = true;
  }

  /**
   * Split the given elements out of their fragment batches as standalone
   * opaque meshes, parented in a single group positioned in world space.
   * Returns null when no geometry could be extracted.
   */
  private async buildSplitOutMeshes(
    modelIdMap: OBC.ModelIdMap
  ): Promise<THREE.Group | null> {
    if (!this.fragments) return null;

    const group = new THREE.Group();
    group.name = "__isolationIndicator";
    const material = new THREE.MeshLambertMaterial({
      color: ISOLATION_COLOR,
      side: THREE.DoubleSide,
      // Respect active section planes, like the model geometry it replaces
      clippingPlanes: this.clipPlanes.length > 0 ? this.clipPlanes : null,
    });

    for (const [modelId, localIds] of Object.entries(modelIdMap)) {
      const model = this.fragments.list.get(modelId);
      if (!model) continue;

      const itemsGeometry = await model.getItemsGeometry([...localIds]);
      const modelObject = this.modelObjects.get(modelId);

      for (const meshes of itemsGeometry) {
        for (const data of meshes) {
          if (!data.positions || !data.indices) continue;

          const geometry = new THREE.BufferGeometry();
          const positions =
            data.positions instanceof Float64Array
              ? new Float32Array(data.positions)
              : data.positions;
          geometry.setAttribute(
            "position",
            new THREE.BufferAttribute(positions, 3)
          );
          geometry.setIndex(new THREE.BufferAttribute(data.indices, 1));
          if (data.normals) {
            // Fragments deliver quantized Int16 normals
            geometry.setAttribute(
              "normal",
              new THREE.BufferAttribute(data.normals, 3, true)
            );
          } else {
            geometry.computeVertexNormals();
          }

          const mesh = new THREE.Mesh(geometry, material);
          mesh.applyMatrix4(data.transform);
          if (modelObject) {
            mesh.applyMatrix4(modelObject.matrixWorld);
          }
          group.add(mesh);
        }
      }
    }

    if (group.children.length === 0) {
      material.dispose();
      return null;
    }
    return group;
  }

  /**
   * Fallback indicator: wireframe + translucent bounding box around the
   * selected element, used when no split-out geometry is available.
   */
  private async buildBoundingBoxIndicator(
    modelIdMap: OBC.ModelIdMap
  ): Promise<void> {
    if (!this.world || !this.components) return;

    const boxer = this.components.get(OBC.BoundingBoxer);
    boxer.dispose();
    await boxer.addFromModelIdMap(modelIdMap);
    const box = boxer.get();
    if (box.isEmpty()) return;

    const group = new THREE.Group();
    group.name = "__isolationIndicator";

    // Wireframe box outline
    const helper = new THREE.Box3Helper(box, new THREE.Color(ISOLATION_COLOR));
    group.add(helper);

    // Semi-transparent filled box for visibility
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const geometry = new THREE.BoxGeometry(size.x, size.y, size.z);
    const material = new THREE.MeshBasicMaterial({
      color: ISOLATION_COLOR,
      opacity: 0.25,
      transparent: true,
      depthTest: false,
      side: THREE.DoubleSide,
    });
    const filled = new THREE.Mesh(geometry, material);
    filled.position.copy(center);
    group.add(filled);

    this.world.scene.three.add(group);
    this.isolationIndicator = group;
  }

  /**
   * Remove isolation indicator from the scene.
   */
  private removeIsolationIndicator(): void {
    if (!this.isolationIndicator) return;
    this.isolationIndicator.parent?.remove(this.isolationIndicator);
    this.isolationIndicator.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.geometry.dispose();
        const mats = Array.isArray(child.material)
          ? child.material
          : [child.material];
        for (const m of mats) m.dispose();
      }
    });
    this.isolationIndicator = null;
  }

  /**
   * Ghost every mesh material under the given object, saving the original
   * state for restore. The savedMaterials map doubles as a guard against
   * double-ghosting shared materials. Uses isMesh duck-typing so meshes
   * created by other module instances (fragments worker) are not missed.
   */
  private ghostObject(root: THREE.Object3D): void {
    root.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (!mesh.isMesh) return;
      const materials = Array.isArray(mesh.material)
        ? mesh.material
        : [mesh.material];
      for (const mat of materials) {
        if (!mat || this.savedMaterials.has(mat)) continue;
        this.savedMaterials.set(mat, {
          opacity: mat.opacity,
          transparent: mat.transparent,
          depthWrite: mat.depthWrite,
        });
        mat.transparent = true;
        mat.opacity = GHOST_OPACITY;
        mat.depthWrite = false;
        mat.needsUpdate = true;
      }
    });
  }

  /**
   * Restore all materials to their original state.
   */
  private restoreMaterials(): void {
    for (const [mat, saved] of this.savedMaterials) {
      mat.opacity = saved.opacity;
      mat.transparent = saved.transparent;
      mat.depthWrite = saved.depthWrite;
      mat.needsUpdate = true;
    }
    this.savedMaterials.clear();
  }

  /**
   * Clear isolation: restore all materials and remove indicator.
   */
  async clearIsolation(): Promise<void> {
    if (!this._isolated) return;
    this.restoreMaterials();
    this.removeIsolationIndicator();
    this._isolated = false;
  }

  // -- Section Plane Methods --

  /**
   * Add a section plane along a given axis.
   * Creates a transparent colored mesh and auto-selects it with a TransformControls gizmo.
   */
  addSectionPlane(axis: "x" | "y" | "z"): void {
    if (!this.world?.renderer?.three || !this.world?.scene?.three) return;

    const renderer = this.world.renderer.three;
    const scene = this.world.scene.three;

    // Get model bounds for sizing and positioning
    const modelBox = this.getModelBoundingBox();
    const center = new THREE.Vector3();
    const size = new THREE.Vector3();
    if (!modelBox.isEmpty()) {
      modelBox.getCenter(center);
      modelBox.getSize(size);
    }

    const planeSize = Math.max(size.x, size.y, size.z, 10) * 2;
    const color = SECTION_PLANE_COLORS[axis];

    // Clipping plane with normal pointing into the negative axis direction
    const normal = new THREE.Vector3(
      axis === "x" ? -1 : 0,
      axis === "y" ? -1 : 0,
      axis === "z" ? -1 : 0
    );
    const constant = -normal.dot(center);
    const plane = new THREE.Plane(normal, constant);

    // Transparent visual mesh
    const geometry = new THREE.PlaneGeometry(planeSize, planeSize);
    const material = new THREE.MeshBasicMaterial({
      color: new THREE.Color(color),
      opacity: SECTION_PLANE_OPACITY,
      transparent: true,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(center);

    // Orient mesh to match clipping plane axis
    if (axis === "x") mesh.rotation.y = Math.PI / 2;
    else if (axis === "y") mesh.rotation.x = -Math.PI / 2;

    const id = `sectionPlane_${axis}_${Date.now()}`;
    mesh.name = id;
    scene.add(mesh);

    const entry: SectionPlaneEntry = { id, axis, plane, mesh };
    this.sectionEntries.push(entry);

    // Apply clipping per-material to model geometry only, so the plane
    // visuals and the TransformControls gizmo are never clipped themselves
    this.clipPlanes = this.sectionEntries.map((e) => e.plane);
    renderer.localClippingEnabled = true;
    this.applyClippingToAllModels();

    // Create shared gizmo if needed, then select this plane
    this.ensureSectionGizmo();
    this.selectSectionPlane(id);
  }

  /**
   * Remove all section planes, gizmos, and visual meshes.
   */
  removeAllSectionPlanes(): void {
    if (!this.world?.renderer?.three || !this.world?.scene?.three) return;

    const renderer = this.world.renderer.three;
    const scene = this.world.scene.three;

    for (const entry of this.sectionEntries) {
      scene.remove(entry.mesh);
      entry.mesh.geometry.dispose();
      (entry.mesh.material as THREE.Material).dispose();
    }
    this.sectionEntries = [];
    this.activeSectionPlaneId = null;

    // Dispose shared gizmo (visual lives in the scene via getHelper())
    if (this.sectionGizmo) {
      this.sectionGizmo.detach();
      scene.remove(this.sectionGizmo.getHelper());
      this.sectionGizmo.dispose();
      this.sectionGizmo = null;
    }

    this.clipPlanes = [];
    this.applyClippingToAllModels();
    renderer.localClippingEnabled = false;
  }

  /**
   * Apply the active clipping planes to every material under the given
   * object. Passing an empty plane set clears clipping.
   */
  private applyClippingToObject(obj: THREE.Object3D): void {
    const planes = this.clipPlanes.length > 0 ? this.clipPlanes : null;
    obj.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (!mesh.isMesh) return;
      const materials = Array.isArray(mesh.material)
        ? mesh.material
        : [mesh.material];
      for (const mat of materials) {
        if (!mat) continue;
        mat.clippingPlanes = planes;
        mat.needsUpdate = true;
      }
    });
  }

  /**
   * Re-apply clipping to all model geometry and the isolation mesh.
   */
  private applyClippingToAllModels(): void {
    for (const obj of this.modelObjects.values()) {
      this.applyClippingToObject(obj);
    }
    if (this.isolationIndicator) {
      this.applyClippingToObject(this.isolationIndicator);
    }
  }

  /**
   * Get the number of active section planes.
   */
  get sectionPlaneCount(): number {
    return this.sectionEntries.length;
  }

  /**
   * Select a section plane by ID: attach the shared gizmo to its mesh.
   */
  selectSectionPlane(id: string): void {
    const entry = this.sectionEntries.find((e) => e.id === id);
    if (!entry || !this.sectionGizmo) return;

    this.activeSectionPlaneId = id;
    this.sectionGizmo.attach(entry.mesh);
  }

  // -- Section Plane Interaction (private) --

  /**
   * Deselect all section planes: detach the gizmo.
   */
  private deselectAllSectionPlanes(): void {
    if (this.sectionGizmo) {
      this.sectionGizmo.detach();
    }
    this.activeSectionPlaneId = null;
  }

  /**
   * Sync a clipping plane's constant from its mesh position.
   * Called on every gizmo objectChange during drag.
   */
  private syncPlaneFromMesh(entry: SectionPlaneEntry): void {
    entry.plane.constant = -entry.plane.normal.dot(entry.mesh.position);
  }

  /**
   * Create the shared TransformControls gizmo (once).
   * Registers objectChange and dragging-changed listeners.
   */
  private ensureSectionGizmo(): void {
    if (this.sectionGizmo || !this.world?.renderer?.three) return;

    const cam = this.world.camera.three;
    const domElement = this.world.renderer.three.domElement;

    const gizmo = new TransformControls(cam, domElement);
    gizmo.setMode("translate");
    gizmo.setSize(0.8);

    gizmo.addEventListener("dragging-changed", (event) => {
      const isDragging = (event as unknown as { value: boolean }).value;
      if (isDragging) this.wasDraggingSection = true;
      if (!this.world) return;
      const camCtrl = this.world.camera as OBC.OrthoPerspectiveCamera;
      camCtrl.controls.enabled = !isDragging;
    });

    gizmo.addEventListener("objectChange", () => {
      const activeEntry = this.sectionEntries.find(
        (e) => e.id === this.activeSectionPlaneId
      );
      if (activeEntry) this.syncPlaneFromMesh(activeEntry);
    });

    // three r169+: TransformControls is no longer an Object3D itself —
    // its visual representation must be added via getHelper()
    this.world.scene.three.add(gizmo.getHelper());
    this.sectionGizmo = gizmo;
  }

  /**
   * Set up pointer handler for clicking on section plane meshes.
   * Click on a plane mesh -> select it; click elsewhere -> deselect.
   */
  private setupSectionPlaneDeselect(): void {
    if (!this.world?.renderer?.three) return;

    const domElement = this.world.renderer.three.domElement;

    this.sectionPlanePointerHandler = (event: PointerEvent) => {
      if (!this.world || this.sectionEntries.length === 0) return;

      // Skip if we just finished a gizmo drag
      if (this.wasDraggingSection) {
        this.wasDraggingSection = false;
        return;
      }

      const rect = domElement.getBoundingClientRect();
      const mouse = new THREE.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1
      );

      this.sectionRaycaster.setFromCamera(mouse, this.world.camera.three);
      const meshes = this.sectionEntries.map((e) => e.mesh);
      const intersects = this.sectionRaycaster.intersectObjects(meshes, false);

      const firstHit = intersects[0];
      if (firstHit) {
        const hitEntry = this.sectionEntries.find(
          (e) => e.mesh === firstHit.object
        );
        if (hitEntry && hitEntry.id !== this.activeSectionPlaneId) {
          this.selectSectionPlane(hitEntry.id);
        }
      } else if (this.activeSectionPlaneId) {
        this.deselectAllSectionPlanes();
      }
    };

    domElement.addEventListener("pointerup", this.sectionPlanePointerHandler);
  }

  /**
   * Get the combined bounding box of all loaded models.
   */
  private getModelBoundingBox(): THREE.Box3 {
    const box = new THREE.Box3();
    for (const b of this.modelBoxes.values()) box.union(b);
    return box;
  }

  // -- Camera Utility Methods --

  /**
   * Get camera quaternion for ViewCube synchronization.
   * Returns [x, y, z, w] or null if camera not available.
   */
  getCameraQuaternion(): [number, number, number, number] | null {
    if (!this.world) return null;

    const cam = this.world.camera.three;
    const q = cam.quaternion;
    return [q.x, q.y, q.z, q.w];
  }

  /**
   * Navigate camera to a named view target (for ViewCube).
   * Supports faces, edges (e.g. "front-top"), and corners (e.g. "front-top-right").
   * Keeps the camera pointed at the center of all loaded models.
   */
  async navigateToFace(target: string): Promise<void> {
    if (!this.world) return;

    const center = new THREE.Vector3();
    let dist = 15;
    const modelBox = this.getModelBoundingBox();
    if (!modelBox.isEmpty()) {
      modelBox.getCenter(center);
      const size = modelBox.getSize(new THREE.Vector3());
      dist = Math.max(size.x, size.y, size.z) * CAMERA_FIT_PADDING;
    }

    // Build direction vector from target components
    const parts = target.split("-");
    const dir = new THREE.Vector3(0, 0, 0);
    let needsCustomUp = false;
    let up: [number, number, number] = [0, 1, 0];

    for (const part of parts) {
      switch (part) {
        case "front":  dir.z += 1; break;
        case "back":   dir.z -= 1; break;
        case "right":  dir.x += 1; break;
        case "left":   dir.x -= 1; break;
        case "top":    dir.y += 1; break;
        case "bottom": dir.y -= 1; break;
      }
    }

    // Pure top/bottom views need a custom up vector
    if (dir.x === 0 && dir.z === 0 && dir.y !== 0) {
      needsCustomUp = true;
      up = dir.y > 0 ? [0, 0, -1] : [0, 0, 1];
    }

    if (dir.lengthSq() === 0) return;
    dir.normalize().multiplyScalar(dist);

    const cam = this.world.camera as OBC.OrthoPerspectiveCamera;

    if (needsCustomUp) {
      cam.three.up.set(up[0], up[1], up[2]);
    } else {
      cam.three.up.set(0, 1, 0);
    }

    await cam.controls.setLookAt(
      center.x + dir.x,
      center.y + dir.y,
      center.z + dir.z,
      center.x,
      center.y,
      center.z
    );
  }

  // -- BCF Viewpoint Methods --

  /**
   * Capture the current canvas as a PNG data URL.
   *
   * Used for BCF viewpoint snapshots. Forces a render frame
   * before capture to ensure the canvas is up-to-date (important
   * with That Open Engine's tile-streaming renderer).
   *
   * @returns PNG data URL string, or empty string if renderer unavailable.
   */
  async takeScreenshot(): Promise<string> {
    if (!this.world?.renderer) return "";

    const renderer = this.world.renderer.three;

    // Force one render frame so tile-streamed geometry is drawn
    renderer.render(
      this.world.scene.three,
      this.world.camera.three
    );

    // Wait for GPU flush via requestAnimationFrame
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));

    return renderer.domElement.toDataURL("image/png");
  }

  /**
   * Get current camera state for BCF viewpoint.
   *
   * Returns eye/target/up vectors compatible with BCF 2.1
   * perspective_camera and orthogonal_camera elements.
   */
  getCameraState(): BcfCameraState | null {
    if (!this.world) return null;

    const cam = this.world.camera as OBC.OrthoPerspectiveCamera;
    const pos = new THREE.Vector3();
    const target = new THREE.Vector3();

    cam.controls.getPosition(pos);
    cam.controls.getTarget(target);

    const direction = new THREE.Vector3()
      .subVectors(target, pos)
      .normalize();
    const up = cam.three.up.clone();

    const isPerspective =
      cam.three instanceof THREE.PerspectiveCamera;

    return {
      position: { x: pos.x, y: pos.y, z: pos.z },
      direction: { x: direction.x, y: direction.y, z: direction.z },
      up: { x: up.x, y: up.y, z: up.z },
      fieldOfView: isPerspective
        ? (cam.three as THREE.PerspectiveCamera).fov
        : undefined,
      aspectRatio: isPerspective
        ? (cam.three as THREE.PerspectiveCamera).aspect
        : undefined,
      type: isPerspective ? "perspective" : "orthogonal",
    };
  }

  /**
   * Restore camera to a saved BCF viewpoint state.
   *
   * Computes the target position from eye + direction and
   * uses setLookAt for smooth transition.
   */
  async restoreCameraState(state: BcfCameraState): Promise<void> {
    if (!this.world) return;

    const cam = this.world.camera as OBC.OrthoPerspectiveCamera;
    const { position: p, direction: d } = state;

    // Compute a target point at a reasonable distance along the direction
    const dist = 10; // arbitrary look-at distance
    await cam.controls.setLookAt(
      p.x,
      p.y,
      p.z,
      p.x + d.x * dist,
      p.y + d.y * dist,
      p.z + d.z * dist
    );
  }

  /**
   * Prepare the viewer for a BCF viewpoint screenshot.
   *
   * Zooms to the first element, highlights all target elements
   * in red, and returns the screenshot + camera state.
   *
   * @param globalIds - GlobalIds of elements to feature in the viewpoint
   * @param highlightColor - Hex color for highlighted elements
   * @returns Screenshot data URL and camera state, or null on failure
   */
  async captureViewpoint(
    globalIds: string[],
    highlightColor: string = "#ff4444"
  ): Promise<{ screenshot: string; camera: BcfCameraState } | null> {
    if (!this._isInitialized || globalIds.length === 0) return null;

    try {
      // 1. Zoom to combined bounding box of all elements
      await this.zoomToElements(globalIds);

      // 2. Small delay for camera transition + tile loading
      await new Promise((r) => setTimeout(r, 300));

      // 3. Clear existing highlights, apply new ones
      await this.clearHighlights();
      await this.highlightByGlobalIds(globalIds, highlightColor);

      // 4. Wait for render
      await new Promise((r) => setTimeout(r, 200));

      // 5. Capture
      const screenshot = await this.takeScreenshot();
      const camera = this.getCameraState();

      if (!camera || !screenshot) return null;

      return { screenshot, camera };
    } catch {
      return null;
    }
  }

  /**
   * Dispose all engine resources.
   */
  dispose(): void {
    this._disposed = true;
    this._isInitialized = false;
    // Clean up section plane pointer handler before removing planes
    if (this.sectionPlanePointerHandler && this.world?.renderer?.three) {
      this.world.renderer.three.domElement.removeEventListener(
        "pointerup",
        this.sectionPlanePointerHandler
      );
      this.sectionPlanePointerHandler = null;
    }
    this.removeAllSectionPlanes();
    this.removeIsolationIndicator();
    this.modelObjects.clear();
    this.modelBoxes.clear();
    this.modelBytes.clear();
    this._isolated = false;

    for (const extractor of this.propertyExtractors.values()) {
      extractor.dispose();
    }
    this.propertyExtractors.clear();

    // Dispose highlighter if it was created
    if (this._hl) {
      this._hl = null;
    }

    if (this.components) {
      this.components.dispose();
      this.components = null;
      this.world = null;
      this.fragments = null;
      this.importer = null;
    }
  }

  // -- Private helpers --

  /**
   * Fit camera to a bounding box.
   * Positions camera at an isometric-ish angle looking at the box center.
   */
  private fitCameraToBox(box: THREE.Box3): void {
    if (!this.world) return;

    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const dist = maxDim * CAMERA_FIT_PADDING;

    const cam = this.world.camera as OBC.OrthoPerspectiveCamera;
    cam.controls.setLookAt(
      center.x + dist,
      center.y + dist * 0.8,
      center.z + dist,
      center.x,
      center.y,
      center.z
    );
  }

  private setupHighlighter(): void {
    if (!this.components || !this.world) return;

    try {
      const hl = new OBCF.Highlighter(this.components);
      hl.setup({ world: this.world });

      const selectEvents = hl.events.select;
      if (selectEvents) {
        selectEvents.onHighlight.add(
          async (data: OBC.ModelIdMap) => {
            const globalId =
              await this.extractGlobalIdFromSelection(data);
            this.callbacks.onElementSelected?.(globalId);
          }
        );

        selectEvents.onClear.add(() => {
          this.callbacks.onElementSelected?.(null);
        });
      }

      this._hl = hl;
    } catch {
      this._hl = null;
    }
  }

  /**
   * Extract the first GlobalId from a Highlighter selection event.
   *
   * The onHighlight event provides a ModelIdMap (Record<string, Set<number>>).
   * We convert it to GUIDs via FragmentsManager.modelIdMapToGuids().
   */
  private async extractGlobalIdFromSelection(
    data: OBC.ModelIdMap
  ): Promise<string | null> {
    if (!this.fragments) return null;

    try {
      const guids = await this.fragments.modelIdMapToGuids(data);
      return guids.length > 0 ? (guids[0] ?? null) : null;
    } catch {
      return null;
    }
  }

  private checkWebGLSupport(): boolean {
    try {
      const canvas = document.createElement("canvas");
      return !!(
        canvas.getContext("webgl2") ||
        canvas.getContext("webgl") ||
        canvas.getContext("experimental-webgl")
      );
    } catch {
      return false;
    }
  }

  private progress(message: string): void {
    this.callbacks.onProgress?.(message);
  }

  private error(message: string): void {
    this.callbacks.onError?.(message);
  }
}
