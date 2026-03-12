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
        // Single-page app (AppShell handles routing)
        rollupOptions: {
            input: {
                main: resolve(__dirname, 'index.html'),
            },
        },
    },

    // Optimize dependencies
    optimizeDeps: {
        include: [
            'three',
            '@thatopen/components > three',
            '@thatopen/fragments > three',
            '@thatopen/components',
            '@thatopen/components-front',
            '@thatopen/fragments',
            'web-ifc',
            'camera-controls',
            'react',
            'react-dom',
        ],
        esbuildOptions: {
            target: 'esnext',
        },
        force: true,
    },

    // Handle WASM files for web-ifc
    assetsInclude: ['**/*.wasm'],
});
