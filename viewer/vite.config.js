import { defineConfig } from 'vite';

export default defineConfig({
    // Base public path for GitHub Pages or other deployments
    base: './',

    // Development server configuration
    server: {
        port: 8080,
        open: true,
        // Allow loading large IFC files
        headers: {
            'Cross-Origin-Opener-Policy': 'same-origin',
            'Cross-Origin-Embedder-Policy': 'require-corp',
        },
    },

    // Build configuration
    build: {
        outDir: 'dist',
        sourcemap: true,
        // Increase chunk size warning limit for IFC-related bundles
        chunkSizeWarningLimit: 2000,
    },

    // Optimize dependencies
    optimizeDeps: {
        include: [
            '@thatopen/components',
            '@thatopen/components-front',
            '@thatopen/fragments',
            'three',
            'web-ifc',
        ],
        // Required for web-ifc WASM loading
        esbuildOptions: {
            target: 'esnext',
        },
    },

    // Handle WASM files for web-ifc
    assetsInclude: ['**/*.wasm'],
});
