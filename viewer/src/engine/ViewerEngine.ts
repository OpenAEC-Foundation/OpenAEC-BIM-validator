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

const WORKER_URL =
  "https://thatopen.github.io/engine_fragment/resources/worker.mjs";
const WASM_PATH = "https://unpkg.com/web-ifc@0.0.77/";

/** Camera fit distance multiplier */
const CAMERA_FIT_PADDING = 1.5;

/** Default scene background color */
const DEFAULT_BACKGROUND = "#1a1a2e";

/** Default highlight opacity */
const HIGHLIGHT_OPACITY = 0.6;

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
  private highlighter: OBCF.Highlighter | null = null;
  private _isInitialized = false;
  private _disposed = false;

  /**
   * Loaded model objects, keyed by modelId.
   * Used for targeted bounding box / camera fit.
   */
  private modelObjects = new Map<string, THREE.Object3D>();

  /** Bounding boxes from fragment metadata, keyed by modelId. */
  private modelBoxes = new Map<string, THREE.Box3>();

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
        fragments.core.update(true);
      });

      // IFC importer
      this.progress("Loading web-ifc WASM module...");
      const importer = new FRAGS.IfcImporter();
      importer.wasm = { absolute: true, path: WASM_PATH };
      this.importer = importer;

      if (this._disposed) return;

      this.setupHighlighter();

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
    if (this.highlighter) {
      await this.highlighter.clear();
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
    if (!this.components || !this.fragments) {
      this.fitToAllModels();
      return;
    }

    try {
      const modelIdMap = await this.fragments.guidsToModelIdMap([globalId]);
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

    const box = new THREE.Box3();
    for (const modelBox of this.modelBoxes.values()) {
      box.union(modelBox);
    }

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
   * Dispose all engine resources.
   */
  dispose(): void {
    this._disposed = true;
    this._isInitialized = false;
    this.modelObjects.clear();
    this.modelBoxes.clear();

    if (this.components) {
      this.components.dispose();
      this.components = null;
      this.world = null;
      this.fragments = null;
      this.importer = null;
      this.highlighter = null;
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

      this.highlighter = hl;
    } catch {
      this.highlighter = null;
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
