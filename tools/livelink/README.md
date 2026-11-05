# Live Link feeder (referentie-implementatie)

Streamt een IFC-bestand live naar de viewer via het open **Live Link
Protocol v1.0** (zie [`docs/LIVE_LINK_PROTOCOL.md`](../../docs/LIVE_LINK_PROTOCOL.md)).

## Wat het doet

- Laadt een IFC-bestand met `ifcopenshell` (wereldcoördinaten, getrianguleerd)
  en zet de geometrie om naar het protocol-meshformaat (base64
  Float32/Uint32, meters, Y-up, per-materiaal draw-groups).
- Serveert het protocol op een **localhost-only** WebSocket
  (`127.0.0.1` + `[::1]`, poort **19790**) met een HTTP health-probe op
  dezelfde poort.
- Bewaakt het bestand op schijf (mtime-polling elke 2 s) en her-streamt
  **alleen gewijzigde elementen** op basis van een SHA-256 content-hash
  (eerste 8 bytes, hex).

## Starten

```bash
pip install websockets ifcopenshell   # eenmalig

python tools/livelink/feeder.py pad/naar/model.ifc
# opties: --port 19790  --batch-size 100  --poll-interval 2  --allow-origin https://...
```

Health-check: `curl http://127.0.0.1:19790/` →
`{"name": "openaec-livelink-feeder", "protocolVersion": "1.0", "appVersion": "0.1.0"}`

## Versies

| Wat | Versie |
|-----|--------|
| Protocolversie | **1.0** (semver major.minor; los van de app-versie) |
| Feeder-app | 0.1.0 |

## Tests

```bash
python -m pytest test/test_livelink_protocol.py -q -o addopts=""
```
