# Functievergelijking BIM-modelcheckers

Onderzocht op 2026-10-31. Vervolg op `alternatieven-2026-10.md`. Dat document geeft het overzicht van de markt; dit document zet per functie naast elkaar wat de concurrenten bieden en wat wij hebben. De stand van onze tool is gecontroleerd in de code (commit 8f837dd), niet in de documentatie.

**Afkortingen**

| Afkorting | Product |
|---|---|
| S | Solibri |
| BC | BIMcollab Zoom, Nexus en ModelViewer |
| TC | Trimble Connect |
| us | ACCA usBIM |
| AD | Autodesk Navisworks en ACC Model Coordination |
| DX | Dalux |
| bSV | buildingSMART Validation Service |
| SP | Speckle Automate |
| BV | BIMvision |
| RZ | Revizto |
| OSS | IfcTester, Bonsai en xBim |

## Wat er bij Solibri veranderd is in 2026

- **Nieuwe abonnementen.** In april 2026 zijn Office, Site en Anywhere vervangen door Starter, Essential, Advanced en Premium. Anywhere wordt niet verder ontwikkeld.
- **WebChecker (bèta).** Hiermee controleert Solibri in de browser, met export naar PDF en BCF en een keuze tussen EU- en VS-regio. Dit is de directe concurrent van een browsergebaseerde checker. Het vraagt een Advanced- of Premium-abonnement.
- **AI-assistent (bèta, Premium).** Hiermee stel je vragen in gewone taal, zoek je componenten op en stel je regels in.
- **Update van de IDS Editor (juli 2026).** De editor controleert nu IDS-bestanden met foutmeldingen op regel en kolom, heeft een regex-assistent en bewaart revisies in de cloud.

## Functies naast elkaar

Legenda bij "Wij": ✅ aanwezig, 🟡 gedeeltelijk, ❌ ontbreekt.

| Functie | Wie heeft het | Wij | Issue |
|---|---|---|---|
| IDS 1.0-validatie | S, BC, TC (extensie), us, BV, SP, OSS | ✅ ifctester | — |
| Meegeleverde NL-sets (BIM basis ILS, RVB) | S (ILS via BASED), BC (ILS-handleiding); niemand heeft de RVB-norm | ✅ | — |
| IDS-bestand vooraf controleren | S (juli 2026) | ❌ | #5 |
| IDS-editor | S, BC Nexus, us, BV, Bonsai | ❌ | #15 |
| Meerdere IDS-bestanden en batchcontrole | S, BV, us | ❌ | #5 |
| IFC-schema en normatieve regels | bSV | ❌ | #5 |
| Clashdetectie met tolerantie en groepering | S, BC, TC, AD, RZ, DX | ❌ | #12 |
| Dubbele en overlappende elementen | BC, S, AD | ❌ | #12 |
| Vrije ruimte, toegankelijkheid en ruimteregels | S (veel regels, waaronder #226, #246–#252), TC (clearance) | ❌ | #20 |
| Georeferentie en modellocatie | S (25.12) | ❌ | #21 |
| Classificatie toetsen (NL-SfB) | S, BC | ❌ alleen tonen | #22 |
| Modelversies vergelijken (op GUID) | S, BC, DX | ❌ | #13 |
| Resultaten vergelijken met de vorige run | BC (Smart Issues), RZ | ❌ | #5 |
| 3D-viewer met meerdere modellen | allemaal | 🟡 geen uitlijning | #21 |
| Doorsneden | allemaal | ✅ X/Y/Z-vlakken | — |
| Meten | S, BC, TC, DX | ❌ | #16 |
| Kleuren en filteren op eigenschap (Smart Views) | BC, DX, S | ❌ | #17 |
| Falende elementen kleuren per specificatie | BC, TC, BV | 🟡 alleen rood, niet per specificatie | #5 |
| BCF-export | allemaal | ✅ | — |
| BCF-import | S, BC, BV, us | 🟡 parser bestaat, zit niet in de UI | #18 |
| Koppeling met BCF API-servers | S (BCF Live: BIMcollab, Catenda, Dalux, Aconex, ACC) | 🟡 alleen bcf.open-aec.com, niet getest | #18 |
| Rapport als PDF of Excel | S, BC Nexus, BV | ❌ HTML en JSON wel | #5 |
| Hoeveelheden en informatietabellen | S (ITO), BC (Lists), AD | ❌ | #19 |
| Automatisch opnieuw controleren bij een nieuw model | S (Autorun/Superrun), BC (Nightshift), SP, AD | ❌ | #14 |
| Verloop van de naleving per project | BC Nexus (Power BI), S | ❌ | #13 |
| API en CLI | S (Java, Autorun), SP, OSS | ✅ REST en CLI | — |
| MCP en AI-assistent | S (AI-assistent) | ❌ `mcp_server.py` bestaat niet, anders dan #8/#10 stellen | #10 |
| Zelf te hosten en open source | OSS, bSV | ✅ | — |
| Puntenwolk tegen model | S Premium | ❌ | bewust niet |
| 2D-plattegronden | S, DX | ❌ | niet opgepakt |

## Conclusie

- **Waar wij voorlopen:** open source, zelf te hosten en volledig in de browser. Wij leveren de RVB BIM-norm en BIM basis ILS kant-en-klaar mee; voor de RVB-norm vonden we dat nergens anders.
- **Waar Solibri voorloopt:** geometrische regels (clash, vrije ruimte, toegankelijkheid), modelvergelijking, takeoff en automatisering met Autorun/Superrun.
- **Wat het eerst moet:**
  - De Must-eisen uit #5.
  - Clash en dubbele elementen (#12), omdat elke concurrent dit heeft.
  - Modelversies (#13), omdat het verloop over versies de kern is van een "poortwachter".

## Bronnen

- https://www.solibri.com/articles/solibri-release-notes-april-2026
- https://www.solibri.com/articles/solibri-release-notes-june-2026
- https://www.solibri.com/articles/solibri-ids-editor-release-notes-july-2026
- https://www.solibri.com/articles/release-highlights-release-25-12-0
- https://help.solibri.com/hc/en-us/articles/39702258403607-Solibri-Webchecker-Beta
- https://solibri.github.io/Developer-Platform/latest/superrun-actions.html
- https://www.solibri.com/articles/new-in-smc-v9-7-15-model-comparison-improvements
- https://help.solibri.com/hc/articles/1500004784301 (BCF Live)
- https://helpcenter.bimcollab.com/portal/en/kb/articles/bimcollab-application-feature-overview
- https://docs.3d.connect.trimble.com/clashes/creating-clash-sets
- https://construction.autodesk.com/tools/clash-detection
- https://revizto.com/product/collaborative-clash-automation
- https://buildingsmart.github.io/ifc-gherkin-rules/branches/main/features/index.html
- https://docs.speckle.systems/analytics/model-checker/overview
- https://bimvision.eu/ids-checker/

**Niet geverifieerd:**
- de "Duplicates"-functie en de hoeveelhedenfunctie van Navisworks;
- IDS-ondersteuning bij Dalux, Revizto en Simplebim;
- de nummers van de losse ruimte- en locatieregels van Solibri;
- de verdeling van functies over de nieuwe Solibri-abonnementen.
