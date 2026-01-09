/**
 * Example Test File
 *
 * This file demonstrates that Vitest is correctly configured with:
 * - jsdom environment for DOM testing
 * - React Testing Library for component testing
 * - jest-dom matchers for assertions
 *
 * Delete this file after verifying the setup works.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

/**
 * Simple test component for verification
 */
function TestComponent({ message }: { message: string }) {
    return <div data-testid="test-component">{message}</div>;
}

describe('Vitest Setup Verification', () => {
    it('should render a React component', () => {
        render(<TestComponent message="Hello, Vitest!" />);

        const element = screen.getByTestId('test-component');
        expect(element).toBeInTheDocument();
    });

    it('should have correct text content', () => {
        render(<TestComponent message="Testing works!" />);

        const element = screen.getByText('Testing works!');
        expect(element).toBeInTheDocument();
    });

    it('should have access to jest-dom matchers', () => {
        render(<TestComponent message="Matcher test" />);

        const element = screen.getByTestId('test-component');
        expect(element).toHaveTextContent('Matcher test');
        expect(element).toBeVisible();
    });
});

describe('Global Mocks Verification', () => {
    it('should have URL.createObjectURL mocked', () => {
        const url = URL.createObjectURL(new Blob(['test']));
        expect(url).toBe('blob:mock-url');
    });

    it('should have fetch mocked', () => {
        expect(global.fetch).toBeDefined();
        expect(vi.isMockFunction(global.fetch)).toBe(true);
    });

    it('should have matchMedia mocked', () => {
        const mql = window.matchMedia('(min-width: 768px)');
        expect(mql.matches).toBe(false);
        expect(mql.media).toBe('(min-width: 768px)');
    });
});
