# Release- en integratieplan

De bestaande Python-validatiekern, FastAPI-server, React-viewer en Tauri-shell blijven de productarchitectuur. De publicatie volgt de versie- en signingconventies van OpenAEC-Blueprint.

1. Reproduceerbaarheid (#4): npm-lockfile vastleggen, virtualenv uit de index verwijderen, projectlicentie en dependencylicenties leveren. Verificatie: schone npm-installatie en productiebuild.
2. Versies (#7): ISO-jaar.week.volgnummer synchroniseren in Python, npm, Cargo, Tauri en installer. Verificatie: grensgevallen rond de jaarwisseling en overeenkomst met de releasetag.
3. Regressies: bestaande Python- en viewertests uitvoeren, oorzaken herstellen en opnieuw controleren zonder acceptatiecriteria te verlagen.
4. Distributie (#6, #9): Windows-installer en container bouwen, artifacts en containerdigest publiceren, signatures daadwerkelijk verifiëren. Ontbrekende signing mag niet als geslaagde signing worden gerapporteerd.
5. Servicecontract (#8, #10, #11): geauthenticeerde, geïsoleerde toolaanroepen en MCP over HTTP met begrensde jobs, uploads en bewaartermijn.
6. Productfunctionaliteit (#2, #3, #5, #12–#22): per issue bestaande implementatie toetsen aan de acceptatiecriteria, ontbrekende functies aanvullen en met modeltests controleren.
7. Documentatie: README in Engels en Nederlands, ondersteunde platformen en beperkingen expliciet, verwijzingen naar versiegebonden test- en releasebewijzen.

Gedeelde basis: https://github.com/OpenAEC-Foundation/OpenAEC-Blueprint. Bestaande bronnen en gegevenslicenties blijven leidend; interpretatieregels blijven gescheiden van IDS-conformiteit.

## Acceptatie per issue

Een werkende deelimplementatie sluit een issue niet automatisch. De acceptatiecriteria in het gekoppelde issue blijven leidend.

| Issue | Geleverde basis | Nog te verifiëren of implementeren |
|---|---|---|
| #2 Frappe-integratie | Zelfstandige viewer en server | Browserruntime, storage-adapter, hostintegratie en naamruimte |
| #3 Browservalidatie | Servervalidatie als referentie | Pyodide/wasm-proef met gelijkwaardige resultaten, tijd- en geheugenmetingen |
| #4 Reproduceerbaarheid | npm-lockfile, Python-lock, MIT-licentie, dependencylicenties, virtualenv uit git | Schone CI-build en licentieherkenning op de hoofdbranch |
| #5 Validatie-eisen | IDS-engine en rapportage | Volledige acceptatiematrix voor semantiek, herkomst, determinisme, foutstatussen en prestaties |
| #6 Ecosysteem | Windows-build, Python-library, CLI, HTTP API, stdio MCP en Blueprint UI 0.4 | Overige native platformen, SDK-contract en platformintegratie |
| #7 Versies | Script synchroniseert tien versievelden en controleert releasetags | Gepubliceerde release met overeenkomstige versie |
| #8 SuperCloud | Container en bestaande API | Gezamenlijke acceptatie van #9, #10 en #11 |
| #9 Containerrelease | Tagworkflow, OCI-labels, dependencylicenties, non-root en healthcheck | Gepubliceerde digest ophalen en controleren |
| #10 Servicecontract | Asynchrone validatiejobs | Gedeeld `/v1/tools`-contract en MCP over HTTP |
| #11 Isolatie | Bestaande tenantfilters voor projecten | API-keys, sleutelgebonden jobs/bestanden, limieten en bewaartermijnen zonder vertrouwde proxyheaders |
| #12 Clashdetectie | Bestaande clashroute en vieweronderdelen | Duplicaten, groepering, viewpoints en prestatieacceptatie volledig toetsen |
| #13 Modelversies | Project- en bestandsopslag | Revisies, modelvergelijking en nalevingsverloop |
| #14 Hercontrole | Handmatig aanroepbare validatie | Triggers, idempotentie en automatische hercontrole |
| #15 IDS-editor | Upload van bestaande IDS-bestanden | Browsereditor met schema- en inhoudsvalidatie |
| #16 Meten | 3D-viewer | Meetgereedschap en eenhedenacceptatie |
| #17 Smart Views | Modelweergave en selectie | Bewaarbare filters en kleuren op eigenschappen |
| #18 BCF-roundtrip | BCF 2.1-import in issue-UI, camera/selectie, statusbewerking en behoud van topicbestanden bij export | Externe API 3.0/OAuth2, status/reacties ophalen en externe testprojectacceptatie |
| #19 Hoeveelheden | IFC-elementgegevens | Aggregatie, eenheden en Excel-export |
| #20 Niet-IDS-regels | Aparte kwaliteitsroute | Afgebakende geometrische regels met expliciete herkomst en toetsstatus |
| #21 Georeferentie | Meerdere modellen in de viewer | Eenheden, coördinatenstelsels en federatieafwijkingen controleren |
| #22 NL-SfB | Eigenschappen beschikbaar voor validatie | Versiebeheerde codelijst, herkomst en inhoudelijke classificatiecontrole |
