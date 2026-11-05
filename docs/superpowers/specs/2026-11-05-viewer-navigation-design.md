# Viewer navigation

Replace the CSS cube and detached compass with an SVG orientation cube: six faces, twelve bevels and eight corner facets. Project world coordinates through the inverse camera quaternion, cull rear facets and render depth order. Keep labels upright. Use existing Blueprint tokens and components, Dutch/English labels and keyboard activation. A standard-view selector provides access to hidden faces.

Use the existing Three.js camera and camera-controls, without another renderer or dependency. A WebGL overlay would duplicate rendering resources; CSS transforms retain fragile overlap and hit testing. SVG provides explicit geometry and accessible hit targets.

Orientation changes preserve the orbit target, distance and orthographic zoom. Fit frames the bounds in the current direction for portrait and landscape viewports. Home restores an isometric direction and fits the loaded models. Perspective/orthographic switching remains synchronized after BCF viewpoint restoration. Camera polling stays inside the small navigation component and only updates when state changes.

This change does not alter project serialization, BCF clipping support or the model rendering pipeline. Existing Blueprint themes, local fonts and icon set remain authoritative. Reference principle: separate visible face/edge/corner facets in the native point-cloud viewer; geometry is implemented locally for this viewer's Y-up coordinates.
