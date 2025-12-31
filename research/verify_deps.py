"""Verify all research dependencies are installed correctly."""

def main():
    print("Verifying research dependencies...")
    print("-" * 40)

    # Check ifcopenshell
    try:
        import ifcopenshell
        print(f"ifcopenshell: {ifcopenshell.version}")
    except ImportError as e:
        print(f"ifcopenshell: FAILED - {e}")

    # Check ifctester
    try:
        from ifctester import ids
        print("ifctester: OK")
    except ImportError as e:
        print(f"ifctester: FAILED - {e}")

    # Check FastAPI
    try:
        from fastapi import FastAPI
        import fastapi
        print(f"fastapi: {fastapi.__version__}")
    except ImportError as e:
        print(f"fastapi: FAILED - {e}")

    # Check python-multipart
    try:
        import multipart
        print("python-multipart: OK")
    except ImportError as e:
        print(f"python-multipart: FAILED - {e}")

    # Check uvicorn
    try:
        import uvicorn
        print("uvicorn: OK")
    except ImportError as e:
        print(f"uvicorn: FAILED - {e}")

    print("-" * 40)
    print("Dependency verification complete!")

if __name__ == "__main__":
    main()
