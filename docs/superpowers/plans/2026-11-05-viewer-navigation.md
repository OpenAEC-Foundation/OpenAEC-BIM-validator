# Viewer Navigation Implementation Plan

**Goal:** Compact, accessible orientation control with predictable framing and camera state.

**Architecture:** SVG facets driven by the camera quaternion; navigation helpers use the existing camera controller. Local state isolates animation updates from the viewer panel.

**Tech Stack:** React, TypeScript, Three.js, camera-controls, Blueprint UI.

**Spec:** ../specs/2026-11-05-viewer-navigation-design.md

## Constraints and review focus

- No new runtime dependencies; use Blueprint tokens and shared controls.
- Preserve selected focus/zoom and avoid camera pole singularities.
- Verify portrait framing, orthographic zoom, hidden faces, keyboard use and stationary-camera updates.
- Do not modify project serialization or unrelated local files.

## Tasks

- [x] Add camera regression tests in `viewer/src/engine/viewNavigation.test.ts`; verify failure, then implement `viewNavigation.ts` and integrate into `ViewerEngine.ts`.
- [x] Add projection/facet tests in `viewer/src/components/viewcube/cubeGeometry.test.ts`; verify failure, then implement `cubeGeometry.ts` with 26 unique facets and inverse-quaternion projection.
- [x] Replace `ViewCube.tsx` and CSS; add interaction tests, localized labels, shared controls and isolate polling from `CenterPanel.tsx`.
- [x] Run frontend tests, production build and Blueprint checks; inspect the running viewer with a model, both projections and themes. Review diff and update documentation.

## Verification notes

Real camera-controls and browser ProjectionManager regressions cover large-model distance/zoom limits, clipping, top/bottom directions, camera roll and scale across projection changes. Browser verification uses the repository IFC fixture, standard views and light/dark themes. A fresh-context review found projection-state and orthographic clipping issues; both are corrected and regression-tested.
