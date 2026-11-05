# Blueprint UI and BCF integration implementation plan

**Goal:** Replace the legacy UI design layer with the current Blueprint web and React package, and connect BCF file import to the active issue queue.
**Architecture:** Vendor upstream source with a pinned commit and SHA256 manifest; document defensive indexed-access guards needed by the consuming TypeScript configuration. Use the official CSS variables directly throughout the product; keep only BIM-specific layout and semantic behavior locally.
**Tech Stack:** React 18, TypeScript, OpenAEC UI 0.4, Vite, Vitest, JSZip.
**Spec:** Blueprint web/README.md and web/react/README.md at the revision recorded in viewer/vendor/blueprint-source.json; issues #6 and #18.

## Constraints
- No competing theme definitions or legacy color aliases; five upstream themes.
- Fonts and icon sprite must work offline. Preserve upstream license/source attribution.
- Preserve existing project, validation, BCF and Tauri workflows.
- Test keyboard interaction, old persisted theme migration, invalid/duplicate BCF imports and export roundtrip.

## Tasks
- [x] Vendor upstream source and add source-integrity verification.
- [x] Test theme migration and modal accessibility, then replace theme application, shared controls, dialogs, tabs and status presentation.
- [x] Migrate application CSS references to canonical tokens; remove old theme/font implementations. Verify production build and all frontend tests.
- [x] Implement and test BCF import into the current issue type, retaining topic IDs, components, viewpoints and snapshots without duplicate issues.
- [x] Review the running application, fix regressions, update both READMEs and acceptance evidence, and request an independent code review.
