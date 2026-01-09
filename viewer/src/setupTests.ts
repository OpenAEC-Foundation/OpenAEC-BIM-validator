/**
 * Test Setup File for Vitest
 *
 * This file runs before each test file and sets up the testing environment.
 * It configures jsdom, extends expect with jest-dom matchers, and provides
 * common test utilities.
 */

import '@testing-library/jest-dom';

/**
 * Mock the fetch API for tests that don't explicitly mock it
 * This prevents tests from making actual network requests
 */
global.fetch = vi.fn();

/**
 * Mock URL.createObjectURL and URL.revokeObjectURL
 * These are used by file upload components but not available in jsdom
 */
URL.createObjectURL = vi.fn(() => 'blob:mock-url');
URL.revokeObjectURL = vi.fn();

/**
 * Mock window.matchMedia for responsive components
 * jsdom doesn't implement matchMedia, so we provide a mock
 */
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(), // deprecated
        removeListener: vi.fn(), // deprecated
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});

/**
 * Mock ResizeObserver for components that use it
 * jsdom doesn't implement ResizeObserver
 */
global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
}));

/**
 * Mock IntersectionObserver for components that use it
 * jsdom doesn't implement IntersectionObserver
 */
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
}));

/**
 * Cleanup after each test
 * This ensures that mocks and DOM state don't leak between tests
 */
afterEach(() => {
    vi.clearAllMocks();
});

/**
 * Global test utilities
 * These can be used in any test file without importing
 */

// Re-export testing utilities that might be useful globally
export { vi } from 'vitest';
