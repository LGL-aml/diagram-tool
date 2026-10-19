from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = Path(__file__).resolve().parent
TEMPLATES = PACKAGE / "templates"
SPECS = ROOT / "specs"
STATIC = PACKAGE / "static"
RENDER_DIR = ROOT / ".render"
OUTPUT_DIR = ROOT / "output"

SPECS.mkdir(exist_ok=True)
RENDER_DIR.mkdir(exist_ok=True)
