# IFC 3D Viewer - That Open Engine POC

Proof of Concept for browser-based IFC 3D rendering using That Open Engine (@thatopen/components).

## Prerequisites

- Node.js 18+
- npm or pnpm

## Setup

1. Install dependencies:
   ```bash
   cd viewer
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open http://localhost:8080 in your browser

## Usage

1. Click "Load IFC File" to select an IFC file from your computer
2. The 3D model will render in the viewport
3. Use mouse to:
   - **Left-click + drag**: Rotate view
   - **Right-click + drag**: Pan view
   - **Scroll wheel**: Zoom in/out
4. Use toolbar buttons:
   - **Fit to View**: Center camera on model
   - **Reset View**: Return to default camera position

## Project Structure

```
viewer/
├── package.json        # Node.js dependencies
├── vite.config.js      # Vite bundler configuration
├── index.html          # Main HTML entry point
└── src/
    └── main.js         # That Open Engine initialization
```

## Dependencies

- **@thatopen/components**: Core viewer components (IFC loader, scene, camera)
- **@thatopen/components-front**: Frontend rendering components
- **@thatopen/fragments**: Fragment-based geometry handling
- **three**: WebGL rendering engine
- **web-ifc**: IFC file parsing (WASM-based)
- **vite**: Development server and bundler

## Test Files

Use the IFC files from the parent repository for testing:
- `../test/2786_CLT_model.ifc` - Small test model (~7MB)

## Phase 0 Research

This POC validates:
1. That Open Engine library installation and compatibility
2. WebGL-based 3D rendering in modern browsers
3. Client-side IFC file loading and parsing
4. Basic camera controls and interaction
