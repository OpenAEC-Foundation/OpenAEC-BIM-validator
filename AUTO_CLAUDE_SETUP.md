# Auto Claude Setup Handleiding

## Wat is Auto Claude?

Auto Claude is een tool die Claude Code aanstuurt voor autonome software development. Het biedt:
- **Autonomous Tasks** - Agents die planning, coding en validation afhandelen
- **Agent Terminals** - Tot 12 parallelle agents
- **Memory Layer** - Onthoudt context tussen sessies

---

## Lokaal Starten (Zonder Git)

Je kunt prima lokaal experimenteren zonder git. Git is pas nodig als je:
- Code wilt delen met anderen
- Versies wilt bijhouden
- Naar productie wilt deployen

### Optie A: Direct met Claude Code (Simpelste)

Dit is de snelste manier om te starten:

```bash
# 1. Installeer Claude Code
npm install -g @anthropic-ai/claude-code

# 2. Open terminal in project folder
cd C:\IDS

# 3. Start Claude Code
claude

# Claude leest automatisch CLAUDE.md en kent de context
```

**Dat is alles!** Je kunt nu direct vragen stellen zoals:
- "Lees de specs voor Phase 0 en begin met ifctester research"
- "Maak een Python script dat een IDS file laadt"
- "Test of IfcOpenShell werkt met een simpel voorbeeld"

### Optie B: Auto Claude (Meer Gestructureerd)

Als je de volledige Auto Claude ervaring wilt:

#### Stap 1: Installeer vereiste software

```bash
# Node.js (v18+)
https://nodejs.org/

# Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Docker Desktop (optioneel, voor memory feature)
https://www.docker.com/products/docker-desktop/
```

#### Stap 2: Download Auto Claude

```bash
# Download van releases:
https://github.com/presidio-oss/cline-based-code-generator/releases

# Of clone (vereist git):
git clone https://github.com/presidio-oss/cline-based-code-generator.git
```

#### Stap 3: Start Auto Claude

1. Open Auto Claude applicatie
2. Klik op **"New Project"**
3. Selecteer `C:\IDS` als project folder
4. Auto Claude vindt automatisch `CLAUDE.md`

---

## Eerste Experiment: ifctester Testen

Voordat je de hele tool bouwt, test eerst of de kern werkt:

### Test 1: IfcOpenShell installeren

```bash
# Maak een test folder
mkdir C:\IDS\test
cd C:\IDS\test

# Maak virtual environment
python -m venv venv
venv\Scripts\activate

# Installeer IfcOpenShell
pip install ifcopenshell
```

### Test 2: ifctester proberen

```bash
# Installeer ifctester
pip install ifctester

# Maak test script
```

Maak bestand `C:\IDS\test\test_ids.py`:

```python
from ifctester import ids

# Laad de IDS
ids_file = ids.open(r"C:\IDS\ids-bestanden\NL_BIM_Basis_ILS_v2.ids")

# Check of het werkt
print(f"Geladen: {ids_file.info.title}")
print(f"Aantal specs: {len(ids_file.specifications)}")

for spec in ids_file.specifications:
    print(f"  - {spec.name}")
```

Run het:
```bash
python test_ids.py
```

**Als dit werkt → Phase 0 research is al half klaar!**

### Test 3: Met een IFC bestand (als je er een hebt)

```python
import ifcopenshell
from ifctester import ids

# Laad IFC
ifc = ifcopenshell.open("jouw_model.ifc")

# Laad IDS
ids_file = ids.open(r"C:\IDS\ids-bestanden\NL_BIM_Basis_ILS_v2.ids")

# Valideer
ids_file.validate(ifc)

# Bekijk resultaten
for spec in ids_file.specifications:
    status = "✅" if not spec.failed_entities else "❌"
    print(f"{status} {spec.name}: {len(spec.failed_entities)} gefaald")
```

---

## Wanneer Wel Git Gebruiken?

| Situatie | Git nodig? |
|----------|------------|
| Lokaal experimenteren | ❌ Nee |
| Proof of concept testen | ❌ Nee |
| Alleen voor jezelf bouwen | ❌ Nee |
| Code delen met collega's | ✅ Ja |
| Naar productie deployen | ✅ Ja |
| Open source publiceren | ✅ Ja |
| Versies willen terugdraaien | ✅ Ja |

### Later Git Toevoegen

Als je later besluit git te gebruiken:

```bash
cd C:\IDS
git init
git add .
git commit -m "Initial commit - werkende validator"

# Optioneel: naar GitHub pushen
# git remote add origin https://github.com/jouw-account/ifc-validator.git
# git push -u origin main
```

---

## Project Configureren in Auto Claude

### Via UI (zonder git)

1. **Project Name:** IFC Web Viewer
2. **Project Path:** `C:\IDS`
3. **Description:** Browser-based IFC validation tool

### Context Toevoegen

Kopieer inhoud van `C:\IDS\claude-code\PROJECT_CONTEXT.md` naar Auto Claude's Context sectie.

### Features Toevoegen

Maak deze features aan in Auto Claude:

#### Feature 1: Research (Start hier!)
```
Name: Phase 0 - Research
Priority: Critical
Duration: 3-5 dagen

Tasks:
- [ ] Test ifctester met NL_BIM_Basis_ILS.ids
- [ ] Test That Open Engine in browser
- [ ] Vergelijk client vs server rendering
- [ ] Documenteer bevindingen
- [ ] Go/No-Go beslissing
```

#### Feature 2: Engine + CLI
```
Name: Phase 1 - Validation Engine
Priority: High
Duration: 1 week

Tasks:
- [ ] Python project setup
- [ ] IFC Parser module
- [ ] IDS Validator module
- [ ] CLI tool
- [ ] Unit tests
```

(Voeg overige features toe zoals beschreven in ROADMAP.md)

---

## Aanbevolen Workflow

### Week 1: Experimenteren

```
Dag 1-2: Test ifctester lokaal
         → Werkt het? Ja/Nee

Dag 3-4: Test That Open Engine
         → Laadt IFC in browser? Ja/Nee

Dag 5:   Beslissing
         → Doorgaan of aanpassen?
```

### Week 2+: Bouwen (als research positief)

```
- Start Phase 1 in Claude Code
- Bouw incrementeel
- Test regelmatig
- Geen git nodig tot je wilt delen
```

---

## Tips voor Lokaal Werken

### Do's ✅

- **Klein beginnen** - Test eerst de kern (ifctester)
- **Regelmatig backups** - Kopieer werkende versies naar andere folder
- **Notities maken** - Documenteer wat werkt en wat niet

### Don'ts ❌

- **Niet te veel tegelijk** - Focus op één ding
- **Niet meteen alles bouwen** - Eerst proof of concept
- **Niet vergeten te backuppen** - Zonder git ben je eigen backup

### Simpele Backup Strategie

```bash
# Maak backup van werkende versie
xcopy C:\IDS C:\IDS_backup_v1 /E /I

# Of met datum
xcopy C:\IDS "C:\IDS_backup_%date:~-4%%date:~3,2%%date:~0,2%" /E /I
```

---

## Samenvatting

| Wat | Hoe |
|-----|-----|
| **Simpelste start** | `cd C:\IDS` → `claude` → begin te praten |
| **Eerst testen** | Run `test_ids.py` om ifctester te checken |
| **Git later** | Pas toevoegen als je wilt delen/deployen |
| **Backups** | Kopieer folder naar backup locatie |

---

## Volgende Stappen

1. ✅ Installeer Python + Node.js (als nog niet)
2. ✅ Maak test folder: `C:\IDS\test`
3. ✅ Test ifctester met het script hierboven
4. 🔄 Als het werkt → start Claude Code en bouw verder
5. 🔄 Als het niet werkt → debug of vraag hulp

---

Succes met experimenteren! 🧪

© 2025 3BM Bouwkunde
