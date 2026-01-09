/**
 * Main Entry Point
 *
 * This file is the entry point for the React application.
 * It renders the App component to the DOM using React 18's createRoot API.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

// Components
import App from './App';

// Styles
import './styles/brand.css';
import './styles/responsive.css';

// Get the root element
const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error(
    'Failed to find the root element. Make sure there is a <div id="root"></div> in your index.html.'
  );
}

// Create root and render the app
const root = createRoot(rootElement);

root.render(
  <StrictMode>
    <App />
  </StrictMode>
);
