import os
import shutil
from pathlib import Path

GRAPHVIZ_HELP = (
    "Chưa tìm thấy Graphviz (lệnh dot). "
    "Cài bằng: winget install Graphviz.Graphviz — rồi mở lại Diagram Studio."
)

_CANDIDATES = (
    Path(r"C:\Program Files\Graphviz\bin"),
    Path(r"C:\Program Files (x86)\Graphviz\bin"),
)


def ensure_graphviz_on_path() -> str | None:
    for folder in _CANDIDATES:
        if (folder / "dot.exe").exists():
            folder_text = str(folder)
            current = os.environ.get("PATH", "")
            if folder_text.lower() not in current.lower():
                os.environ["PATH"] = folder_text + os.pathsep + current
            break
    return shutil.which("dot")
