/**
 * That Open Engine IFC Viewer - Main Entry Point
 *
 * This is a minimal setup for the That Open Engine (@thatopen/components)
 * to verify the library works correctly in the browser.
 *
 * Phase 0 Research POC - Browser-based IFC 3D rendering
 */

import * as OBC from "@thatopen/components";
import * as OBCF from "@thatopen/components-front";

// DOM Elements
const container = document.getElementById("container");
const fileInput = document.getElementById("file-input");
const fitBtn = document.getElementById("fit-btn");
const resetBtn = document.getElementById("reset-btn");
const status = document.getElementById("status");
const loading = document.getElementById("loading");
const welcome = document.getElementById("welcome");

// Initialize components
let components = null;
let world = null;
let fragments = null;
let ifcLoader = null;

/**
 * Initialize That Open Engine components
 */
async function init() {
    try {
        updateStatus("Initializing viewer...");

        // Create the components manager
        components = new OBC.Components();

        // Get the worlds component and create a simple world
        const worlds = components.get(OBC.Worlds);
        world = worlds.create();

        // Set up the scene
        world.scene = new OBC.SimpleScene(components);
        world.scene.setup();

        // Set up the renderer
        world.renderer = new OBCF.PostproductionRenderer(components, container);
        world.renderer.postproduction.enabled = false;

        // Set up the camera
        world.camera = new OBC.OrthoPerspectiveCamera(components);

        // Initialize the world
        await world.camera.controls.setLookAt(10, 10, 10, 0, 0, 0);

        // Start the components
        components.init();

        // Set up the grid
        const grids = components.get(OBC.Grids);
        grids.create(world);

        // Get the fragments manager
        fragments = components.get(OBC.FragmentsManager);

        // Get the IFC loader
        ifcLoader = components.get(OBC.IfcLoader);

        // Configure the IFC loader with WASM path
        await ifcLoader.setup();

        // Enable UI controls
        fitBtn.disabled = false;
        resetBtn.disabled = false;

        updateStatus("Ready - Select an IFC file to load");

    } catch (error) {
        updateStatus(`Initialization error: ${error.message}`);
        throw error;
    }
}

/**
 * Load an IFC file from a File object
 */
async function loadIFC(file) {
    if (!ifcLoader) {
        updateStatus("Error: Viewer not initialized");
        return;
    }

    try {
        showLoading(true);
        updateStatus(`Loading ${file.name}...`);

        // Read file as ArrayBuffer
        const buffer = await file.arrayBuffer();
        const data = new Uint8Array(buffer);

        // Load the IFC model
        const model = await ifcLoader.load(data);

        // Fit camera to the loaded model
        world.camera.fit(world.meshes);

        showLoading(false);
        welcome.style.display = "none";

        updateStatus(`Loaded: ${file.name}`);

    } catch (error) {
        showLoading(false);
        updateStatus(`Error loading file: ${error.message}`);
        throw error;
    }
}

/**
 * Update status display
 */
function updateStatus(message) {
    status.textContent = message;
}

/**
 * Show/hide loading indicator
 */
function showLoading(show) {
    loading.classList.toggle("active", show);
}

// Event listeners
fileInput.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (file) {
        await loadIFC(file);
    }
});

fitBtn.addEventListener("click", () => {
    if (world && world.meshes.length > 0) {
        world.camera.fit(world.meshes);
        updateStatus("View fitted to model");
    }
});

resetBtn.addEventListener("click", async () => {
    if (world) {
        await world.camera.controls.setLookAt(10, 10, 10, 0, 0, 0);
        updateStatus("View reset");
    }
});

// Initialize the viewer when DOM is ready
init().catch((error) => {
    updateStatus(`Failed to initialize: ${error.message}`);
});
