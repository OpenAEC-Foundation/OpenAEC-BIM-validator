# Concurrentieanalyse OpenAEC BIM Validator (IDS/IFC-checkers)

Onderzocht op 2026-10-21. Bekeken: README.md, CLAUDE.md en STATUS.md. Het product draait op FastAPI met ifctester, een React/That Open-viewer, BCF, multi-tenant, Nextcloud en projectcontainers. De backend gebruikt dus al ifctester.

## 1. Vergelijkingstabel

| Product | Licentie | Platform | IDS 1.0 | IFC | BCF | Prijs | Volwassenheid |
|---|---|---|---|---|---|---|---|
| **Solibri Office** (+ IDS Editor) | Commercieel | Desktop | Ja, volledige workflow: IDS maken en toetsen | 2x3, 4, 4.3 | Ja | ca. €176/mnd per gebruiker bij jaarbetaling (€1.962/jr) | Zeer hoog, marktstandaard |
| **BIMcollab Zoom** (KUBUS, NL) | Commercieel, gratis viewer-modus | Desktop + BIMcollab Nexus/Cloud | Ja (alleen met licentie), inclusief "Smart Issues" bij IDS-conflicten | 2x3, 4, 4.3 | Ja, eigen issue-platform | Platform €12,50–25 per gebruiker per maand | Hoog, sterk in NL (BIM basis ILS Smart View-set) |
| **Trimble Connect + IDS Validator** (Construsoft) | Commercieel add-on | Web (SaaS) | Ja | 2x3, 4 | Via Connect-issues | €69/mnd per project, bovenop een Business-licentie | Middel |
| **usBIM.IDS** (ACCA) | Commercieel SaaS | Web | Ja: editor, "modeler" en validator | 2x3, 4, 4.3 | BCF 2.0/2.1/3.0 en BCF API 3.0 | Freemium/abonnement, niet bevestigd | Middel-hoog |
| **BIMvision + IDS Checker** | Gratis viewer, betaalde plugin | Desktop (Windows) | Ja, vanaf plugin v1.1 | 2x3, 4 | Niet vermeld; resultaten als IFC Comments/BVF | Plugin betaald; gratis web-IDS-maker | Middel |
| **IfcOpenShell ifctester** | LGPL-3.0+ | Python-bibliotheek/CLI, experimentele webapp | Ja, IDS-testcases | 2x3, 4, 4.3 | BCF-, JSON- en HTML-rapporten | Gratis | Hoog; v0.9.0 (sep 2026). Onze eigen engine |
| **Bonsai** (ex-BlenderBIM) | GPL-3.0 | Desktop (Blender) | Ja, via ifctester | Alle | Ja | Gratis | Middel |
| **Xbim.IDS.Validator** | AGPL-3.0 (commerciële licentie mogelijk) | .NET-bibliotheek/CLI | Ja, 100% van de IDS-testcases, leest ook IDS als JSON | 2x3, 4, 4x3-ADD2 | Nee | Gratis/dual license | Hoog |
| **buildingSMART IDS-Audit-tool** | MIT | .NET CLI/bibliotheek, plus browserversie via Xbim | Controleert IDS-bestanden zelf (niet modellen) | 2x3, 4, 4x3 | n.v.t. | Gratis | Officiële referentie |
| **buildingSMART Validation Service** | Open source (GitHub buildingSMART/validate) | Web | IDS-integratie gepland | Schema- en normregels | Nee | Gratis | Hoog |
| **That Open Components** (IDSSpecifications) | MIT | Browser (TS) | IDS maken, importeren en exporteren, toetsen in de browser | 2x3, 4 | BCF-component | Gratis | Middel. Zit al in onze frontend |
| **Speckle Model Checker / Automate** | Apache-2.0 kern, SaaS | Web | Eigen regels, geen native IDS (alleen derden zoals Fluxus) | Via connectors | Nee | Freemium | Middel |
| **Simplebim** (Datacubist) | Commercieel | Desktop | Niet bevestigd | 2x3, 4 | Beperkt | Abonnement | Hoog (IFC-verrijking) |
| **Revit pre-export**: BIMGuard IDS Inspector, Onboard ILS Checker, BIMcollab IDS-palet | Commercieel | Revit-plugin | Ja (Onboard richt zich op BIM basis ILS) | n.v.t. (live model) | Deels | IDS Inspector $15/mnd | Jong |
| **Solibri "Onmisbare BIM basis IDS"-extensie** (BASED, NL) | Gratis extensie | Solibri | ILS-regelset | — | Via Solibri | Gratis | Bestaand, gebaseerd op ILS v2 |

Een specifieke ILS-checker van BIM Loket of het RVB is niet gevonden. Het RVB publiceert de BIM-norm en BIM Loket het BIM basis ILS/IDS, maar het toetsen laten ze over aan Solibri, BIMcollab en vergelijkbare tools. Die lege plek is een kans.

## 2. Functies die wij missen en die het overnemen waard zijn

1. **IDS-editor/-auteur in de browser**: Solibri, usBIM, BIMvision en That Open hebben er een. Met de That Open IDSSpecifications-component is dit goedkoop te bouwen.
2. **IDS-bestand vooraf controleren**: met de Audit-tool, zodat een fout IDS geen onterechte modelfouten oplevert.
3. **IFC-schemavalidatie** naast IDS, zoals de buildingSMART Validation Service doet.
4. **Smart Views/kleurfilters per eis**, zoals in BIMcollab: elementen in 3D kleuren op pass/fail per specificatie.
5. **Issues terugkoppelen**: BCF API 3.0 (usBIM, BIMcollab) en round-trip naar Revit en ArchiCAD, niet alleen een BCF-zip.
6. **Kant-en-klare NL-regelsets met versiebeheer**: BIM basis ILS (actuele versie), RVB BIM-norm, NL-SfB- en STABU-classificatiecontrole, plus een "ILS-configurator"-achtige vragenlijst die het juiste IDS samenstelt.
7. **Trends en dashboard per project**: compliance-percentage over modelversies heen.
8. **CI/API-modus**: automatisch valideren bij upload in Nextcloud, met webhook en badge (vergelijkbaar met Speckle Automate).
9. **Rapportage als PDF/Excel** voor opdrachtgevers.

## 3. Herbruikbare OSS-bibliotheken en -services

- **ifctester / IfcOpenShell**: LGPL-3.0+. Al in gebruik en uitstekend voor SaaS. Bevat ook BCF/JSON/HTML-reporters.
- **buildingSMART IDS-Audit-tool**: MIT, .NET. Als CLI in een container naast de server draaien, of de browserversie van Xbim gebruiken.
- **@thatopen/components**: MIT. De IDSSpecifications-component voor de editor en voor directe controle in de client, plus BCF-onderdelen.
- **buildingSMART/validate**: open source, Python. Schema- en normregelchecks overnemen of aanroepen.
- **Xbim.IDS.Validator**: AGPL-3.0. Alleen als tweede referentie-engine. Let op: AGPL heeft netwerkgevolgen en vraagt dus een eigen licentiebeslissing.
- **IDS-testcases** uit github.com/buildingSMART/IDS: als regressiesuite in onze pytest-tests.
- **Bonsai**: GPL-3.0. Alleen als inspiratie of als desktopbrug, niet inbouwen.

## 4. Positionering voor de Nederlandse markt

Kies voor **"open-source, self-hostbare ILS-validatieservice"**. Dat is het gat tussen de dure desktopcheckers (Solibri, BIMcollab Zoom-licentie) en de generieke SaaS-diensten (Trimble/usBIM, data buiten de EU of buiten eigen beheer). De onderscheidende punten:

- **Soevereiniteit**: multi-tenant, Nextcloud, Hetzner/EU, zelf te hosten door overheden en corporaties (RVB, gemeenten, woningcorporaties).
- **NL-first**: BIM basis ILS en RVB BIM-norm zitten er standaard in, de interface is Nederlands, met NL-SfB-checks. Er bestaat geen officiële webchecker van BIM Loket of het RVB; een samenwerking met de DigiGO/BIM Loket-community ligt dus voor de hand.
- **Standaardgetrouw**: officiële IDS 1.0-engine (ifctester), IDS-audit, BCF. Klaar voor IDS 1.1 zodra die uitkomt; daar is nog geen releasedatum voor.
- Niet concurreren met Solibri op regelcomplexiteit. Wel aanvullen als laagdrempelige "poortwachter" bij modeloplevering, met een gratis tier voor kleine bureaus.

## Bronnen

- https://technical.buildingsmart.org/services/validation-service/
- https://github.com/buildingSMART/IDS-Audit-tool
- https://github.com/buildingSMART/IDS/blob/master/Documentation/developer-guide.md
- https://pypi.org/project/ifctester/
- https://github.com/xBimTeam/Xbim.IDS.Validator
- https://helpcenter.bimcollab.com/portal/nl/kb/bimcollab-zoom/model-checking/ids
- https://helpcenter.bimcollab.com/articles/340793
- https://www.ki-syndikat.de/tools/bimcollab/
- https://www.solibri.com/articles/solibri-25-6-0-release-notes
- https://www.aecplustech.com/tools/solibri
- https://shop.construsoft.com/products/ids-validator
- https://technical.buildingsmart.org/resources/software-implementations/entry/616/
- https://biblus.acca.it/informazioni-gestite-con-standard-ids/
- https://bimvision.eu/ids-checker/
- https://docs.speckle.systems/analytics/model-checker/overview
- https://marketplace.autodesk.com/apps/586f7e37-09c5-4f1e-bfbd-41c79d63c409
- https://www.based.co.nl/redirect/100/EN
- https://digigo.nu/wp-content/uploads/2023/11/BIMcollab_-_BIM_basis_ILS2_0-ppt-handleiding_20201013.pdf
- https://www.buildingsmart.org/standards/bsi-standards/information-delivery-specification-ids/

Kanttekeningen: de prijzen van usBIM, BIMvision en Simplebim zijn niet geverifieerd. De IDS-ondersteuning van Simplebim en het BCF-gedrag van BIMvision zijn ook niet bevestigd.
