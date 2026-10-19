import re
import threading
import unicodedata
from dataclasses import dataclass

from app.spec import SpecError, as_text, load_spec
from app.svgutil import frame_svg
from app.theme import RENDERERS

LOCK = threading.Lock()


@dataclass
class Figure:
    svg: str
    renderer: str
    warnings: list[str]
    diagram_type: str
    title: str
    filename: str


def render_text(text: str) -> Figure:
    return render_spec(load_spec(text))


def render_spec(spec: dict) -> Figure:
    kind = as_text(spec.get("type")).lower()
    if kind not in RENDERERS:
        allowed = ", ".join(RENDERERS)
        raise SpecError(f"type phải là một trong: {allowed}")
    title = as_text(spec.get("title"))
    if not title:
        raise SpecError("Cần title")
    prepared = {**spec, "type": kind, "title": title}
    with LOCK:
        raw, warnings = _dispatch(kind, prepared)
    return Figure(
        svg=frame_svg(raw, prepared),
        renderer=RENDERERS[kind],
        warnings=warnings,
        diagram_type=kind,
        title=title,
        filename=_slug(title),
    )


def _dispatch(kind: str, spec: dict) -> tuple[str, list[str]]:
    if kind == "architecture":
        from app.renderers.architecture import render_architecture

        return render_architecture(spec)
    if kind in {"context", "flow", "dependency"}:
        from app.renderers.graph import render_graph

        return render_graph(spec)
    if kind == "roadmap":
        from app.renderers.roadmap import render_roadmap

        return render_roadmap(spec)
    if kind == "sequence":
        from app.renderers.sequence import render_sequence

        return render_sequence(spec)
    if kind == "stack":
        from app.renderers.stack import render_stack

        return render_stack(spec)
    if kind == "schematic":
        from app.renderers.schematic import render_schematic

        return render_schematic(spec)
    raise SpecError(f"Chưa có renderer cho {kind}")


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text[:60] or "diagram"
