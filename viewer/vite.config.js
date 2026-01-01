import { defineConfig } from 'vite';
import { resolve } from 'path';

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
        // Multi-page build configuration
        rollupOptions: {
            input: {
                main: resolve(__dirname, 'index.html'),
                demo: resolve(__dirname, 'thatopen-demo.html'),
                clientRender: resolve(__dirname, 'client-render.html'),
                serverRender: resolve(__dirname, 'server-render.html'),
            },
        },
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
