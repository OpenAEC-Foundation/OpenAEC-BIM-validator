/**
 * Client-Side IFC Renderer Module
 *
 * A specialized IFC renderer for the Client-Side Rendering POC.
 * This module handles IFC file loading and rendering entirely in the browser
 * without any server processing. It provides detailed performance metrics
 * for benchmarking client-side rendering capabilities.
 *
 * Phase 0 Research POC - Client-Side Rendering
 */

import * as OBC from "@thatopen/components";
import * as OBCF from "@thatopen/components-front";

/**
 * Performance metrics structure for client-side rendering
 * @typedef {Object} RenderMetrics
 * @property {number} fileReadTime - Time to read file into memory (ms)
 * @property {number} parseTime - Time to parse IFC data (ms)
 * @property {number} renderTime - Time to render geometry (ms)
 * @property {number} totalTime - Total load time (ms)
 * @property {number} fileSize - File size in bytes
 * @property {number} meshCount - Number of meshes created
 * @property {Object|null} memoryUsage - Memory usage metrics (if available)
 */

/**
 * Client-Side IFC Renderer
 * Optimized for performance measurement and client-side rendering POC
 */
export class ClientRenderer {
    constructor(containerElement, options = {}) {
        this.container = containerElement;
        this.options = {
            backgroundColor: "#1a1a2e",
            gridEnabled: true,
            ...options,
        };

        // Core components
        this.components = null;
        this.world = null;
        this.fragments = null;
        this.ifcLoader = null;
        this.isInitialized = false;

        // Performance tracking
        this.metrics = {
            initTime: 0,
            loadHistory: [],
            totalBytesLoaded: 0,
            peakMemoryUsage: null,
        };

        // Event callbacks
        this.onProgress = options.onProgress || (() => {});
        this.onMetricsUpdate = options.onMetricsUpdate || (() => {});
        this.onError = options.onError || (() => {});
    }

    /**
     * Initialize the renderer components
     * @returns {Promise<Object>} Initialization result with timing
     */
    async init() {
        const startTime = performance.now();

        try {
            this.onProgress("Checking WebGL support...");

            if (!this.checkWebGLSupport()) {
                throw new Error(
                    "WebGL is not supported. Client-side rendering requires WebGL."
                );
            }

            this.onProgress("Initializing That Open Engine...");

            // Create the components manager
            this.components = new OBC.Components();

            // Create world
            const worlds = this.components.get(OBC.Worlds);
            this.world = worlds.create();

            // Set up scene
            this.world.scene = new OBC.SimpleScene(this.components);
            this.world.scene.setup();
            this.world.scene.three.background = new OBCF.THREE.Color(
                this.options.backgroundColor
            );

            // Set up renderer
            this.world.renderer = new OBCF.PostproductionRenderer(
                this.components,
                this.container
            );
            this.world.renderer.postproduction.enabled = false;

            // Set up camera
            this.world.camera = new OBC.OrthoPerspectiveCamera(this.components);
            await this.world.camera.controls.setLookAt(15, 15, 15, 0, 0, 0);

            // Initialize components
            this.components.init();

            // Add grid if enabled
            if (this.options.gridEnabled) {
                const grids = this.components.get(OBC.Grids);
                grids.create(this.world);
            }

            // Set up fragments manager
            this.fragments = this.components.get(OBC.FragmentsManager);

            // Set up IFC loader
            this.onProgress("Loading web-ifc WASM module...");
            this.ifcLoader = this.components.get(OBC.IfcLoader);
            await this.ifcLoader.setup();

            this.isInitialized = true;
            this.metrics.initTime = performance.now() - startTime;

            const result = {
                success: true,
                initTime: this.metrics.initTime,
                webglInfo: this.getWebGLInfo(),
            };

            this.onProgress(`Initialized (${this.metrics.initTime.toFixed(0)}ms)`);
            this.onMetricsUpdate(this.getMetrics());

            return result;
        } catch (error) {
            this.onError(`Initialization failed: ${error.message}`);
            throw error;
        }
    }

    /**
     * Load an IFC file entirely in the browser (no server processing)
     * Provides detailed timing breakdown for performance analysis
     * @param {File} file - The IFC file to load
     * @returns {Promise<RenderMetrics>} Detailed performance metrics
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
            // Phase 1: File Read (client-side only - no server upload)
            this.onProgress(`Reading file: ${file.name}...`);
            const readStartTime = performance.now();

            const buffer = await file.arrayBuffer();
            const data = new Uint8Array(buffer);

            metrics.fileReadTime = performance.now() - readStartTime;

            // Phase 2: IFC Parsing (web-ifc WASM in browser)
            this.onProgress("Parsing IFC data in browser...");
            const parseStartTime = performance.now();

            // The ifcLoader.load() handles both parsing and geometry creation
            // We'll measure this as the combined parse+render time
            const model = await this.ifcLoader.load(data);

            const parseEndTime = performance.now();
            metrics.parseTime = parseEndTime - parseStartTime;

            // Phase 3: Camera fit (part of rendering)
            const renderStartTime = performance.now();

            if (this.world.meshes.length > 0) {
                this.world.camera.fit(this.world.meshes);
            }

            metrics.renderTime = performance.now() - renderStartTime;

            // Calculate totals
            metrics.totalTime = performance.now() - totalStartTime;
            metrics.meshCount = this.world.meshes.length;
            metrics.memoryAfter = this.getMemoryUsage();

            // Track in history
            this.metrics.loadHistory.push({
                ...metrics,
                timestamp: new Date().toISOString(),
            });
            this.metrics.totalBytesLoaded += file.size;

            // Update peak memory
            if (metrics.memoryAfter && metrics.memoryAfter.usedJSHeapSize) {
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

    /**
     * Check if WebGL is supported
     * @returns {boolean}
     */
    checkWebGLSupport() {
        try {
            const canvas = document.createElement("canvas");
            const gl =
                canvas.getContext("webgl2") ||
                canvas.getContext("webgl") ||
                canvas.getContext("experimental-webgl");
            return !!gl;
        } catch (e) {
            return false;
        }
    }

    /**
     * Get WebGL information
     * @returns {Object}
     */
    getWebGLInfo() {
        try {
            const canvas = document.createElement("canvas");
            const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");

            if (!gl) {
                return { supported: false };
            }

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
        } catch (e) {
            return { supported: false, error: e.message };
        }
    }

    /**
     * Get current memory usage (if available)
     * Note: Only works in Chrome with experimental flag or in some contexts
     * @returns {Object|null}
     */
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

    /**
     * Get all collected metrics
     * @returns {Object}
     */
    getMetrics() {
        return {
            initialized: this.isInitialized,
            initTime: this.metrics.initTime,
            loadHistory: this.metrics.loadHistory,
            totalBytesLoaded: this.metrics.totalBytesLoaded,
            totalFilesLoaded: this.metrics.loadHistory.length,
            peakMemoryUsage: this.metrics.peakMemoryUsage,
            currentMemory: this.getMemoryUsage(),
            meshCount: this.world ? this.world.meshes.length : 0,
            webglInfo: this.getWebGLInfo(),
        };
    }

    /**
     * Get summary statistics for performance comparison
     * @returns {Object}
     */
    getPerformanceSummary() {
        const history = this.metrics.loadHistory;

        if (history.length === 0) {
            return null;
        }

        const totalTimes = history.map((h) => h.totalTime);
        const fileSizes = history.map((h) => h.fileSize);

        return {
            filesLoaded: history.length,
            totalBytesLoaded: this.metrics.totalBytesLoaded,
            averageLoadTime: totalTimes.reduce((a, b) => a + b, 0) / totalTimes.length,
            minLoadTime: Math.min(...totalTimes),
            maxLoadTime: Math.max(...totalTimes),
            averageFileSize: fileSizes.reduce((a, b) => a + b, 0) / fileSizes.length,
            peakMemory: this.metrics.peakMemoryUsage,
            // Throughput: bytes per millisecond
            averageThroughput:
                this.metrics.totalBytesLoaded /
                totalTimes.reduce((a, b) => a + b, 0),
        };
    }

    /**
     * Format file size for display
     * @param {number} bytes
     * @returns {string}
     */
    formatFileSize(bytes) {
        if (bytes === 0) return "0 B";
        const k = 1024;
        const sizes = ["B", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    }

    /**
     * Format time duration for display
     * @param {number} ms
     * @returns {string}
     */
    formatTime(ms) {
        if (ms < 1000) {
            return `${ms.toFixed(0)}ms`;
        }
        return `${(ms / 1000).toFixed(2)}s`;
    }

    /**
     * Fit camera to show all loaded models
     */
    fitToView() {
        if (this.world && this.world.meshes.length > 0) {
            this.world.camera.fit(this.world.meshes);
        }
    }

    /**
     * Reset camera to default position
     */
    async resetView() {
        if (this.world) {
            await this.world.camera.controls.setLookAt(15, 15, 15, 0, 0, 0);
        }
    }

    /**
     * Clear all loaded models and reset metrics
     */
    clearModels() {
        if (this.fragments) {
            this.fragments.dispose();
        }
    }

    /**
     * Dispose of the renderer and free resources
     */
    dispose() {
        if (this.components) {
            this.components.dispose();
            this.components = null;
            this.world = null;
            this.fragments = null;
            this.ifcLoader = null;
            this.isInitialized = false;
        }
    }
}

export default ClientRenderer;
