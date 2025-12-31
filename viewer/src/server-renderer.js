/**
 * Server-Side IFC Renderer Module
 *
 * A specialized renderer for the Server-Side Rendering POC.
 * This module handles:
 * 1. Uploading IFC files to the server
 * 2. Requesting server-side processing
 * 3. Receiving and rendering optimized geometry in the browser
 *
 * Phase 0 Research POC - Server-Side Rendering
 */

import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

/**
 * Server-Side IFC Renderer
 * Uploads IFC to server, receives processed geometry, and renders it
 */
export class ServerRenderer {
    constructor(containerElement, options = {}) {
        this.container = containerElement;
        this.options = {
            backgroundColor: "#1a2e1a",
            gridEnabled: true,
            serverUrl: "http://localhost:8000",
            ...options,
        };

        // Three.js components
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.currentModel = null;
        this.gridHelper = null;
        this.isInitialized = false;

        // Performance tracking
        this.metrics = {
            initTime: 0,
            loadHistory: [],
            totalBytesUploaded: 0,
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
                throw new Error("WebGL is not supported.");
            }

            this.onProgress("Initializing Three.js renderer...");

            // Create scene
            this.scene = new THREE.Scene();
            this.scene.background = new THREE.Color(this.options.backgroundColor);

            // Create camera
            const aspect = this.container.clientWidth / this.container.clientHeight;
            this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 1000);
            this.camera.position.set(15, 15, 15);
            this.camera.lookAt(0, 0, 0);

            // Create renderer
            this.renderer = new THREE.WebGLRenderer({ antialias: true });
            this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
            this.renderer.setPixelRatio(window.devicePixelRatio);
            this.container.appendChild(this.renderer.domElement);

            // Create controls
            this.controls = new OrbitControls(this.camera, this.renderer.domElement);
            this.controls.enableDamping = true;
            this.controls.dampingFactor = 0.05;

            // Add lighting
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
            this.scene.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(10, 20, 15);
            this.scene.add(directionalLight);

            const backLight = new THREE.DirectionalLight(0xffffff, 0.3);
            backLight.position.set(-10, 10, -15);
            this.scene.add(backLight);

            // Add grid if enabled
            if (this.options.gridEnabled) {
                this.gridHelper = new THREE.GridHelper(50, 50, 0x444444, 0x333333);
                this.scene.add(this.gridHelper);
            }

            // Handle window resize
            window.addEventListener("resize", () => this.handleResize());

            // Start render loop
            this.animate();

            this.isInitialized = true;
            this.metrics.initTime = performance.now() - startTime;

            const result = {
                success: true,
                initTime: this.metrics.initTime,
                webglInfo: this.getWebGLInfo(),
            };

            this.onProgress(`Initialized (${this.metrics.initTime.toFixed(0)}ms)`);
            this.onMetricsUpdate(this.getMetrics());

            // Check server connectivity
            await this.checkServerHealth();

            return result;
        } catch (error) {
            this.onError(`Initialization failed: ${error.message}`);
            throw error;
        }
    }

    /**
     * Animation loop
     */
    animate() {
        requestAnimationFrame(() => this.animate());
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    /**
     * Handle window resize
     */
    handleResize() {
        if (!this.container || !this.camera || !this.renderer) return;

        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    /**
     * Check server health
     * @returns {Promise<Object>}
     */
    async checkServerHealth() {
        try {
            const response = await fetch(`${this.options.serverUrl}/api/health`);
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }
            const data = await response.json();
            this.onProgress("Server connection verified");
            return data;
        } catch (error) {
            this.onError(`Server not reachable: ${error.message}`);
            throw new Error(`Cannot connect to server at ${this.options.serverUrl}: ${error.message}`);
        }
    }

    /**
     * Load an IFC file via server-side processing
     * @param {File} file - The IFC file to load
     * @param {string} format - Output format: 'auto', 'gltf', or 'json-mesh'
     * @returns {Promise<Object>} Detailed performance metrics
     */
    async loadFile(file, format = "auto") {
        if (!this.isInitialized) {
            throw new Error("Renderer not initialized. Call init() first.");
        }

        const totalStartTime = performance.now();
        const metrics = {
            fileName: file.name,
            fileSize: file.size,
            uploadTime: 0,
            processTime: 0,
            downloadTime: 0,
            renderTime: 0,
            totalTime: 0,
            meshCount: 0,
            vertexCount: 0,
            faceCount: 0,
            outputSize: 0,
            outputFormat: null,
            memoryBefore: this.getMemoryUsage(),
            memoryAfter: null,
        };

        try {
            // Phase 1: Upload file to server
            this.onProgress(`Uploading ${file.name} to server...`);
            const uploadStartTime = performance.now();

            const formData = new FormData();
            formData.append("ifc_file", file);

            const uploadResponse = await fetch(`${this.options.serverUrl}/api/upload`, {
                method: "POST",
                body: formData,
            });

            if (!uploadResponse.ok) {
                const errorData = await uploadResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || `Upload failed: ${uploadResponse.status}`);
            }

            const uploadResult = await uploadResponse.json();
            metrics.uploadTime = performance.now() - uploadStartTime;
            const fileId = uploadResult.file_id;

            // Phase 2: Process file on server
            this.onProgress("Server processing IFC file...");
            const processStartTime = performance.now();

            const processResponse = await fetch(
                `${this.options.serverUrl}/api/process/${fileId}?output_format=${format}`,
                { method: "POST" }
            );

            if (!processResponse.ok) {
                const errorData = await processResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || `Processing failed: ${processResponse.status}`);
            }

            const processResult = await processResponse.json();
            metrics.processTime = performance.now() - processStartTime;
            metrics.outputFormat = processResult.format;
            metrics.vertexCount = processResult.stats?.vertices || 0;
            metrics.faceCount = processResult.stats?.faces || 0;
            metrics.outputSize = processResult.stats?.output_size_bytes || 0;

            // Phase 3: Load geometry into viewer
            const downloadStartTime = performance.now();

            if (processResult.format === "json-mesh" && processResult.geometry) {
                // JSON mesh format - geometry is inline in response
                this.onProgress("Rendering JSON mesh geometry...");
                await this.loadJsonMesh(processResult.geometry);
            } else if (processResult.output_file) {
                // glTF format - need to download
                this.onProgress("Downloading processed glTF...");
                await this.loadGltfFromServer(processResult.output_file);
            } else {
                throw new Error("No geometry data in server response");
            }

            metrics.downloadTime = performance.now() - downloadStartTime;

            // Phase 4: Final camera fit
            const renderStartTime = performance.now();
            this.fitToView();
            metrics.renderTime = performance.now() - renderStartTime;

            // Calculate totals
            metrics.totalTime = performance.now() - totalStartTime;
            metrics.meshCount = this.getMeshCount();
            metrics.memoryAfter = this.getMemoryUsage();

            // Track in history
            this.metrics.loadHistory.push({
                ...metrics,
                timestamp: new Date().toISOString(),
            });
            this.metrics.totalBytesUploaded += file.size;

            // Update peak memory
            if (metrics.memoryAfter && metrics.memoryAfter.usedJSHeapSize) {
                if (
                    !this.metrics.peakMemoryUsage ||
                    metrics.memoryAfter.usedJSHeapSize > this.metrics.peakMemoryUsage.usedJSHeapSize
                ) {
                    this.metrics.peakMemoryUsage = { ...metrics.memoryAfter };
                }
            }

            this.onProgress(`Loaded ${file.name} in ${metrics.totalTime.toFixed(0)}ms`);
            this.onMetricsUpdate(this.getMetrics());

            return metrics;
        } catch (error) {
            this.onError(`Failed to load ${file.name}: ${error.message}`);
            throw error;
        }
    }

    /**
     * Load JSON mesh geometry from server response
     * @param {Object} geometryData - JSON mesh data from server
     */
    async loadJsonMesh(geometryData) {
        // Clear existing model
        this.clearModel();

        const elements = geometryData.elements || [];
        let meshCount = 0;

        // Create a parent group for all elements
        const modelGroup = new THREE.Group();

        for (const elem of elements) {
            if (!elem.vertices || !elem.indices || elem.vertices.length === 0) {
                continue;
            }

            try {
                // Create buffer geometry
                const geometry = new THREE.BufferGeometry();

                // Set vertices (IFC uses float32)
                const vertices = new Float32Array(elem.vertices);
                geometry.setAttribute("position", new THREE.BufferAttribute(vertices, 3));

                // Set indices
                const indices = new Uint32Array(elem.indices);
                geometry.setIndex(new THREE.BufferAttribute(indices, 1));

                // Set normals if available
                if (elem.normals && elem.normals.length > 0) {
                    const normals = new Float32Array(elem.normals);
                    geometry.setAttribute("normal", new THREE.BufferAttribute(normals, 3));
                } else {
                    geometry.computeVertexNormals();
                }

                // Create material
                let color = 0x808080; // Default gray
                let opacity = 1.0;

                if (elem.color && elem.color.length >= 3) {
                    color = new THREE.Color(elem.color[0], elem.color[1], elem.color[2]);
                    if (elem.color.length >= 4) {
                        opacity = elem.color[3];
                    }
                }

                const material = new THREE.MeshStandardMaterial({
                    color: color,
                    side: THREE.DoubleSide,
                    transparent: opacity < 1.0,
                    opacity: opacity,
                });

                // Create mesh
                const mesh = new THREE.Mesh(geometry, material);
                mesh.userData = {
                    id: elem.id,
                    guid: elem.guid,
                    type: elem.type,
                    name: elem.name,
                };

                modelGroup.add(mesh);
                meshCount++;
            } catch (err) {
                // Skip elements that fail to load
            }
        }

        this.scene.add(modelGroup);
        this.currentModel = modelGroup;
    }

    /**
     * Load glTF file from server
     * @param {string} downloadPath - API path to download glTF
     */
    async loadGltfFromServer(downloadPath) {
        // Clear existing model
        this.clearModel();

        const loader = new GLTFLoader();
        const url = `${this.options.serverUrl}${downloadPath}`;

        return new Promise((resolve, reject) => {
            loader.load(
                url,
                (gltf) => {
                    this.scene.add(gltf.scene);
                    this.currentModel = gltf.scene;
                    resolve(gltf);
                },
                (progress) => {
                    if (progress.lengthComputable) {
                        const pct = ((progress.loaded / progress.total) * 100).toFixed(0);
                        this.onProgress(`Downloading glTF: ${pct}%`);
                    }
                },
                (error) => {
                    reject(new Error(`Failed to load glTF: ${error.message}`));
                }
            );
        });
    }

    /**
     * Clear current model from scene
     */
    clearModel() {
        if (this.currentModel) {
            this.scene.remove(this.currentModel);
            this.disposeObject(this.currentModel);
            this.currentModel = null;
        }
    }

    /**
     * Recursively dispose of Three.js object
     */
    disposeObject(obj) {
        if (obj.geometry) {
            obj.geometry.dispose();
        }
        if (obj.material) {
            if (Array.isArray(obj.material)) {
                obj.material.forEach((m) => m.dispose());
            } else {
                obj.material.dispose();
            }
        }
        if (obj.children) {
            obj.children.forEach((child) => this.disposeObject(child));
        }
    }

    /**
     * Get count of meshes in current model
     */
    getMeshCount() {
        let count = 0;
        if (this.currentModel) {
            this.currentModel.traverse((obj) => {
                if (obj instanceof THREE.Mesh) {
                    count++;
                }
            });
        }
        return count;
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
            totalBytesUploaded: this.metrics.totalBytesUploaded,
            totalFilesLoaded: this.metrics.loadHistory.length,
            peakMemoryUsage: this.metrics.peakMemoryUsage,
            currentMemory: this.getMemoryUsage(),
            meshCount: this.getMeshCount(),
            webglInfo: this.getWebGLInfo(),
            serverUrl: this.options.serverUrl,
        };
    }

    /**
     * Fit camera to show all loaded geometry
     */
    fitToView() {
        if (!this.currentModel) return;

        const box = new THREE.Box3().setFromObject(this.currentModel);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());

        const maxDim = Math.max(size.x, size.y, size.z);
        const fov = this.camera.fov * (Math.PI / 180);
        let cameraDistance = maxDim / (2 * Math.tan(fov / 2));
        cameraDistance *= 1.5; // Add padding

        const direction = new THREE.Vector3(1, 1, 1).normalize();
        this.camera.position.copy(center).addScaledVector(direction, cameraDistance);
        this.camera.lookAt(center);
        this.controls.target.copy(center);
        this.controls.update();
    }

    /**
     * Reset camera to default position
     */
    resetView() {
        this.camera.position.set(15, 15, 15);
        this.camera.lookAt(0, 0, 0);
        this.controls.target.set(0, 0, 0);
        this.controls.update();
    }

    /**
     * Dispose of the renderer and free resources
     */
    dispose() {
        this.clearModel();

        if (this.gridHelper) {
            this.scene.remove(this.gridHelper);
            this.gridHelper.dispose();
        }

        if (this.renderer) {
            this.renderer.dispose();
            if (this.container.contains(this.renderer.domElement)) {
                this.container.removeChild(this.renderer.domElement);
            }
        }

        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.isInitialized = false;
    }
}

export default ServerRenderer;
