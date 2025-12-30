"""
Test script voor ifctester - 3BM IFC Validator
Run dit om te checken of de basis werkt.

Gebruik:
    1. Maak virtual environment: python -m venv venv
    2. Activeer: venv\Scripts\activate
    3. Installeer: pip install ifcopenshell ifctester
    4. Run: python test_ifctester.py
"""

import sys
from pathlib import Path

def test_ifctester():
    print("=" * 60)
    print("3BM IFC Validator - ifctester Test")
    print("=" * 60)
    
    # Test 1: Import check
    print("\n1️⃣ Imports testen...")
    try:
        from ifctester import ids
        print("   ✅ ifctester geïmporteerd")
    except ImportError as e:
        print(f"   ❌ ifctester import failed: {e}")
        print("   → Run: pip install ifctester")
        return False
    
    try:
        import ifcopenshell
        print(f"   ✅ ifcopenshell geïmporteerd (versie: {ifcopenshell.version})")
    except ImportError as e:
        print(f"   ❌ ifcopenshell import failed: {e}")
        print("   → Run: pip install ifcopenshell")
        return False
    
    # Test 2: IDS laden
    print("\n2️⃣ IDS bestanden laden...")
    
    ids_folder = Path(__file__).parent.parent / "ids-bestanden"
    
    ids_files = [
        ids_folder / "NL_BIM_Basis_ILS_v2.ids",
        ids_folder / "RVB_BIM_Norm_v1.1.ids",
    ]
    
    for ids_path in ids_files:
        if ids_path.exists():
            try:
                ids_file = ids.open(str(ids_path))
                print(f"   ✅ {ids_path.name}")
                print(f"      Titel: {ids_file.info.title}")
                print(f"      Specs: {len(ids_file.specifications)}")
            except Exception as e:
                print(f"   ❌ {ids_path.name}: {e}")
        else:
            print(f"   ⚠️ {ids_path.name} niet gevonden")
    
    # Test 3: Specificaties bekijken
    print("\n3️⃣ Specificaties in NL_BIM_Basis_ILS_v2:")
    
    nl_ids_path = ids_folder / "NL_BIM_Basis_ILS_v2.ids"
    if nl_ids_path.exists():
        ids_file = ids.open(str(nl_ids_path))
        for i, spec in enumerate(ids_file.specifications, 1):
            print(f"   {i:2}. {spec.name}")
    
    # Test 4: IFC bestand (optioneel)
    print("\n4️⃣ IFC bestand testen...")
    
    # Zoek naar .ifc bestanden in test folder
    test_folder = Path(__file__).parent
    ifc_files = list(test_folder.glob("*.ifc"))
    
    if ifc_files:
        ifc_path = ifc_files[0]
        print(f"   Gevonden: {ifc_path.name}")
        
        try:
            ifc = ifcopenshell.open(str(ifc_path))
            print(f"   ✅ IFC geladen")
            print(f"      Schema: {ifc.schema}")
            print(f"      Elementen: {len(list(ifc.by_type('IfcProduct')))}")
            
            # Valideer tegen IDS
            print("\n5️⃣ Validatie uitvoeren...")
            ids_file = ids.open(str(nl_ids_path))
            ids_file.validate(ifc)
            
            passed = 0
            failed = 0
            
            for spec in ids_file.specifications:
                if spec.status:
                    passed += 1
                    status = "✅"
                else:
                    failed += 1
                    status = "❌"
                
                fail_count = len(spec.failed_entities) if hasattr(spec, 'failed_entities') else 0
                print(f"   {status} {spec.name}")
                if fail_count > 0:
                    print(f"      → {fail_count} elementen gefaald")
            
            print(f"\n   Samenvatting: {passed} passed, {failed} failed")
            
        except Exception as e:
            print(f"   ❌ Fout bij IFC laden: {e}")
    else:
        print("   ⚠️ Geen IFC bestand gevonden in test folder")
        print("   → Plaats een .ifc bestand in C:\\IDS\\test\\ om te testen")
    
    # Conclusie
    print("\n" + "=" * 60)
    print("✅ Basis test geslaagd! ifctester werkt.")
    print("=" * 60)
    print("\nVolgende stappen:")
    print("1. Plaats een IFC bestand in C:\\IDS\\test\\")
    print("2. Run dit script opnieuw voor volledige validatie test")
    print("3. Start Claude Code: cd C:\\IDS && claude")
    
    return True

if __name__ == "__main__":
    success = test_ifctester()
    sys.exit(0 if success else 1)
