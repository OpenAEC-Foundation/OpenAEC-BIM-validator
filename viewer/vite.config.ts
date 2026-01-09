import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
    // React plugin for JSX/TSX support
    plugins: [react()],

    // Path resolution for @ alias
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src'),
        },
    },

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
        // Proxy API requests to backend
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                secure: false,
            },
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
            'react',
            'react-dom',
        ],
        // Required for web-ifc WASM loading
        esbuildOptions: {
            target: 'esnext',
        },
    },

    // Handle WASM files for web-ifc
    assetsInclude: ['**/*.wasm'],
});
