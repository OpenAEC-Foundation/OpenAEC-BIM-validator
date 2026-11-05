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
