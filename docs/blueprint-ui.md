# Blueprint UI integration

The viewer uses OpenAEC Blueprint UI 0.4.0 from revision `5e4b0f3419147d6fe72ecbf48f352bba89662d71`. The source snapshot is committed under `viewer/vendor`; the npm dependency resolves to that local package. No remote stylesheet, font or icon request is required.

- `openaec-web` supplies the canonical tokens, components and fonts, unchanged from upstream.
- `openaec-ui-react` supplies buttons, selects, tabs, native dialogs, notifications, icons and the status bar. Three source files contain defensive indexed-access checks for the application's strict TypeScript settings. Original and patched hashes are recorded separately.
- `public/openaec/bim.svg` combines the upstream standard and validator sprites, retaining the first symbol for each ID. Both original sprites are included.
- Application styles contain BIM-specific layout. They use `--oa-*` directly; the old theme definitions and font stylesheet have been removed.
- `data-oa-theme` selects light, dark, blueprint, high-contrast-dark or high-contrast-light. Persisted forge/openaec values migrate to dark and contrast migrates to high-contrast-dark.

Run `npm run check:blueprint` in `viewer` to verify source hashes and token references. CI also runs the frontend tests and production build. The source manifest must be updated deliberately when upgrading the vendored package.

Application code remains MIT licensed. Blueprint code is LGPL-3.0-only and fonts retain their included SIL Open Font Licenses. The vendored source is editable and can be rebuilt with `npm ci` and `npm run build`. Public UI notices are served under `/openaec/`; generated release notices include the UI and font license texts.

# BCF file interoperability

The current queue imports BCF 2.1 with bounded archive expansion. It rejects malformed XML, document type declarations, unsafe asset paths, missing referenced files and duplicate topic IDs within a file. Reimporting an existing local ID leaves the local issue intact.

The importer accepts the canonical BCF 2.1 `Viewpoints` references and repeated `Labels` elements, plus older locally generated nested forms. Topic files are retained for export so additional viewpoints, comments, clipping definitions and attachments are not regenerated or discarded. The viewer displays the first viewpoint's camera, selection, visibility and colours; imported clipping planes and additional viewpoints are retained but not displayed. Local topic status changes are written into the exported markup.

Schema reference: [buildingSMART BCF XML 2.1](https://github.com/buildingSMART/BCF-XML/tree/release_2_1/Schemas). File round-trip support does not imply external BCF API 3.0/OAuth2 interoperability or remote status synchronization; those acceptance criteria remain tracked in issue #18.
