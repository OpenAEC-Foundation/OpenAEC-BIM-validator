# IFC Validator Project - 3BM Bouwkunde

## Quick Start (Lokaal Testen)

```bash
# 1. Maak virtual environment
cd C:\IDS\test
python -m venv venv
venv\Scripts\activate

# 2. Installeer dependencies
pip install ifcopenshell ifctester

# 3. Test of het werkt
python test_ifctester.py
```

**Als de test slaagt → je kunt verder bouwen!**

---

## Folder Structuur

```
C:\IDS\
├── README.md                      ← Dit bestand
├── AUTO_CLAUDE_SETUP.md           ← Handleiding (lokaal, zonder git)
├── CLAUDE.md                      ← Context voor Claude Code
│
├── test/                          ← 🆕 Test folder
│   └── test_ifctester.py         ← Test script om te starten
│
├── ids-bestanden/                 ← IDS specificaties
│   ├── NL_BIM_Basis_ILS_v2.ids   ← 13 checks, NL standaard
│   └── RVB_BIM_Norm_v1.1.ids     ← 30 checks, Rijksvastgoed
│
├── claude-code/                   ← Development documentatie
│   ├── PROJECT_CONTEXT.md        ← Volledige project info
│   ├── ROADMAP.md                ← Fase planning
│   ├── ARCHITECTURE_DECISIONS.md ← Technische beslissingen
│   ├── specs/                    ← Specs per fase
│   └── fixtures/                 ← Test bestanden
│
└── webpagina/                     ← UI mockup
    └── index.html                ← 3BM branded preview
```

---

## Stap-voor-Stap

### Stap 1: Test de Basis
```bash
cd C:\IDS\test
python -m venv venv
venv\Scripts\activate
pip install ifcopenshell ifctester
python test_ifctester.py
```

### Stap 2: Test met Eigen IFC
Plaats een `.ifc` bestand in `C:\IDS\test\` en run het script opnieuw.

### Stap 3: Start Claude Code
```bash
cd C:\IDS
claude
```
Claude leest automatisch `CLAUDE.md` en kent de context.

### Stap 4: Bouw Verder
Vraag Claude om te beginnen met Phase 1 volgens de specs.

---

## Geen Git Nodig

Je kunt volledig lokaal werken. Git is pas nodig als je:
- Code wilt delen met anderen
- Naar productie wilt deployen
- Versiebeheer wilt

**Backup tip:** Kopieer werkende versies naar een backup folder.

---

## Links

- [IfcOpenShell](https://ifcopenshell.org/)
- [ifctester Docs](https://docs.ifcopenshell.org/ifctester.html)
- [That Open Engine](https://thatopen.com/)
- [IDS Specification](https://technical.buildingsmart.org/projects/information-delivery-specification-ids/)

---

© 2025 3BM Bouwkunde - Ingenieurs van oplossingen
