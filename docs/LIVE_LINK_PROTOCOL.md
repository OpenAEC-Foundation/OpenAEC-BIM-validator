# Live Link Protocol — v1.0

Dit document beschrijft het open WebSocket-protocol waarmee de OpenAEC BIM
Validator-viewer live BIM-geometrie kan ontvangen van een lokaal draaiende
**feeder**. Elke applicatie die dit protocol implementeert — een plugin in een
authoring-applicatie, een los Python-script, een export-service — kan als
live databron voor de viewer fungeren.

De referentie-implementatie is `tools/livelink/feeder.py`: een Python-feeder
die een IFC-bestand laadt en over dit protocol streamt, en het bestand op
schijf bewaakt voor incrementele updates.

---

## Poorten en transport

| Service | Standaardpoort | Transport | Richting |
|---------|---------------|-----------|----------|
| **Feeder** | `19790` | WebSocket + HTTP | Feeder luistert; de viewer verbindt |

De viewer verbindt eerst met **`127.0.0.1`** (expliciete IPv4-loopback; dit
vermijdt de Windows-DNS-eigenaardigheid waarbij `localhost` eerst naar
`[::1]` resolvet). Als de socket direct wordt geweigerd (`ECONNREFUSED`),
probeert de viewer automatisch **`[::1]`** (IPv6-loopback) voordat
exponentiële backoff start (1 s → 2 s → 4 s … afgetopt op 30 s).

**Binding-eis voor feeders:** luister op **beide** loopback-adressen —
`127.0.0.1:19790` (IPv4) **én** `[::1]:19790` (IPv6) — als twee expliciete
listeners. Bind **nooit** aan `0.0.0.0` of `::`: dat zou de server op elke
netwerkinterface (LAN, Wi-Fi) blootstellen, wat onbedoeld is voor een lokale
desktoptool. Dubbele loopback geeft bereikbaarheid op beide adresfamilies
zonder netwerk-exposure.

---

## HTTP health-probe

De viewer stuurt bij het opstarten een `GET` naar `http://127.0.0.1:19790/`
om te detecteren of er een feeder draait, zonder meteen een WebSocket te
openen. De probe heeft een client-side timeout van 2 seconden.

Een feeder beantwoordt elke gewone HTTP-`GET` (elk pad) met status `200` en
een JSON-body:

```json
{
  "name": "openaec-livelink-feeder",
  "protocolVersion": "1.0",
  "appVersion": "0.1.0"
}
```

| Veld | Betekenis |
|------|-----------|
| `name` | Identificatie van de feeder-implementatie. |
| `protocolVersion` | Versie van **dit protocol** (semver major.minor). |
| `appVersion` | Versie van de feeder-**applicatie** zelf. |

---

## WebSocket-handshake

1. De viewer opent `ws://127.0.0.1:19790` (met `[::1]`-fallback).
2. Zodra de socket open is stuurt de viewer `{"type":"ping"}`.
3. De feeder antwoordt met `{"type":"pong", ...}` (zie hieronder).
4. Het protocol is nu actief.

De viewer hanteert een **handshake-timeout van 5 seconden** — komt er binnen
die tijd geen `pong`, dan sluit de viewer de socket en probeert opnieuw met
exponentiële backoff.

### Origin-allowlist

Feeders **moeten** de `Origin`-header van het WebSocket-upgrade-verzoek
valideren tegen een allowlist. Aanbevolen standaard-allowlist:

- de productie-origin(s) van de viewer;
- gangbare lokale dev-origins (`http://localhost:<poort>`,
  `http://127.0.0.1:<poort>`);
- de letterlijke string `"null"` — browsers sturen `Origin: null` voor
  pagina's die vanaf `file://` geopend zijn; lokaal een `index.html` vanaf
  schijf draaien is een ondersteunde workflow;
- verzoeken **zonder** `Origin`-header (niet-browser-clients) worden ook
  geaccepteerd.

Een verzoek met een niet-toegestane `Origin` wordt met HTTP `403` geweigerd
vóór de WebSocket-upgrade.

---

## Protocolversie versus app-versie

Er zijn **twee losse versienummers** en ze mogen niet vermengd worden:

1. **`protocolVersion`** (ook kortweg `version` in de `pong`) — de versie
   van dit protocol, semver **major.minor** als string, nu `"1.0"`.
   - *Zelfde major* → compatibel; een minor-verschil wordt gelogd maar is
     niet fataal.
   - *Andere major* → de viewer toont een versie-waarschuwing; functies
     kunnen ontbreken.
2. **`appVersion`** (in de `pong`: `feederVersion`) — de versie van de
   feeder-applicatie zelf. Puur informatief (logging, update-checks); heeft
   **geen** invloed op compatibiliteit.

Breaking wijzigingen aan het protocol (velden verwijderen, semantiek
veranderen) vereisen een major-bump. Additieve wijzigingen (nieuwe optionele
velden, nieuwe berichttypen) zijn minor-bumps en blijven backward-compatibel.
Implementaties negeren onbekende berichttypen en onbekende velden stilzwijgend.

---

## Berichtenreferentie

Alle berichten zijn JSON-objecten, verstuurd als WebSocket-**tekst**frames.
Binaire frames worden niet gebruikt.

### Viewer → feeder

#### `ping`

Direct na het openen van de WebSocket.

```json
{ "type": "ping" }
```

---

#### `export`

Vraag een geometrie-export aan. De feeder streamt terug:
`export-start` → `model-start` → `element-batch` (×N) → `model-end` →
`export-end`.

```json
{
  "type": "export",
  "categories": ["all"],
  "knownElements": {
    "<globalId>": "<contentHash>"
  }
}
```

| Veld | Type | Beschrijving |
|------|------|--------------|
| `categories` | string[] | Te exporteren categorieën. `["all"]` = alles. |
| `knownElements` | object? | **Delta-cache**: map `globalId → contentHash` van elementen die de viewer al heeft. De feeder streamt alleen elementen waarvan de hash afwijkt. Weggelaten bij een eerste export. |

---

#### `cancel-export`

Breek een lopende export af.

```json
{ "type": "cancel-export" }
```

---

### Feeder → viewer

#### `pong`

Antwoord op `ping`.

```json
{
  "type": "pong",
  "version": "1.0",
  "feederVersion": "0.1.0",
  "documentName": "gebouw_model.ifc"
}
```

| Veld | Type | Beschrijving |
|------|------|--------------|
| `version` | string | **Protocol**versie (semver major.minor). |
| `feederVersion` | string? | Versie van de feeder-applicatie. |
| `documentName` | string? | Naam van het geopende document/model. |

---

#### `export-start`

Begin van een exportsequentie.

```json
{
  "type": "export-start",
  "totalModels": 1,
  "totalElements": 12500
}
```

---

#### `model-start`

Eén per model. Bij gefedereerde bronnen (host + gelinkte bestanden) volgt
per bestand een eigen `model-start` … `model-end`-blok.

```json
{
  "type": "model-start",
  "name": "gebouw_model.ifc",
  "elementCount": 4200
}
```

| Veld | Type | Beschrijving |
|------|------|--------------|
| `name` | string | Weergavenaam van het model (bestandsnaam). |
| `elementCount` | number? | Verwacht totaal aantal elementen (voortgangsbalk). |

---

#### `element-batch`

Eén of meer batches (chunks) met elementen, volgend op `model-start`. Grote
modellen worden opgeknipt zodat de viewer incrementeel kan renderen en de
frames beheersbaar blijven.

```json
{
  "type": "element-batch",
  "batchIndex": 0,
  "totalBatches": 25,
  "elements": [
    {
      "globalId": "3g7k...",
      "name": "Basiswand 200mm",
      "category": "IfcWall",
      "type": "Basiswand",
      "level": "Verdieping 1",
      "materials": ["Beton - in het werk gestort"],
      "parameters": {
        "Pset_WallCommon": { "LoadBearing": true, "FireRating": "REI60" }
      },
      "quantities": { "Length": 4.2, "Area": 12.6, "Volume": 2.52 },
      "geometry": {
        "positions": "<base64 Float32Array>",
        "indices": "<base64 Uint32Array>",
        "normals": "<base64 Float32Array>",
        "color": [0.65, 0.65, 0.65, 1.0],
        "groups": [
          { "start": 0, "count": 120, "color": [0.65, 0.65, 0.65, 1.0] },
          { "start": 120, "count": 48, "color": [0.6, 0.8, 1.0, 0.15] }
        ]
      }
    }
  ]
}
```

**Elementvelden:**

| Veld | Type | Beschrijving |
|------|------|--------------|
| `globalId` | string | IFC GlobalId (22 tekens, base64-GUID). Primaire sleutel. |
| `name` | string? | Elementnaam. |
| `category` | string? | IFC-type (bv. `"IfcWall"`) of categorienaam uit de bronapplicatie. |
| `type` | string? | Typenaam uit de bronapplicatie. |
| `level` | string? | Naam van de bouwlaag/verdieping. |
| `materials` | string[]? | Materiaalnamen. |
| `parameters` | object? | Property-sets, gegroepeerd per Pset-naam. |
| `quantities` | object? | Platte map met gangbare hoeveelheden in SI-eenheden (m / m² / m³): `Length`, `Area`, `Volume`, `Width`, `Height`, `Thickness` — alleen wat aanwezig is. |
| `geometry` | object? | Mesh-data, zie hieronder. |

**Geometrievelden (`geometry`-object):**

| Veld | Type | Beschrijving |
|------|------|--------------|
| `positions` | string | Base64-gecodeerde `Float32Array` met XYZ-vertexposities in wereldcoördinaten (**meters**). Drie floats per vertex. |
| `indices` | string | Base64-gecodeerde `Uint32Array` met driehoeksindices. Drie indices per driehoek. |
| `normals` | string? | Base64-gecodeerde `Float32Array` met per-vertex-normalen. Berekent de viewer zelf als het veld ontbreekt. |
| `color` | [r,g,b,a]? | RGBA-kleur in bereik 0–1. Standaard `[0.65, 0.65, 0.65, 1.0]` (middengrijs). |
| `groups` | object[]? | **Per-materiaal draw-groups**: ranges in de indexbuffer `{ start, count, color:[r,g,b,a] }`, waarbij `start`/`count` index-offsets zijn (driehoeken × 3). Alleen nodig als een element meer dan één materiaal heeft (bv. kozijn + glas), zodat transparante delen correct renderen. Ondoorzichtige groups komen vóór transparante. Elementen met één materiaal gebruiken de platte `color`. |

**Weg te laten elementen:** stuur geen elementen die de bronapplicatie nooit
in 3D toont: stramienen, bouwlagen als objecten, referentievlakken, ruimtes
(tenzij expliciet gevraagd), camera's en viewports.

---

#### `model-end`

Einde van de elementstream van één model.

```json
{
  "type": "model-end",
  "storeys": ["Verdieping 1", "Verdieping 2", "Dak"],
  "storeyData": [
    { "name": "Verdieping 1", "elevation": 0.0 }
  ],
  "elementHashes": { "<globalId>": "<contentHash>" },
  "unchanged": ["<globalId>"]
}
```

| Veld | Type | Beschrijving |
|------|------|--------------|
| `storeys` | string[]? | Geordende namen van bouwlagen. |
| `storeyData` | object[]? | `{ name, elevation }` per bouwlaag (elevatie in meters). |
| `elementHashes` | object? | Content-hashes voor de delta-cache. De viewer bewaart deze lokaal en stuurt ze bij het volgende `export`-verzoek terug als `knownElements`. |
| `unchanged` | string[]? | GlobalIds van elementen die **niet** opnieuw zijn gestreamd omdat hun hash overeenkwam met `knownElements`. De viewer behoudt ze uit het bestaande model. |

---

#### `export-end`

Einde van de volledige export.

```json
{ "type": "export-end" }
```

---

#### `element-update`

Incrementele update buiten een exportsequentie om — één of meer elementen
zijn gewijzigd, verwijderd, of hebben alleen nieuwe properties. Voorkomt een
volledige her-export wanneer het bronmodel wijzigt.

```json
{
  "type": "element-update",
  "action": "modified",
  "elements": [ /* zelfde schema als element-batch-elementen */ ]
}
```

```json
{
  "type": "element-update",
  "action": "deleted",
  "globalIds": ["3g7k...", "9a1m..."]
}
```

```json
{
  "type": "element-update",
  "action": "properties-only",
  "elements": [
    {
      "globalId": "3g7k...",
      "parameters": { "Pset_WallCommon": { "FireRating": "REI90" } }
    }
  ]
}
```

| `action` | Effect |
|----------|--------|
| `modified` | Vervang geometrie én properties van de genoemde elementen (nieuwe elementen: toevoegen). |
| `deleted` | Verwijder elementen op `globalIds`. |
| `properties-only` | Merge alleen de properties; GPU-geometrie blijft onaangeroerd. |

---

#### `error`

Generieke foutmelding.

```json
{ "type": "error", "message": "Er ging iets mis" }
```

---

## Content-hash en delta-cache

Elke feeder berekent per element een **content-hash** over geometrie én
properties:

```
hash = hex( SHA-256( positions ‖ indices ‖ normals ‖ canonical_json(properties) ) )[0:16]
```

- `positions`, `indices`, `normals`: de rauwe bytes van de arrays
  (little-endian; `normals` mag leeg zijn als ze niet meegestuurd worden);
- `canonical_json(properties)`: de properties/parameters als JSON met
  gesorteerde sleutels en zonder witruimte, UTF-8-gecodeerd;
- resultaat: de **eerste 8 bytes** van de digest als **16 hex-tekens**
  (kleine letters).

De viewer bewaart de `elementHashes` uit `model-end` en stuurt ze bij een
volgende `export` terug als `knownElements`. De feeder streamt dan alleen
elementen waarvan de hash afwijkt of die nieuw zijn; identieke elementen
komen als `unchanged`-lijst in `model-end`. Elementen die in de cache van de
viewer zitten maar niet meer in het model bestaan, meldt de feeder als
`element-update` met `action: "deleted"` (of de viewer ruimt ze zelf op na
`export-end` op basis van `elementHashes` + `unchanged`).

---

## Coördinatensysteem

Alle geometrie is in een **rechtshandig, Y-up coördinatensysteem in meters**
(de gangbare webgraphics-conventie). De gebruikelijke mapping vanuit IFC
(Z-up) is:

| IFC (Z-up) | Live Link (Y-up) |
|------------|------------------|
| X (oost) | X |
| Z (omhoog) | Y |
| −Y (noord) | Z |

Ofwel per vertex: `(x, y, z)ifc → (x, z, −y)`. De viewer herprojecteert
niets: alle modellen binnen één sessie moeten hetzelfde wereldorigin delen.
Bak bij gefedereerde modellen de gedeelde-coördinaten-transformaties vooraf
in de posities.

---

## Typische berichtenflow

```
Viewer                                   Feeder
──────                                   ──────
                open ws://127.0.0.1:19790
  ping        →
              ←   pong { version:"1.0", feederVersion, documentName }

  export { categories:["all"] }  →
              ←   export-start { totalModels:1, totalElements:8000 }
              ←   model-start  { name:"gebouw_model.ifc", elementCount:8000 }
              ←   element-batch (×N)
              ←   model-end    { storeys, elementHashes, unchanged }
              ←   export-end

  (bronbestand wijzigt op schijf)
              ←   element-update { action:"modified",  elements:[…] }
              ←   element-update { action:"deleted",   globalIds:[…] }
```

## Delta-export (herverbinding)

```
Viewer                                   Feeder
──────                                   ──────
  export { knownElements:{…} }  →
              ←   export-start
              ←   model-start
              ←   element-batch  (alleen gewijzigde/nieuwe elementen)
              ←   model-end { unchanged:[…], elementHashes:{…} }
              ←   export-end
```

---

## Referentie-implementatie

`tools/livelink/feeder.py` in deze repository implementeert dit protocol als
zelfstandige Python-feeder op basis van een IFC-bestand, inclusief
bestandsbewaking (mtime-polling, 2 s) en delta-updates op content-hash.
Zie `tools/livelink/README.md` voor gebruik.
