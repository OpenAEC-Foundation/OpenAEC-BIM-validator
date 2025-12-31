/**
 * That Open Engine IFC Viewer Module
 *
 * A modular, reusable IFC viewer component built on That Open Engine (@thatopen/components).
 * This module encapsulates all 3D viewer functionality for loading and rendering IFC files.
 *
 * Phase 0 Research POC - Browser-based IFC 3D rendering
 */

import * as OBC from "@thatopen/components";
import * as OBCF from "@thatopen/components-front";

/**
 * IFC Viewer class that manages the That Open Engine 3D viewer
 */
export class IFCViewer {
    constructor(containerElement, options = {}) {
        this.container = containerElement;
        this.options = {
            enablePostprocessing: false,
            backgroundColor: "#1a1a2e",
            gridEnabled: true,
            ...options,
        };

        this.components = null;
        this.world = null;
        this.fragments = null;
        this.ifcLoader = null;
        this.loadedModels = [];
        this.isInitialized = false;

        // Performance metrics
        this.metrics = {
            initTime: 0,
            loadTimes: [],
            lastLoadTime: 0,
        };

        // Event callbacks
        this.onStatusChange = options.onStatusChange || (() => {});
        this.onLoadStart = options.onLoadStart || (() => {});
        this.onLoadEnd = options.onLoadEnd || (() => {});
        this.onError = options.onError || (() => {});
    }

    /**
     * Initialize the viewer components
     * @returns {Promise<void>}
     */
    async init() {
        const startTime = performance.now();

        try {
            this.onStatusChange("Initializing WebGL context...");

            // Verify WebGL support
            if (!this.checkWebGLSupport()) {
                throw new Error("WebGL is not supported in this browser");
            }

            // Create the components manager
            this.components = new OBC.Components();

            // Get the worlds component and create a world
            const worlds = this.components.get(OBC.Worlds);
            this.world = worlds.create();

            // Set up the scene with optional background color
            this.world.scene = new OBC.SimpleScene(this.components);
            this.world.scene.setup();
            this.world.scene.three.background = new OBCF.THREE.Color(
                this.options.backgroundColor
            );

            // Set up the renderer with optional postprocessing
            this.world.renderer = new OBCF.PostproductionRenderer(
                this.components,
                this.container
            );
            this.world.renderer.postproduction.enabled =
                this.options.enablePostprocessing;

            // Set up the camera with orbit controls
            this.world.camera = new OBC.OrthoPerspectiveCamera(this.components);

            // Set initial camera position
            await this.world.camera.controls.setLookAt(15, 15, 15, 0, 0, 0);

            // Initialize the components system
            this.components.init();

            // Add grid if enabled
            if (this.options.gridEnabled) {
                const grids = this.components.get(OBC.Grids);
                grids.create(this.world);
            }

            // Get the fragments manager for model management
            this.fragments = this.components.get(OBC.FragmentsManager);

            // Set up the IFC loader
            this.ifcLoader = this.components.get(OBC.IfcLoader);
            await this.ifcLoader.setup();

            this.isInitialized = true;
            this.metrics.initTime = performance.now() - startTime;

            this.onStatusChange(
                `Viewer initialized (${this.metrics.initTime.toFixed(0)}ms)`
            );

            return {
                success: true,
                initTime: this.metrics.initTime,
            };
        } catch (error) {
            this.onError(`Initialization failed: ${error.message}`);
            throw error;
        }
    }

    /**
     * Check if WebGL is supported in the current browser
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
     * Get WebGL version and capabilities
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

            return {
                supported: true,
                version: gl.getParameter(gl.VERSION),
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
     * Load an IFC file from a File object
     * @param {File} file - The IFC file to load
     * @returns {Promise<Object>} Load result with metrics
     */
    async loadFile(file) {
        if (!this.isInitialized) {
            throw new Error("Viewer not initialized. Call init() first.");
        }

        const startTime = performance.now();
        const fileSize = file.size;

        try {
            this.onLoadStart(file.name, fileSize);
            this.onStatusChange(`Loading ${file.name} (${this.formatFileSize(fileSize)})...`);

            // Read file as ArrayBuffer
            const buffer = await file.arrayBuffer();
            const data = new Uint8Array(buffer);

            // Load the IFC model
            const model = await this.ifcLoader.load(data);

            // Track the loaded model
            this.loadedModels.push({
                name: file.name,
                model: model,
                size: fileSize,
            });

            // Fit camera to show all loaded geometry
            if (this.world.meshes.length > 0) {
                this.world.camera.fit(this.world.meshes);
            }

            const loadTime = performance.now() - startTime;
            this.metrics.loadTimes.push({
                fileName: file.name,
                fileSize: fileSize,
                loadTime: loadTime,
            });
            this.metrics.lastLoadTime = loadTime;

            this.onLoadEnd(file.name, loadTime);
            this.onStatusChange(
                `Loaded ${file.name} in ${loadTime.toFixed(0)}ms`
            );

            return {
                success: true,
                fileName: file.name,
                fileSize: fileSize,
                loadTime: loadTime,
                meshCount: this.world.meshes.length,
            };
        } catch (error) {
            const loadTime = performance.now() - startTime;
            this.onError(`Failed to load ${file.name}: ${error.message}`);
            throw error;
        }
    }

    /**
     * Load an IFC file from a URL
     * @param {string} url - URL to the IFC file
     * @param {string} [fileName] - Optional display name for the file
     * @returns {Promise<Object>} Load result with metrics
     */
    async loadFromURL(url, fileName = null) {
        if (!this.isInitialized) {
            throw new Error("Viewer not initialized. Call init() first.");
        }

        const startTime = performance.now();
        const displayName = fileName || url.split("/").pop() || "model.ifc";

        try {
            this.onLoadStart(displayName, 0);
            this.onStatusChange(`Fetching ${displayName}...`);

            // Fetch the file
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const buffer = await response.arrayBuffer();
            const fileSize = buffer.byteLength;
            const data = new Uint8Array(buffer);

            this.onStatusChange(
                `Loading ${displayName} (${this.formatFileSize(fileSize)})...`
            );

            // Load the IFC model
            const model = await this.ifcLoader.load(data);

            // Track the loaded model
            this.loadedModels.push({
                name: displayName,
                model: model,
                size: fileSize,
            });

            // Fit camera to show all loaded geometry
            if (this.world.meshes.length > 0) {
                this.world.camera.fit(this.world.meshes);
            }

            const loadTime = performance.now() - startTime;
            this.metrics.loadTimes.push({
                fileName: displayName,
                fileSize: fileSize,
                loadTime: loadTime,
            });
            this.metrics.lastLoadTime = loadTime;

            this.onLoadEnd(displayName, loadTime);
            this.onStatusChange(
                `Loaded ${displayName} in ${loadTime.toFixed(0)}ms`
            );

            return {
                success: true,
                fileName: displayName,
                fileSize: fileSize,
                loadTime: loadTime,
                meshCount: this.world.meshes.length,
            };
        } catch (error) {
            this.onError(`Failed to load from URL: ${error.message}`);
            throw error;
        }
    }

    /**
     * Fit camera to show all loaded models
     */
    fitToView() {
        if (this.world && this.world.meshes.length > 0) {
            this.world.camera.fit(this.world.meshes);
            this.onStatusChange("View fitted to model");
        }
    }

    /**
     * Reset camera to default position
     */
    async resetView() {
        if (this.world) {
            await this.world.camera.controls.setLookAt(15, 15, 15, 0, 0, 0);
            this.onStatusChange("View reset to default");
        }
    }

    /**
     * Clear all loaded models
     */
    clearModels() {
        if (this.fragments) {
            this.fragments.dispose();
            this.loadedModels = [];
            this.onStatusChange("All models cleared");
        }
    }

    /**
     * Get performance metrics
     * @returns {Object}
     */
    getMetrics() {
        return {
            ...this.metrics,
            modelsLoaded: this.loadedModels.length,
            meshCount: this.world ? this.world.meshes.length : 0,
            webglInfo: this.getWebGLInfo(),
        };
    }

    /**
     * Format file size for display
     * @param {number} bytes - File size in bytes
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
     * Dispose of the viewer and free resources
     */
    dispose() {
        if (this.components) {
            this.components.dispose();
            this.components = null;
            this.world = null;
            this.fragments = null;
            this.ifcLoader = null;
            this.loadedModels = [];
            this.isInitialized = false;
            this.onStatusChange("Viewer disposed");
        }
    }
}

export default IFCViewer;
