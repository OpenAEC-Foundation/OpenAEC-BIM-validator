import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
    plugins: [react()],

    test: {
        // Use jsdom for DOM simulation
        environment: 'jsdom',

        // Setup file for test utilities
        setupFiles: ['./src/setupTests.ts'],

        // Global test configuration
        globals: true,

        // Include patterns for test files
        include: ['src/**/*.{test,spec}.{ts,tsx}'],

        // Exclude patterns
        exclude: ['node_modules', 'dist'],

        // Coverage configuration
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            exclude: [
                'node_modules/',
                'dist/',
                'src/setupTests.ts',
                '**/*.d.ts',
                '**/*.test.{ts,tsx}',
                '**/*.spec.{ts,tsx}',
            ],
        },

        // CSS handling
        css: {
            modules: {
                classNameStrategy: 'non-scoped',
            },
        },

        // Reporter configuration
        reporters: ['default'],

        // Watch mode exclusions
        watchExclude: ['node_modules', 'dist'],
    },

    // Path resolution (matches vite.config.ts)
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src'),
        },
    },
});
