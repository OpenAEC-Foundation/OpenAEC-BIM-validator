/**
 * Client-Side IFC Renderer Module (That Open Engine v3)
 *
 * Handles IFC file loading and rendering entirely in the browser
 * using @thatopen/components v3 + @thatopen/fragments.
 */

import * as OBC from "@thatopen/components";
import * as FRAGS from "@thatopen/fragments";
import * as THREE from "three";

const WORKER_URL =
  "https://thatopen.github.io/engine_fragment/resources/worker.mjs";
const WASM_PATH = "https://unpkg.com/web-ifc@0.0.77/";

/**
 * Client-Side IFC Renderer (v3 API)
 */
export class ClientRenderer {
  constructor(containerElement, options = {}) {
    this.container = containerElement;
    this.options = {
      backgroundColor: "#1a1a2e",
      gridEnabled: true,
      ...options,
    };

    this.components = null;
    this.world = null;
    this.fragments = null;
    this.importer = null;
    this.isInitialized = false;

    this.metrics = {
      initTime: 0,
      loadHistory: [],
      totalBytesLoaded: 0,
      peakMemoryUsage: null,
    };

    this.onProgress = options.onProgress || (() => {});
    this.onMetricsUpdate = options.onMetricsUpdate || (() => {});
    this.onError = options.onError || (() => {});
  }

  /**
   * Initialize the renderer components (v3 API)
   */
  async init() {
    const startTime = performance.now();

    try {
      this.onProgress("Checking WebGL support...");
      if (!this.checkWebGLSupport()) {
        throw new Error("WebGL is not supported.");
      }

      this.onProgress("Initializing That Open Engine v3...");

      // Create components manager
      this.components = new OBC.Components();

      // Create world
      const worlds = this.components.get(OBC.Worlds);
      this.world = worlds.create();

      // Scene
      this.world.scene = new OBC.SimpleScene(this.components);
      this.world.scene.setup();
      this.world.scene.three.background = new THREE.Color(
        this.options.backgroundColor
      );

      // Renderer
      this.world.renderer = new OBC.SimpleRenderer(
        this.components,
        this.container
      );

      // Camera
      this.world.camera = new OBC.OrthoPerspectiveCamera(this.components);
      await this.world.camera.controls.setLookAt(15, 15, 15, 0, 0, 0);

      // Start rendering
      this.components.init();

      // Grid
      if (this.options.gridEnabled) {
        const grids = this.components.get(OBC.Grids);
        grids.create(this.world);
      }

      // FragmentsManager with worker
      this.onProgress("Loading fragments worker...");
      this.fragments = this.components.get(OBC.FragmentsManager);
      const workerResp = await fetch(WORKER_URL);
      const workerBlob = await workerResp.blob();
      const workerFile = new File([workerBlob], "worker.mjs", {
        type: "text/javascript",
      });
      const workerUrl = URL.createObjectURL(workerFile);
      this.fragments.init(workerUrl);

      // Register model callback — adds to scene when loaded
      this.fragments.list.onItemSet.add(({ value: model }) => {
        model.useCamera(this.world.camera.three);
        this.world.scene.three.add(model.object);
        this.fragments.core.update(true);
      });

      // IFC importer
      this.onProgress("Loading web-ifc WASM module...");
      this.importer = new FRAGS.IfcImporter();
      this.importer.wasm = { absolute: true, path: WASM_PATH };

      this.isInitialized = true;
      this.metrics.initTime = performance.now() - startTime;

      const result = {
        success: true,
        initTime: this.metrics.initTime,
        webglInfo: this.getWebGLInfo(),
      };

      this.onProgress(
        `Initialized (${this.metrics.initTime.toFixed(0)}ms)`
      );
      this.onMetricsUpdate(this.getMetrics());

      return result;
    } catch (error) {
      this.onError(`Initialization failed: ${error.message}`);
      throw error;
    }
  }

  /**
   * Load an IFC file entirely in the browser
   */
  async loadFile(file) {
    if (!this.isInitialized) {
      throw new Error("Renderer not initialized. Call init() first.");
    }

    const totalStartTime = performance.now();
    const metrics = {
      fileName: file.name,
      fileSize: file.size,
      fileReadTime: 0,
      parseTime: 0,
      renderTime: 0,
      totalTime: 0,
      meshCount: 0,
      memoryBefore: this.getMemoryUsage(),
      memoryAfter: null,
    };

    try {
      // Phase 1: Read file
      this.onProgress(`Reading file: ${file.name}...`);
      const readStart = performance.now();
      const buffer = await file.arrayBuffer();
      const data = new Uint8Array(buffer);
      metrics.fileReadTime = performance.now() - readStart;

      // Phase 2: Convert IFC to fragments
      this.onProgress("Converting IFC to fragments...");
      const parseStart = performance.now();
      const fragmentBytes = await this.importer.process({
        bytes: data,
        progressCallback: (progress) => {
          this.onProgress(
            `Parsing IFC... ${Math.round(progress * 100)}%`
          );
        },
      });
      metrics.parseTime = performance.now() - parseStart;

      // Phase 3: Load fragments into scene
      this.onProgress("Loading into 3D scene...");
      const renderStart = performance.now();
      const modelId = `model-${Date.now()}`;
      await this.fragments.core.load(fragmentBytes, { modelId });
      metrics.renderTime = performance.now() - renderStart;

      // Fit camera
      this.onProgress("Fitting camera...");
      const meshes = [];
      this.world.scene.three.traverse((child) => {
        if (child.isMesh) meshes.push(child);
      });

      if (meshes.length > 0) {
        const box = new THREE.Box3();
        for (const mesh of meshes) {
          box.expandByObject(mesh);
        }
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const dist = maxDim * 1.5;
        await this.world.camera.controls.setLookAt(
          center.x + dist,
          center.y + dist,
          center.z + dist,
          center.x,
          center.y,
          center.z
        );
      }

      // Finalize metrics
      metrics.totalTime = performance.now() - totalStartTime;
      metrics.meshCount = meshes.length;
      metrics.memoryAfter = this.getMemoryUsage();

      this.metrics.loadHistory.push({
        ...metrics,
        timestamp: new Date().toISOString(),
      });
      this.metrics.totalBytesLoaded += file.size;

      if (
        metrics.memoryAfter &&
        metrics.memoryAfter.usedJSHeapSize
      ) {
        if (
          !this.metrics.peakMemoryUsage ||
          metrics.memoryAfter.usedJSHeapSize >
            this.metrics.peakMemoryUsage.usedJSHeapSize
        ) {
          this.metrics.peakMemoryUsage = { ...metrics.memoryAfter };
        }
      }

      this.onProgress(
        `Loaded ${file.name} in ${metrics.totalTime.toFixed(0)}ms`
      );
      this.onMetricsUpdate(this.getMetrics());

      return metrics;
    } catch (error) {
      this.onError(`Failed to load ${file.name}: ${error.message}`);
      throw error;
    }
  }

  checkWebGLSupport() {
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

  getWebGLInfo() {
    try {
      const canvas = document.createElement("canvas");
      const gl =
        canvas.getContext("webgl2") || canvas.getContext("webgl");
      if (!gl) return { supported: false };

      const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
      const isWebGL2 = gl instanceof WebGL2RenderingContext;

      return {
        supported: true,
        version: isWebGL2 ? "WebGL 2.0" : "WebGL 1.0",
        glVersion: gl.getParameter(gl.VERSION),
        vendor: gl.getParameter(gl.VENDOR),
        renderer: debugInfo
          ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
          : "unknown",
        maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
        maxViewportDims: gl.getParameter(gl.MAX_VIEWPORT_DIMS),
      };
    } catch {
      return { supported: false };
    }
  }

  getMemoryUsage() {
    if (performance.memory) {
      return {
        usedJSHeapSize: performance.memory.usedJSHeapSize,
        totalJSHeapSize: performance.memory.totalJSHeapSize,
        jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
      };
    }
    return null;
  }

  getMetrics() {
    return {
      initialized: this.isInitialized,
      initTime: this.metrics.initTime,
      loadHistory: this.metrics.loadHistory,
      totalBytesLoaded: this.metrics.totalBytesLoaded,
      totalFilesLoaded: this.metrics.loadHistory.length,
      peakMemoryUsage: this.metrics.peakMemoryUsage,
      currentMemory: this.getMemoryUsage(),
      meshCount: this.world
        ? this.world.scene.three.children.length
        : 0,
      webglInfo: this.getWebGLInfo(),
    };
  }

  fitToView() {
    if (!this.world) return;
    const meshes = [];
    this.world.scene.three.traverse((child) => {
      if (child.isMesh) meshes.push(child);
    });
    if (meshes.length > 0) {
      const box = new THREE.Box3();
      for (const mesh of meshes) box.expandByObject(mesh);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
      const maxDim = Math.max(size.x, size.y, size.z);
      const dist = maxDim * 1.5;
      this.world.camera.controls.setLookAt(
        center.x + dist,
        center.y + dist,
        center.z + dist,
        center.x,
        center.y,
        center.z
      );
    }
  }

  async resetView() {
    if (this.world) {
      await this.world.camera.controls.setLookAt(15, 15, 15, 0, 0, 0);
    }
  }

  dispose() {
    if (this.components) {
      this.components.dispose();
      this.components = null;
      this.world = null;
      this.fragments = null;
      this.importer = null;
      this.isInitialized = false;
    }
  }
}

export default ClientRenderer;
